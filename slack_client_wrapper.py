class SlackClientWrapper:
    """
    This class is a wrapper around the raw slack client provided by Slack.
    It principally allows calls to Slack to be mocked out.
    """

    def __init__(self, client):
        self.client = client

    def channel_info(self, channel_id):
        return self.client.api_call("channels.info", channel=channel_id)

    def user_info(self, user_id):
        return self.client.api_call("users.info", user=user_id)

    def post_chat_message(self, channel_id, message):
        return self.client.api_call("chat.postMessage", channel=channel_id, attachments=[message])
