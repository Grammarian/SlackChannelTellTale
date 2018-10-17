import json
import logging
import random
import re
import time

from toolbox import nested_get
from in_memory_redis import InMemoryRedis
from uncommon_words import uncommon_words

COLORS = ["#ff1744", "#f50057", "#d500f9", "#651fff", "#3d5afe", "#2979ff", "#00b0ff", "#00e5ff",
          "#1de9b6", "#00e676", "#76ff03", "#ffea00", "#ffc400", "#ff9100", "#ff3d00"]


class Processor:
    """
    This class processes slack events and sends notification messages as required
    """

    def __init__(self, target_channel_id, channel_prefixes, slack_client, redis_client=None, logger=None, jira=None, image_searcher=None):
        self.target_channel_id = target_channel_id
        self.channel_prefixes = channel_prefixes
        self.slack_client = slack_client
        self.redis_client = redis_client or InMemoryRedis()
        self.logger = logger or logging.getLogger("Processor")
        self.image_search = image_searcher

        # Make sure that, if there is a jira prefix, it ends with "/jira/browse/"
        self.jira_prefix = jira if not jira or jira.endswith("/jira/browse/") else jira + "/jira/browse/"

    def remember_channel(self, channel):
        """
        Remember the given channel. Return a bool indicating if we've already seen it
        """
        redis_channel_key = "channel:%s" % channel["id"]
        is_new = self.redis_client.setnx(redis_channel_key, channel.get("created", "0"))
        if is_new:
            # We don't want our redis instance to just continue growing, so delete the key after 7 days
            self.redis_client.expire(redis_channel_key, 7 * 24 * 60 * 60)
        return not is_new

    def get_channel_info(self, channel_id):
        """
        Fetch information about the given channel from slack
        """
        channel_info = self.slack_client.channel_info(channel_id)
        if channel_info and channel_info.get("ok"):
            return channel_info

        self.logger.error("fetching of channel %s failed: %s", channel_id, repr(channel_info))
        return None

    def insistent_get_channel_info(self, channel_id):
        """
        Repeatedly attempt to fetch information about the given channel from slack

        We particularly want the purpose of the channel, but Slack sometimes separates
        the creation of the channel from the setting of the purpose, so we have to do
        a little waiting dance. It could be that the channel was created without a 
        purpose, so don't try too hard
        """
        attempts = 0
        channel_info = self.get_channel_info(channel_id)
        while attempts < 3 and not nested_get(channel_info, "channel", "purpose", "value"):
            attempts += 1
            self.logger.info("attempt %d: waiting for channel %s to find its purpose in life", attempts, channel_id)
            time.sleep(1)
            channel_info = self.get_channel_info(channel_id)

        return channel_info

    def process_channel_event(self, event_type, event_data):
        """
        When a channel is created or renamed, send a notification message to the target channel, if required.

        For the same channel, we will only send one notification message, even if we receive multiple
        created notifications, or if it is renamed multiple times.
        """
        channel = nested_get(event_data, "event", "channel")

        # Make sure the event structure is sensible
        if not channel or \
                "id" not in channel or \
                "name" not in channel:
            self.logger.error("ignored... event was missing required attributes")
            return

        channel_id = channel["id"]
        channel_name = channel["name"]

        # Is the new channel one of the ones that we want to report?
        if self.channel_prefixes and not any(channel_name.startswith(x) for x in self.channel_prefixes):
            self.logger.info("ignored... channel name doesn't start with the appropriate prefix: %s", channel_name)
            return

        # Have we already processed this channel?
        if self.remember_channel(channel):
            self.logger.info("ignored... we've already processed this channel: %s/%s", channel_id, channel_name)
            return

        # Try hard to fetch the full info about the channel
        channel_info = self.insistent_get_channel_info(channel_id)
        if not channel_info:
            self.logger.error("ignored.... failed to get information about the channel (%s/%s)", channel_id, channel_name)
            return

        # Fetch the full info about the creator of the channel
        creator_id = nested_get(channel_info, "channel", "creator")
        if not creator_id:
            self.logger.error("ignored... channel did not contain creator: %s", repr(channel_info))
            return
        creator_info = self.slack_client.user_info(creator_id)
        if not creator_info or not creator_info.get("ok"):
            self.logger.error("ignored... fetching of creator failed: %s", repr(creator_info))
            return

        # We now have all the information that we need to send the creation notification
        self._send_pretty_notification(event_type, channel_info.get("channel"), creator_info.get("user"))

        # Do any post notification processing
        self._post_notification(event_type, channel_info.get("channel"))

    # noinspection PyPep8Naming
    def _send_pretty_notification(self, event_type, channel, creator):
        """
        Send a channel creation notification to the given target channel
        """
        # Log for debugging if needed
        self.logger.info("channel: %s", json.dumps(channel))
        self.logger.info("creator: %s", json.dumps(creator))

        # Setup all the values that will be needed for the messages
        values = {
            "creator_id": nested_get(creator, "id"),
            "creator_name": nested_get(creator, "profile", "real_name_normalized"),
            "creator_image": nested_get(creator, "profile", "image_24"),
            "channel_id": nested_get(channel, "id"),
            "channel_name": nested_get(channel, "name"),
            "channel_purpose": nested_get(channel, "purpose", "value"),
            "rename_msg": "(via renaming)" if event_type == "rename" else ""
        }

        # Use templates for all fields in the message (even though some don't need complex substitutions).
        # The messages use the attachments format: https://api.slack.com/docs/message-attachments
        MESSAGE_TEMPLATE = {
            "fallback": "{creator_name} just created a new channel {rename_msg} :tada:\n"
                        "<#{channel_id}|{channel_name}>\n"
                        "Its purpose is: {channel_purpose} ",
            "color": random.choice(COLORS),
            "pretext": "A new channel has been created {rename_msg} :tada:",
            "author_name": "{creator_name} <@{creator_id}>",
            "author_icon": "{creator_image}",
            "title": "<#{channel_id}>",
            "text": "{channel_purpose}"
        }
        # Make a nicely format notification from the above template
        fancy_message = {key: value.format(**values) for (key, value) in MESSAGE_TEMPLATE.items()}
        self.logger.info("sending to %s: %s", self.target_channel_id, json.dumps(fancy_message))

        # Finally, announce the new channel in the announcement channel
        self.slack_client.post_chat_message(self.target_channel_id, fancy_message)

    def _post_notification(self, event_type, channel):
        """
        Do any post processing required. This can include setting the channel's purpose, topic, or
        sending an intro message to the channel.

        :param event_type: Was the channel created or renamed?
        :param channel: Full channel info
        """
        # At the moment, all the post processing is only relevant to newly created channels
        if event_type != "create":
            return

        # For testing purposes, let's limit this to just my channels
        if not channel.get("name").startswith("jpp"):
            return

        self._post_notification_jira(channel)
        self._post_notification_intro_message(channel)

    def _post_notification_jira(self, channel):
        """
        Do any post processing related to jira

        :param channel: Full channel info
        """
        # If we're not configured for jira, there's nothing to do
        if not self.jira_prefix:
            return

        # If the channel isn't related to a JIRA ticket, there's nothing else to do
        channel_name = channel.get("name")
        jira_id = self._extract_jira_id(channel_name)
        if not jira_id:
            return

        link = self.jira_prefix + jira_id
        message = {
            "fallback": "This channel is related to this JIRA issue: %s" % link,
            "color": random.choice(COLORS),
            "title": "Related JIRA Issue",
            "text": link
        }
        channel_id = channel.get("id")
        self.slack_client.post_chat_message(channel_id, message)

    def _extract_jira_id(self, channel_name):
        """
        If the channel name looks like it relates to a JIRA issue, extract and return the JIRA id.

        The code understands channel names that looks like: [prefix]-[issue number]-[tail]
        The dash before and after the jira id are optional.

        Jira ids have to look like this: [A-Za-z]+ [dash] [0-9]+

        Project prefixes are (by default) 2 uppercase letters, but only the first character *has*
        to be a letter -- subsequent characters can also be numbers or underscore, but *not* hyphen.
        https://confluence.atlassian.com/adminjiraserver/changing-the-project-key-format-938847081.html

        Just for sanity, we limit the prefix and the issue number to 32 characters each.

        :param channel_name:
        :return: The jira id related to the name or None
        """
        name = self._remove_prefix(channel_name)
        match = re.match("([A-Za-z][A-Za-z0-9_]{1,32}-[0-9]{1,32})", name)
        return match.group(1) if match else None

    def _remove_prefix(self, name):
        for prefix in self.channel_prefixes:
            if name.startswith(prefix):
                return name[len(prefix):]
        return name

    cute_animals = [
        "https://i.ytimg.com/vi/opKg3fyqWt4/hqdefault.jpg",
        "http://cdn2.holytaco.com/wp-content/uploads/images/2009/12/dog-cute-baby.jpg",
        "http://1.bp.blogspot.com/-NnDHYuLcDbE/ToJ6Rd6Dl5I/AAAAAAAACa4/NzFAKfIV_CQ/s400/golden_retriever_puppies.jpg",
        "https://pbs.twimg.com/profile_images/497043545505947648/ESngUXG0.jpeg",
        "https://assets.rbl.ms/10706353/980x.jpg",
        "http://stuffpoint.com/dogs/image/92783-dogs-cute-puppy.png",
        "https://groomarts.com/assets/images/_listItem/cute-puppy-1.jpg",
        "https://pbs.twimg.com/profile_images/568848749611724800/Gv5zUXpu.jpeg",
        "https://i.ytimg.com/vi/rT_I_GV_oEM/hqdefault.jpg",
        "http://2.bp.blogspot.com/-GWvh8d_O8QE/UcnF6E7hJpI/AAAAAAAAAF8/VzvEBk3cVsk/s1600/cute+pomeranian+puppies.jpg",
        "https://i.ytimg.com/vi/Gw_xvtWJ6q0/hqdefault.jpg",
        "http://3.bp.blogspot.com/-Nlispwf06Ec/UaeSfJ3jXrI/AAAAAAAALl4/UxXUUzEyUdg/s640/cute+puppies+1.jpg",
        "https://groomarts.com/assets/images/_listItem/cute-puppy-2.jpg",
        "http://1.bp.blogspot.com/-HpbjntFMqpQ/TyOKIp8s-6I/AAAAAAAAE6Q/kBJdpTqgx80/s1600/Cute-Kissing-Puppies-02.jpg",
        "https://i.ytimg.com/vi/XhDZGkA1cDk/hqdefault.jpg",
        "https://pbs.twimg.com/profile_images/555279965194051585/swMjWLLf.jpeg",
        "https://i.ytimg.com/vi/xTVDBegsddE/hqdefault.jpg",
        "http://1.bp.blogspot.com/-Jp-_R2WUyVg/USXcf-GJi_I/AAAAAAAAAQ0/7QWew3pXoM8/s400/very+cute+puppies+and+kittens09.jpg",
        "https://s-media-cache-ak0.pinimg.com/736x/61/ec/ff/61ecff9521848763390c9056ebf87191.jpg",
        "https://s-media-cache-ak0.pinimg.com/736x/e4/d4/6d/e4d46d3d4e6bec19fecf6cb168cf9375.jpg",
        "http://4.bp.blogspot.com/_HOCuXB2IC34/SuhaDCdFP_I/AAAAAAAAEhU/1SJlOOuO5og/s400/1+(www.cute-pictures.blogspot.com).jpg",
        "http://www.cutenessoverflow.com/wp-content/uploads/2016/06/a.jpg",
        "https://i0.wp.com/www.cutepuppiesnow.com/wp-content/uploads/2017/03/Maltese-Puppy-2.jpg",
        "http://cuteimages.net/data/460x/2015/9/dog-family-cutest-cuteimages.net.jpg"
    ]

    def _post_notification_intro_message(self, channel):
        """
        Guess an appropriate intro message and send it to the channel

        :param channel: Full channel info
        """

        # If all else fails, send this message
        txt = "*I have no idea what this channel is about. So here's a cute animal photo.*\n\n%s" % random.choice(self.cute_animals)

        # What is the purpose of the channel? Fall back to the channel name as a last resort
        channel_purpose = nested_get(channel, "purpose", "value") or ""
        words_from_channel_name = self._remove_prefix(channel.get("name")).replace("-", " ")

        # Find photo related to the purpose of the channel
        if self.image_search:
            candidates = "%s %s" % (channel_purpose, words_from_channel_name)
            img = self.image_search.random(uncommon_words(candidates))
            if img:
                txt = "*This might be appropriate for this channel\n\n%s" % img

        # Send the message
        channel_id = channel.get("id")
        self.slack_client.post_chat_text_message(channel_id, txt)
