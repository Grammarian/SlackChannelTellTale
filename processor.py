import json
import logging
import random
import time

from in_memory_redis import InMemoryRedis


def nested_get(d, *keys):
    """
    Iteratively fetch keys from nested dictionaries
    """
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, None)
        else:
            return None
    return d


class Processor:
    """
    This class processes slack events and sends notification messages as required
    """

    def __init__(self, target_channel_id, channel_prefixes, slack_client, redis_client=None, logger=None):
        self.target_channel_id = target_channel_id
        self.channel_prefixes = channel_prefixes
        self.slack_client = slack_client
        self.redis_client = redis_client or InMemoryRedis()
        self.logger = logger or logging.getLogger("Processor")

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

        # Use templates for all fields in the message (even though some don't need complex substitutions)
        FALLBACK_MESSAGE = "{creator_name} just created a new channel :tada:\n" \
                           "<#{channel_id}|{channel_name}>\n" \
                           "Its purpose is: {channel_purpose} "
        PRETEXT_MESSAGE = "A new channel has been created {rename_msg} :tada:"
        AUTHOR_NAME = "{creator_name} <@{creator_id}>"
        TITLE = "<#{channel_id}>"
        CREATOR_IMAGE = "{creator_image}"
        PURPOSE = "{channel_purpose}"

        COLORS = ["#ff1744", "#f50057", "#d500f9", "#651fff", "#3d5afe", "#2979ff", "#00b0ff", "#00e5ff", "#1de9b6",
                  "#00e676", "#76ff03", "#ffea00", "#ffc400", "#ff9100", "#ff3d00"]

        # Make a nicely format notification
        fancy_message = {
            "fallback": FALLBACK_MESSAGE.format(**values),
            "color": random.choice(COLORS),
            "pretext": PRETEXT_MESSAGE.format(**values),
            "author_name": AUTHOR_NAME.format(**values),
            "author_icon": CREATOR_IMAGE.format(**values),
            "title": TITLE.format(**values),
            "text": PURPOSE.format(**values)
        }
        self.logger.info("sending to %s: %s", self.target_channel_id, json.dumps(fancy_message))

        # Finally, announce the new channel in the announcement channel
        self.slack_client.post_chat_message(self.target_channel_id, fancy_message)
