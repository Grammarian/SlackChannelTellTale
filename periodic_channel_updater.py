import random

from toolbox import nested_get, null_logger

COLORS = ["#ff1744", "#f50057", "#d500f9", "#651fff", "#3d5afe", "#2979ff", "#00b0ff", "#00e5ff",
          "#1de9b6", "#00e676", "#76ff03", "#ffea00", "#ffc400", "#ff9100", "#ff3d00"]


class MessageTemplate:

    @staticmethod
    def announcement(event_type, channel, creator, statistics):
        """
        Send a channel creation notification to the given target channel
        """

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
        template = {
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
        fancy_message = {key: value.format(**values) for (key, value) in template.items()}
        return {"attachments": [fancy_message]}


class ChannelStateUpdater:
    """
    Every so often, update the announcement message with current channel statistics.
    """
    def __init__(self, redis_client, slack_client, logger=None):
        self.redis_client = redis_client
        self.slack_client = slack_client
        self.logger = logger or null_logger()

    def execute(self):
        for (channel_id, message_ts) in self.channels_to_check():
            self._update_channel_statistics(channel_id, message_ts)

    def _make_redis_key(self, channel_id):
        return "channel-initial-message:" + channel_id

    def channels_to_check(self):
        for key in self.redis_client.keys(self._make_redis_key("*")):
            channel_id = key.split(":")[-1]
            message_ts = self.redis_client.get(key)
            if channel_id and message_ts:
                yield (channel_id, message_ts)

    def _update_channel_statistics(self, channel_id, message_ts):
        channel_stats = self._get_channel_stats(channel_id)
        if not channel_stats:
            return

        templator = MessageTemplate()
        msg = templator.generate_msg()
        self.slack_client.update_chat_message(channel_id, message_ts, attachments=msg.get("attachments"))
