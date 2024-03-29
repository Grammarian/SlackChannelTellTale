import random
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
            "creator": "CREATORID1",
            "created": 1537991036,
            "id": "CHANNELID1",
        }
    }
}

CREATE_EVENT_JIRA = {
    "type": "event_callback",
    "event": {
        "event_ts": "1537991036.000100",
        "type": "channel_created",
        "channel": {
            "name_normalized": "dev-PROJ-1234-dev-test-1",
            "name": "dev-PROJ-1234-dev-test-1",
            "creator": "CREATORID1",
            "created": 1537991036,
            "id": "CHANNELID1",
        }
    }
}

CREATE_EVENT_FUN = {
    "type": "event_callback",
    "event": {
        "event_ts": "1537991036.000100",
        "type": "channel_created",
        "channel": {
            "name_normalized": "fun-dogs",
            "name": "fun-dogs",
            "creator": "CREATORID2",
            "created": 1537991036,
            "id": "CHANNELID2",
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
            "creator": "CREATORID1",
            "created": 1537991036,
            "id": "CHANNELID1",
        }
    }
}

CHANNEL_INFO_SUCCESS = {
    "ok": True,
    "channel": {
        "created": 1533784859,
        "creator": "USERID1",
        "id": "CHANNELID1",
        "is_channel": True,
        "members": ["USERID1"],
        "name": "dev-test-2",
        "name_normalized": "dev-test-2",
        "purpose": {
            "creator": "USERID1",
            "value": "TESTING THIS"
        },
        "topic": {
            "creator": "USERID1",
            "value": "Channel topic"
        },
    }
}

CHANNEL_INFO_SUCCESS_JIRA = {
    "ok": True,
    "channel": {
        "created": 1533784859,
        "creator": "USERID1",
        "id": "CHANNELID1",
        "is_channel": True,
        "members": ["USERID1"],
        "name_normalized": "dev-PROJ-1234-dev-test-1",
        "name": "dev-PROJ-1234-dev-test-1",
        "purpose": {
            "creator": "USERID1",
            "value": "TESTING THIS"
        },
        "topic": {
            "creator": "USERID1",
            "value": "Channel topic"
        },
    }
}

CHANNEL_INFO_SUCCESS_FUN = {
    "ok": True,
    "channel": {
        "created": 1533784859,
        "creator": "CREATORID2",
        "id": "CHANNELID2",
        "is_channel": True,
        "members": ["CREATORID2"],
        "name_normalized": "fun-dogs",
        "name": "fun-dogs",
        "purpose": {
            "creator": "CREATORID2",
            "value": "Cute photos of dogs"
        },
        "topic": {
            "creator": "CREATORID2",
            "value": "Cute photos of dogs"
        },
    }
}

USER_INFO_SUCCESS = {
    "ok": True,
    "user": {
        "id": "USERID1",
        "name": "phillip.piper",
        "profile": {
            "display_name": "phillip.piper",
            "display_name_normalized": "phillip.piper",
            "email": "phillip.piper@thetradedesk.com",
            "first_name": "Phillip",
            "image_24": "https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_24.jpg",
            "image_32": "https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_32.jpg",
            "last_name": "Piper",
            "real_name": "Phillip Piper",
            "real_name_normalized": "Phillip Piper",
            "team": "T0AT6LB9B",
            "title": "Developer"
        },
        "real_name": "Phillip Piper"
    }
}


class TestProcessor(unittest.TestCase):

    def setUp(self):
        random.seed(1)  # Make random behave the same each time
        self.maxDiff = None

    def test_create(self):
        expected_message = {
            "author_icon": "https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_32.jpg",
            "author_name": "Phillip Piper <@phillip.piper>",
            "fallback": "Phillip Piper just created a new channel  :tada:\n<#CHANNELID1|dev-test-2>\nIts purpose is: TESTING THIS ",
            "pretext": "A new channel has been created  :tada:",
            "text": "TESTING THIS",
            "title": "<#CHANNELID1>"
        }
        event = CREATE_EVENT
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS
        logger = MagicMock()
        target_channel = "target"
        prefixes = ["dev-"]

        processor = Processor({target_channel: prefixes}, slack_client, logger=logger)
        processor.process_channel_event("create", event)

        self.assertFalse(logger.error.called)
        slack_client.channel_info.assert_called_with("CHANNELID1")
        slack_client.user_info.assert_called_with("USERID1")
        self.assertTrue(slack_client.post_chat_message.called)
        ((posted_channel, posted_text, posted_attachments), _) = slack_client.post_chat_message.call_args
        self.assertEqual(target_channel, posted_channel)
        self.assertEqual(1, len(posted_attachments))
        attachment = posted_attachments[0]
        del attachment['color']  # the color of the message is random and can't be tested
        self.assertDictEqual(attachment, expected_message)

    def test_create_channel_in_secondary_channel_group(self):
        expected_message = {
            "author_icon": "https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_32.jpg",
            "author_name": "Phillip Piper <@phillip.piper>",
            "fallback": "Phillip Piper just created a new channel  :tada:\n<#CHANNELID2|fun-dogs>\nIts purpose is: Cute photos of dogs ",
            "pretext": "A new channel has been created  :tada:",
            "text": "Cute photos of dogs",
            "title": "<#CHANNELID2>"
        }
        event = CREATE_EVENT_FUN
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS_FUN
        logger = MagicMock()
        target_channel = "target"
        prefixes = {"other_channel": ["prefix1", "prefix2"], target_channel: ["fun-"]}

        processor = Processor(prefixes, slack_client, logger=logger)
        processor.process_channel_event("create", event)

        self.assertFalse(logger.error.called)
        slack_client.channel_info.assert_called_with("CHANNELID2")
        slack_client.user_info.assert_called_with("CREATORID2")
        self.assertTrue(slack_client.post_chat_message.called)
        ((posted_channel, posted_text, posted_attachments), _) = slack_client.post_chat_message.call_args
        self.assertEqual(target_channel, posted_channel)
        self.assertEqual(1, len(posted_attachments))
        attachment = posted_attachments[0]
        del attachment['color']  # the color of the message is random and can't be tested
        self.assertDictEqual(attachment, expected_message)

    def test_create_channel_with_multiple_targets(self):
        event = CREATE_EVENT_FUN
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS_FUN
        logger = MagicMock()
        prefixes = {"target1": ["prefix-", "fun-dog"], "target2": ["different", "fun-d"], "target3": ["x-", "fun-"]}

        processor = Processor(prefixes, slack_client, logger=logger)
        processor.process_channel_event("create", event)

        self.assertFalse(logger.error.called)
        self.assertEqual(3, slack_client.post_chat_message.call_count)
        self.assertEqual(["target1", "target2", "target3"],
                         sorted(x.args[0] for x in slack_client.post_chat_message.call_args_list))

    def test_create_post_notify(self):
        expected_message = {
            "fallback": "This channel is related to this JIRA issue: https://something/jira/browse/PROJ-1234",
            "title": "Related JIRA Issue",
            "text": "https://something/jira/browse/PROJ-1234"
        }
        event = CREATE_EVENT_JIRA
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS_JIRA
        logger = MagicMock()
        target_channel = "target"
        prefixes = ["dev-"]

        processor = Processor({target_channel: prefixes}, slack_client, logger=logger, jira="https://something")
        processor.process_channel_event("create", event)

        self.assertFalse(logger.error.called)
        self.assertEqual(2, slack_client.post_chat_message.call_count)
        ((posted_channel, posted_text, posted_attachments), _) = slack_client.post_chat_message.call_args
        self.assertEqual("CHANNELID1", posted_channel)
        self.assertEqual(1, len(posted_attachments))
        attachment = posted_attachments[0]
        del attachment['color']  # the color of the message is random and can't be tested
        self.assertDictEqual(attachment, expected_message)

    def test_rename(self):
        expected_message = {
            "author_icon": "https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_32.jpg",
            "author_name": "Phillip Piper <@phillip.piper>",
            "fallback": "Phillip Piper just created a new channel (via renaming) :tada:\n<#CHANNELID1|dev-test-2>\nIts purpose is: TESTING THIS ",
            "pretext": "A new channel has been created (via renaming) :tada:",
            "text": "TESTING THIS",
            "title": "<#CHANNELID1>"
        }
        event = RENAME_EVENT
        slack_client = MagicMock()
        slack_client.user_info.return_value = USER_INFO_SUCCESS
        slack_client.channel_info.return_value = CHANNEL_INFO_SUCCESS
        logger = MagicMock()
        target_channel = "target"
        prefixes = ["dev-"]

        processor = Processor({target_channel: prefixes}, slack_client, logger=logger)
        processor.process_channel_event("rename", event)

        self.assertFalse(logger.error.called)
        slack_client.channel_info.assert_called_with("CHANNELID1")
        slack_client.user_info.assert_called_with("USERID1")
        self.assertTrue(slack_client.post_chat_message.called)
        ((posted_channel, posted_text, posted_attachments), _) = slack_client.post_chat_message.call_args
        self.assertEqual(target_channel, posted_channel)
        self.assertEqual(1, len(posted_attachments))
        attachment = posted_attachments[0]
        del attachment['color']  # the color of the message is random and can't be tested
        self.assertDictEqual(attachment, expected_message)

    def test_ignore_non_matching_names(self):
        event = RENAME_EVENT
        slack_client = MagicMock()
        logger = MagicMock()
        processor = Processor({"target": ["only-", "accept-", "these-"]}, slack_client, logger=logger)
        processor.process_channel_event("rename", event)

        logger.info.assert_called_with("ignored... channel name doesn't start with the appropriate prefix: %s",
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
        processor = Processor({"target": ["dev-"]}, slack_client, redis_client=redis, logger=logger)
        processor.process_channel_event("rename", event)

        self.assertFalse(logger.error.called)
        self.assertFalse(slack_client.post_chat_message.called)
        logger.info.assert_called_with("ignored... we've already processed this channel: %s/%s", channel_id,
                                       channel_name)

    def test_jira_id_extraction(self):
        slack_client = MagicMock()
        processor = Processor({"target": ["prefix1-", "something2_", "bug-"]}, slack_client)
        tests = [
            ("prefix1-not-jira-issue", None),
            ("prefix1-some-text-and-a-number-9999-like-this", None),  # Jira id has to be immediately after prefix
            ("prefix1-number-9999-like-this", "number-9999"),
            ("bug-xyz-1234", "xyz-1234"),
            ("bug-X1-01234", "X1-01234"),
            ("bug-X-1", None),  # Project prefix has two have at least two characters
            ("prefix1-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-1234", None),  # Just..no
            ("prefix1-IM-1234-some-description", "IM-1234"),
            ("something2_IM-1234-some-description", "IM-1234"),
        ]
        for (name, expected_jira_id) in tests:
            (jira_id, channel_name_without_prefix) = processor._extract_jira_id(name)
            self.assertEqual(expected_jira_id, jira_id)


if __name__ == '__main__':
    unittest.main()
