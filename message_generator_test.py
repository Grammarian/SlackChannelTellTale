import unittest
from mock import MagicMock

from in_memory_redis import InMemoryRedis
from message_generator import MessageGenerator
from processor import Processor


class TestMessageGenerator(unittest.TestCase):

    def test_initial(self):
        image_searcher = MagicMock()
        image_searcher.random.return_value = "http://some.com/image.png"
        logger = MagicMock()
        generator = MessageGenerator(image_searcher, logger)
        generator.start(search_terms="cute dogs")
        msg = generator.get_msg()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.get("text"), "I found this photo using the following search terms: cute dogs\n\nhttp://some.com/image.png")
        self.assertIsNotNone(msg.get("attachment"))

    def test_initial_not_found(self):
        def mock_random(terms, rating="G", lang="en-US", exclude=[]):
            return None if terms == "particle physics" else "http://cute.com/animal"
        image_searcher = MagicMock()
        image_searcher.random.side_effect = mock_random
        logger = MagicMock()
        generator = MessageGenerator(image_searcher, logger)
        generator.start(search_terms="particle physics")
        msg = generator.get_msg()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.get("text"), "I have no idea what this channel is about. So here's a cute animal photo:\n\nhttp://cute.com/animal")
        self.assertIsNotNone(msg.get("attachment"))

    def test_action_keep(self):
        image_searcher = MagicMock()
        image_searcher.random.return_value = "http://some.com/image.png"
        logger = MagicMock()
        generator = MessageGenerator(image_searcher, logger)
        generator.start(search_terms="cute dogs")
        generator.transition("keep")
        msg = generator.get_msg()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.get("text"),
                         "You chose this photo as the photo for this channel :heart:\n\nhttp://some.com/image.png")
        self.assertIsNone(msg.get("attachment"))

    # def test_jira_id_extraction(self):
    #     slack_client = MagicMock()
    #     processor = Processor("target", ["prefix1-", "something2_", "bug-"], slack_client)
    #     tests = [
    #         ("prefix1-not-jira-issue", None),
    #         ("prefix1-some-text-and-a-number-9999-like-this", None),  # Jira id has to be immediately after prefix
    #         ("prefix1-number-9999-like-this", "number-9999"),
    #         ("bug-xyz-1234", "xyz-1234"),
    #         ("bug-X1-01234", "X1-01234"),
    #         ("bug-X-1", None),  # Project prefix has two have at least two characters
    #         ("prefix1-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-1234", None),  # Just..no
    #         ("prefix1-IM-1234-some-description", "IM-1234"),
    #         ("something2_IM-1234-some-description", "IM-1234"),
    #     ]
    #     for (name, jira_id) in tests:
    #         self.assertEqual(jira_id, processor._extract_jira_id(name))


if __name__ == '__main__':
    unittest.main()
