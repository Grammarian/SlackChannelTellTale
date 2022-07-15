import datetime
import json
import logging
import random
import re
import time
import itertools
from collections import namedtuple

from in_memory_redis import InMemoryRedis
from toolbox import nested_get
import clippy_messages

COLORS = ["#ff1744", "#f50057", "#d500f9", "#651fff", "#3d5afe", "#2979ff", "#00b0ff", "#00e5ff",
          "#1de9b6", "#00e676", "#76ff03", "#ffea00", "#ffc400", "#ff9100", "#ff3d00"]
AVALANCHES = [
    "https://media.giphy.com/media/MZoiwmsZXx6g0/giphy-downsized.gif",
    "https://media.giphy.com/media/ZTjQgJGDiuJZS/giphy-downsized.gif",
    "https://media.giphy.com/media/l41YBikSYhA4LybJe/giphy-downsized.gif",
    "https://media.giphy.com/media/xT5LMSY5XBlbAXBVwk/giphy.gif"
]
APRIL_FOOL_ONLY_CHANNELS = ["fun-", "test-"]

KnownUser = namedtuple('KnownUser', ['display_name', 'user_id'])

# How long do we want to keep information about channels? Default is 60 days.
# During this period we will not report the same channel a second time.
# If a rename happens outside of this period, we will announce the same channel a second time.
CHANNEL_INFO_TTL_IN_SECONDS = 60 * (24 * 60 * 60)


class Processor:
    """
    This class processes slack events and sends notification messages as required
    """

    def __init__(self, target_channel_to_prefixes_map, slack_client, redis_client=None, logger=None, jira=None,
                 fomo_users_as_string=None):
        self.slack_client = slack_client
        self.redis_client = redis_client or InMemoryRedis()
        self.logger = logger or logging.getLogger("Processor")
        self.logger.info("target_channel_to_prefixes_map: %r", target_channel_to_prefixes_map)

        # Make sure that, if there is a jira prefix, it ends with "/jira/browse/"
        self.jira_prefix = jira if not jira or jira.endswith("/jira/browse/") else jira + "/jira/browse/"

        # Parse the fomo list of users
        self.fomo_users = self._parse_fomo_users(fomo_users_as_string)

        # Convert the map of channel->prefixes into a single list of (prefix, channel) tuples
        self.all_channel_prefixes_with_target_channel = [
            (each_prefix, channel)
            for (channel, prefixes) in target_channel_to_prefixes_map.items()
            for each_prefix in prefixes
        ]

        # Create a collection of all known prefixes so we can easily test if we are interested in a channel
        self.all_channel_prefixes = set(x[0] for x in self.all_channel_prefixes_with_target_channel).union(APRIL_FOOL_ONLY_CHANNELS)

    def _parse_fomo_users(self, fomo_users_as_string):
        """
        Parse a list of channel prefixes and users from the given string.
        The format is:
         - <channel_definition>[|<channel_definition>]*
        and <channel_definition> is:
         - <channel_prefix>[,channel_prefix]*:<display_name>[,<display_name>]*
        """
        self.logger.info("parse_fomo_users from %s", fomo_users_as_string)

        if not fomo_users_as_string:
            return {}

        # Map all display names to user ids
        map_name_to_id = {user.get("name"): user.get("id") for user in self._fetch_slack_users()}

        fomo_definitions = {}
        for channel_definition in fomo_users_as_string.split("|"):
            (channels, users_for_channels) = self._parse_one_fomo_channel(channel_definition, map_name_to_id)
            for channel in channels:
                fomo_definitions[channel] = users_for_channels

        self.logger.debug("fomo users: %s", json.dumps(fomo_definitions, indent=2))
        return fomo_definitions

    def _fetch_slack_users(self):
        """
        Fetch the list of known users from slack.
        """
        # THINK - Fetching users takes about ~20 seconds. We could cache the result in redis and refetch it once/day
        start = time.time()
        users = self.slack_client.users()
        self.logger.info("loaded %d users from slack in %d seconds", len(users), int(time.time() - start))
        return users

    def _parse_one_fomo_channel(self, channel_definition, map_name_to_id):
        (channel_prefixes, users) = channel_definition.split(":")
        channels = channel_prefixes.split(',')
        display_names = [x.strip(",@") for x in users.split()]
        bad_names = [x for x in display_names if x not in map_name_to_id]
        if bad_names:
            self.logger.error("For channel %s, these users can't be found: %s", channel_prefixes, bad_names)
        names_with_ids = [(x, map_name_to_id.get(x)) for x in display_names if x not in bad_names]
        known_users = [KnownUser(name, user_id) for (name, user_id) in names_with_ids]
        return channels, known_users

    def remember_channel(self, channel):
        """
        Remember the given channel. Return a bool indicating if we've already seen it
        """
        redis_channel_key = "channel:%s" % channel["id"]
        is_new = self.redis_client.setnx(redis_channel_key, channel.get("created", "0"))
        if is_new:
            # We don't want our redis instance to just continue growing, so delete the key after 60 days
            self.redis_client.expire(redis_channel_key, CHANNEL_INFO_TTL_IN_SECONDS)
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
            self.logger.error("ignored... event was missing required attributes. channel=%r", channel)
            return

        channel_id = channel["id"]
        channel_name = channel["name"]

        # Is the new channel one of the ones that we want to report?
        if self.all_channel_prefixes and \
                not any(channel_name.startswith(x) for x in self.all_channel_prefixes):
            self.logger.info("ignored... channel name doesn't start with the appropriate prefix: %s", channel_name)
            return

        # Have we already processed this channel?
        if self.remember_channel(channel):
            self.logger.info("ignored... we've already processed this channel: %s/%s", channel_id, channel_name)
            return

        # Try hard to fetch the full info about the channel
        channel_info = self.insistent_get_channel_info(channel_id)
        if not channel_info:
            self.logger.error("ignored.... failed to get information about channel (%s/%s)", channel_id, channel_name)
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
        self._post_notification(event_type, channel_info.get("channel"), creator_info.get("user"))

    # noinspection PyPep8Naming
    def _send_pretty_notification(self, event_type, channel, creator):
        """
        Send a channel creation notification to the given target channel
        """
        # Log for debugging if needed
        self.logger.info("channel: %s", json.dumps(channel))
        self.logger.info("creator: %s", json.dumps(creator))

        # Use templates for all fields in the message (even though some don't need complex substitutions).
        # The messages use the attachments format: https://api.slack.com/docs/message-attachments
        MESSAGE_TEMPLATE = {
            "fallback": "{creator_name} just created a new channel {rename_msg} :tada:\n"
                        "<#{channel_id}|{channel_name}>\n"
                        "Its purpose is: {channel_purpose} ",
            "color": random.choice(COLORS),
            "pretext": "A new channel has been created {rename_msg} :tada:",
            "author_name": "{creator_name} <@{creator_display_name}>",
            "author_icon": "{creator_image}",
            "title": "<#{channel_id}>",
            "text": "{channel_purpose}"
        }
        # Make a nicely formatted notification from the above template
        fancy_message = self._make_formatted_message(MESSAGE_TEMPLATE, channel, creator, event_type)

        # Announce the new channel in any matching announcement channels
        channel_name = channel.get("name")
        target_channels = [target for (prefix, target) in self.all_channel_prefixes_with_target_channel if channel_name.startswith(prefix)]
        for target_channel in set(target_channels):
            self.logger.info("sending to %s: %s", target_channel, json.dumps(fancy_message))
            self.slack_client.post_chat_message(target_channel, None, [fancy_message])

    def _make_formatted_message(self, message_template, channel, creator, event_type):
        # Setup all the values that will be needed for the messages
        values = {
            "creator_id": nested_get(creator, "enterprise_user", "id") or nested_get(creator, "id"),
            "creator_name": nested_get(creator, "profile", "real_name_normalized"),
            "creator_image": nested_get(creator, "profile", "image_32"),
            "creator_display_name": nested_get(creator, "profile", "display_name"),
            "channel_id": nested_get(channel, "id"),
            "channel_name": nested_get(channel, "name"),
            "channel_purpose": nested_get(channel, "purpose", "value"),
            "rename_msg": "(via renaming)" if event_type == "rename" else ""
        }
        fancy_message = {key: value.format(**values) for (key, value) in message_template.items()}
        return fancy_message

    def _post_notification(self, event_type, channel, user):
        """
        Do any post-processing required. This can include setting the channel's purpose, topic, or
        sending an intro message to the channel.

        :param event_type: Was the channel created or renamed?
        :param channel: Full channel info
        """
        # At the moment, all the post-processing is only relevant to newly created channels
        if event_type != "create":
            return

        self._post_notification_interested_users(channel, user)

        self._post_notification_jira(channel, user)

        self._april_fools_day(channel, user)

    def _post_notification_interested_users(self, channel, creator):
        channel_name = channel.get("name")

        # Calculate list of users interested in this channel
        list_of_users = [users for (prefix, users) in self.fomo_users.items() if channel_name.startswith(prefix)]
        interested_users = set(itertools.chain.from_iterable(list_of_users))
        self.logger.info("Users interested in this group: %r" % interested_users)

        # Remove the users that are already in the group
        members = channel.get("members", [])
        interested_users = [x for x in interested_users if not x.user_id in members]
        self.logger.info("Users interested in this group that are not already members: %r" % interested_users)

        # If there is no one who want to be included, we can return now
        if not interested_users:
            return

        people_to_invite = ["<@%s>" % x.display_name for x in interested_users]
        message = {
            "color": random.choice(COLORS),
            "title": "People who suffer from FOMO",
            "text": "These people would like to be invited to this group. Copy and paste the following command to invite them:\n\nDo you want join? " + " ".join(
                people_to_invite),
        }
        channel_id = channel.get("id")
        self.slack_client.post_chat_message(channel_id, None, [message])

        # Send direct messages to the invited users
        for user in interested_users:
            message = {
                "color": random.choice(COLORS),
                "pretext": "*FOMO sufferers of the world rejoice!* :tada: \n<@{creator_display_name}> has created a group that you might want to join",
                "title": "<#{channel_id}|{channel_name}>",
                "text": "{channel_purpose}",
                "footer": "If you don't want to be notified about these, please message <@phillip.piper> and he will remove you",
                "footer_icon": "https://qresolve.files.wordpress.com/2015/02/information-icon.png"
            }
            fancy_message = self._make_formatted_message(message, channel, creator, "")
            text = fancy_message.get("pretext")
            del fancy_message["pretext"]
            self.slack_client.post_chat_message(user.user_id, text, [fancy_message], as_user=True)

    def _april_fools_day(self, channel, user):

        # For testing purposes, let's limit this to just my channels
        # if not channel.get("name").startswith("jpp"):
        #     return

        # Calculate the users local time
        tz_offset = user.get("tz_offset", 0)
        user_local_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=tz_offset)
        # Is it the right day?
        target_date = datetime.date(user_local_time.date().year, 4, 1)
        if user_local_time.date() != target_date:
            self.logger.info("Can't do it. Not today. Should be %s, but is %s" % (target_date, user_local_time))
            return

        # Have we annoyed this user already?
        creator_id = channel.get("creator")
        if self._get_user_feature(creator_id, "aprilfool"):
            self.logger.info("We've already annoyed user '%s'. Skip them now" % creator_id)
            return

        channel_id = channel.get("id")
        blocks = random.choice([clippy_messages.NEW_GROUP, clippy_messages.NEW_THREAD])
        self.slack_client.post_chat_message(channel_id, None, blocks=blocks)
        self.logger.info("We annoyed user %s !" % creator_id)

    def _set_user_feature(self, user_id, feature_id):
        redis_key = "user-feature:%s:%s" % (user_id, feature_id)
        self.redis_client.set(redis_key, "true")
        self.redis_client.expire(redis_key, 60 * 60 * 24)  # only keep this info for 24 hours

    def _get_user_feature(self, user_id, feature_id):
        redis_key = "user-feature:%s:%s" % (user_id, feature_id)
        result = self.redis_client.get(redis_key)
        return True if result else False

    def _post_notification_jira(self, channel, user):
        """
        Do any post processing related to jira

        :param channel: Full channel info
        :param user: Full user info about channel creator
        """
        # If we're not configured for jira, there's nothing to do
        if not self.jira_prefix:
            return

        # If the channel isn't related to a JIRA ticket, there's nothing else to do
        channel_name = channel.get("name")
        (jira_id, channel_name_without_prefix) = self._extract_jira_id(channel_name)
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
        self.slack_client.post_chat_message(channel_id, None, [message])

        # Warn the author if the channel is just a jira ticket number
        self.logger.debug("%s -> %s" % (channel_name, channel_name_without_prefix))
        if channel_name_without_prefix == jira_id:
            message = {
                "fallback": "It's normally best to name a channel with more than just the JIRA issue number",
                "color": random.choice(COLORS),
                "title": "Friendly reminder about channel names",
                "text": "<@{creator_display_name}> It's normally better to have more descriptive channel names.\n\n"
                        "Renaming this channel to something like *#{channel_name}-what-went-wrong* will prevent the *Powers That Be* from descending in wrath upon your head :smile:\n",
                "image_url": random.choice(AVALANCHES),
                "footer": "To rename this channel, click the 'down arrow' icon at the top-left of this channel (next to the channel name), then click the 'Settings' tab, then hover over the 'Channel name' section, and click the 'Edit' button that appears.\n",
                "footer_icon": "https://qresolve.files.wordpress.com/2015/02/information-icon.png"
            }
            fancy_message = self._make_formatted_message(message, channel, user, "")
            self.slack_client.post_chat_message(channel_id, None, [fancy_message])

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
        :return: Tuple with (The jira id related to the name or None, the channel name without prefix)
        """
        for prefix in self.all_channel_prefixes:
            if channel_name.startswith(prefix):
                channel_name_without_prefix = channel_name[len(prefix):]
                match = re.match("([A-Za-z][A-Za-z0-9_]{1,32}-[0-9]{1,32})", channel_name_without_prefix)
                if match:
                    return match.group(1), channel_name_without_prefix
        return None, None

    def process_interactive_event(self, event_data):
        """
        Handle a button press event from an interactive message.

        If this process takes more than 3 seconds, Slack reports a time out to the user.
        We might want to spin off the actual calculations onto its own thread
        """
        actions = event_data.get("actions")
        if not len(actions):
            self.logger.error("payload was missing 'actions'")
            return

        channel_id = nested_get(event_data, "channel", "id")
        if not channel_id:
            self.logger.error("payload was missing 'channel.id'")
            return

        message_ts = nested_get(event_data, "container", "message_ts")
        clicked_action = actions[0].get("value", "???")
        self.logger.info("interactive. clicked_action=%s" % clicked_action)

        response = clippy_messages.RESPONSES.get(clicked_action, "unknown action: %s" % clicked_action)
        self.slack_client.update_chat_message(channel_id, ts=message_ts, blocks=response)

        if clicked_action == "click_enough":
            user_id = nested_get(event_data, "user", "id")
            self._set_user_feature(user_id, "aprilfool")
            self.logger.info("user(%s/%s) has had enough" % (user_id, nested_get(event_data, "user", "name")))

        return ""
