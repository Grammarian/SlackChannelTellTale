import unittest
from mock import MagicMock

from in_memory_redis import InMemoryRedis
from processor import Processor

CREATE_EVENT = {
    "type": "event_callback",
    "event": {
        "event_ts": "1537991036.000100",
        "type": "channel_created",
        "channel": {
            "name_normalized": "dev-test-1",
            "name": "dev-test-1",
            "creator": "U0BPCEYR4",
            "created": 1537991036,
            "id": "CD1USGKT7",
        }
    }
}

RENAME_EVENT = {
    "type": "event_callback",
    "event": {
        "event_ts": "1537991036.000100",
        "type": "channel_renamed",
        "channel": {
            "name_normalized": "dev-so-trial-notify",
            "name": "dev-so-trial-notify",
            "creator": "U0BPCEYR4",
            "created": 1537991036,
            "id": "CD1USGKT7",
        }
    }
}

CHANNEL_INFO_SUCCESS = {
    'ok': True,
    'channel': {
        'created': 1533784859,
        'creator': 'UAKA6GKFF',
        'id': 'CC5D77M5Y',
        'is_channel': True,
        'members': ['UAKA6GKFF'],
        'name': 'jpp-test-2',
        'name_normalized': 'jpp-test-2',
        'purpose': {
            'creator': 'UAKA6GKFF',
            'value': 'TESTING THIS'
        },
        'topic': {
            'creator': u'UAKA6GKFF',
            'value': 'Channel topic'
        },
    }
}

USER_INFO_SUCCESS = {
    u'ok': True,
    u'user': {
        u'id': u'UAKA6GKFF',
        u'name': u'phillip.piper',
        u'profile': {
            u'display_name': u'phillip.piper',
            u'display_name_normalized': u'phillip.piper',
            u'email': u'phillip.piper@thetradedesk.com',
            u'first_name': u'Phillip',
            u'image_24': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_24.jpg',
            u'last_name': u'Piper',
            u'real_name': u'Phillip Piper',
            u'real_name_normalized': u'Phillip Piper',
            u'team': u'T0AT6LB9B',
            u'title': u'Developer'
        },
        u'real_name': u'Phillip Piper'
    }
}


class TestProcessor(unittest.TestCase):

    def test_create(self):
        expected_message = {
            'author_icon': 'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_24.jpg',
            'author_name': 'Phillip Piper <@UAKA6GKFF>',
            'fallback': 'Phillip Piper just created a new channel  :tada:\n<#CC5D77M5Y|jpp-test-2>\nIts purpose is: TESTING THIS ',
            'pretext': 'A new channel has been created  :tada:',
            'text': 'TESTING THIS',
            'title': '<#CC5D77M5Y>'
        }
        event = CREATE_EVENT
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS
        logger = MagicMock()
        target_channel = "target"

        processor = Processor(target_channel, [], slack_client, logger=logger)
        processor.process_channel_event("create", event)

        self.assertFalse(logger.error.called)
        slack_client.channel_info.assert_called_with("CD1USGKT7")
        slack_client.user_info.assert_called_with("UAKA6GKFF")
        self.assertTrue(slack_client.post_chat_message.called)
        ((posted_channel, posted_message), _) = slack_client.post_chat_message.call_args
        self.assertEqual(target_channel, posted_channel)
        del posted_message['color']  # the color of the message is random and can't be tested
        self.assertDictEqual(posted_message, expected_message)

    def test_rename(self):
        expected_message = {
            'author_icon': 'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_24.jpg',
            'author_name': 'Phillip Piper <@UAKA6GKFF>',
            'fallback': 'Phillip Piper just created a new channel (via renaming) :tada:\n<#CC5D77M5Y|jpp-test-2>\nIts purpose is: TESTING THIS ',
            'pretext': 'A new channel has been created (via renaming) :tada:',
            'text': 'TESTING THIS',
            'title': '<#CC5D77M5Y>'
        }
        event = RENAME_EVENT
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS
        logger = MagicMock()
        target_channel = "target"

        processor = Processor(target_channel, [], slack_client, logger=logger)
        processor.process_channel_event("rename", event)

        self.assertFalse(logger.error.called)
        slack_client.channel_info.assert_called_with("CD1USGKT7")
        slack_client.user_info.assert_called_with("UAKA6GKFF")
        self.assertTrue(slack_client.post_chat_message.called)
        ((posted_channel, posted_message), _) = slack_client.post_chat_message.call_args
        self.assertEqual(target_channel, posted_channel)
        del posted_message['color']  # the color of the message is random and can't be tested
        self.assertDictEqual(posted_message, expected_message)

    def test_ignore_non_matching_names(self):
        event = RENAME_EVENT
        slack_client = MagicMock()
        logger = MagicMock()
        processor = Processor("target", ["only-", "accept-", "these-"], slack_client, logger=logger)
        processor.process_channel_event("rename", event)

        logger.info.assert_called_once_with("ignored... channel name doesn't start with the appropriate prefix: %s",
                                            "dev-so-trial-notify")
        self.assertFalse(logger.error.called)
        self.assertFalse(slack_client.post_chat_message.called)

    def test_ignore_second_event(self):
        event = RENAME_EVENT
        channel_id = event["event"]["channel"]["id"]
        channel_name = event["event"]["channel"]["name"]

        # Create a redis instance and tell it that it has already processed this channel
        redis = InMemoryRedis()
        redis.setnx("channel:%s" % channel_id, "already-seen")

        slack_client = MagicMock()
        logger = MagicMock()
        processor = Processor("target", [], slack_client, redis_client=redis, logger=logger)
        processor.process_channel_event("rename", event)

        self.assertFalse(logger.error.called)
        self.assertFalse(slack_client.post_chat_message.called)
        logger.info.assert_called_once_with("ignored... we've already processed this channel: %s/%s", channel_id,
                                            channel_name)


if __name__ == '__main__':
    unittest.main()
