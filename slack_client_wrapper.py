import json
import toolbox


class SlackClientWrapper:
    """
    This class is a wrapper around the raw slack client provided by Slack.
    It principally allows calls to Slack to be mocked out.
    """

    def __init__(self, client, logger=None):
        self.client = client
        self.logger = logger or toolbox.null_logger()

    def channel_info(self, channel_id):
        self.logger.info("calling 'conversations.info': %s", channel_id)
        resp = self.client.conversations_info(channel=channel_id)
        return resp.data if resp else None

    def user_info(self, user_id):
        self.logger.info("calling 'users.info': %s", user_id)
        resp = self.client.users_info(user=user_id)
        return resp.data if resp else None

    def users(self):
        self.logger.info("calling 'users.list'")
        response = self.client.users_list()
        users = []
        while response.get("ok"):
            users.extend(response.get("members"))
            next_cursor = toolbox.nested_get(response.data, "response_metadata", "next_cursor")
            if next_cursor:
                response = self.client.users_list(cursor=next_cursor)
            else:
                break
        self.logger.info("found %d users", len(users))
        return users

    def post_chat_message(self, channel_id, text=None, attachments=[], blocks=None, as_user=False):
        self.logger.info("sending to %s: text=%s, attachments=%s, blocks=%s", channel_id, text, json.dumps(attachments),
                         json.dumps(blocks))
        return self.client.api_call(
            api_method="chat.postMessage",
            json={
                'channel': channel_id,
                'text': text,
                'unfurl_media': True,
                'as_user': as_user,
                'attachments': attachments or None,
                'blocks': blocks
            }
        )

    def update_chat_message(self, channel_id, ts, text=None, attachments=[], blocks=None):
        self.logger.info("updating msg %s/%s: text=%s, attachments=%s, blocks=%s", channel_id, ts, text,
                         json.dumps(attachments), json.dumps(blocks))
        return self.client.api_call(
            api_method="chat.update",
            json={
                'channel': channel_id,
                'ts': ts,
                'parse': "full",
                'link_names': True,
                'unfurl_media': True,
                'text': text,
                'attachments': attachments or None,
                'blocks': blocks
            }
        )



