import random
import unittest
from mock import MagicMock

from message_generator import MessageGenerator


class TestMessageGenerator(unittest.TestCase):

    def setUp(self):
        random.seed(1)  # Make random behave the same each time
        self.maxDiff = None

    def test_initial(self):
        image_searcher = MagicMock()
        image_searcher.random.return_value = "http://some.com/image.png"
        logger = MagicMock()
        generator = MessageGenerator(image_searcher, logger)
        generator.start(search_terms="very cute dogs")
        msg = generator.get_msg()
        self.assertIsNotNone(msg)
        self.assertIsNone(msg.get("text"))
        attachments = msg.get("attachments")
        self.assertIsNotNone(attachments)
        self.assertDictEqual(attachments[0], {
            'color': '#71aef2',
            'pretext': '*I found this photo using the following search terms: cute dogs very.*',
            'image_url': 'http://some.com/image.png',
            'attachment_type': 'default'
        })
        self.assertDictEqual(attachments[1], {
            'color': '#71aef2',
            'title': 'Do you want to keep this picture?',
            'callback_id': 'choose_photo',
            'attachment_type': 'default',
            'actions': [{
                'text': "Yes, that's great",
                'style': 'primary',
                'type': 'button',
                'name': 'photo',
                'value': 'keep'
            }, {
                'text': 'No, show something else',
                'type': 'button',
                'name': 'photo',
                'value': 'next'
            }, {
                'text': 'Random',
                'type': 'button',
                'name': 'photo',
                'value': 'random'
            }, {
                'text': 'Stop suggesting',
                'style': 'danger',
                'type': 'button',
                'name': 'photo',
                'value': 'stop'
            }],
        })

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
        self.assertIsNone(msg.get("text"))
        attachments = msg.get("attachments")
        self.assertIsNotNone(attachments)
        self.assertDictEqual(attachments[0], {
            'color': '#71aef2',
            'pretext': "*I have no idea what this channel is about. So here's a cute animal photo.*",
            'image_url': 'http://cute.com/animal',
            'attachment_type': 'default'
        })
        self.assertDictEqual(attachments[1], {
            'color': '#c356ea',
            'title': 'Keep this one?',
            'callback_id': 'choose_photo',
            'attachment_type': 'default',
            'actions': [{
                'text': "Yes, that's great",
                'style': 'primary',
                'type': 'button',
                'name': 'photo',
                'value': 'keep'
            }, {
                'text': 'No, show something else',
                'type': 'button',
                'name': 'photo',
                'value': 'next'
            }, {
                'text': 'Random',
                'type': 'button',
                'name': 'photo',
                'value': 'random'
            }, {
                'text': 'Stop suggesting',
                'style': 'danger',
                'type': 'button',
                'name': 'photo',
                'value': 'stop'
            }],
        })

    def test_action_keep(self):
        image_searcher = MagicMock()
        image_searcher.random.return_value = "http://some.com/image.png"
        logger = MagicMock()
        generator = MessageGenerator(image_searcher, logger)
        generator.start(search_terms="cute dogs")
        generator.transition("keep")
        msg = generator.get_msg()
        self.assertIsNotNone(msg)
        self.assertIsNone(msg.get("text"))
        attachments = msg.get("attachments")
        self.assertIsNotNone(attachments)
        self.assertDictEqual(attachments[0], {
            'color': '#c356ea',
            'pretext': "*You chose this as the photo for this channel :heart:*",
            'image_url': 'http://some.com/image.png',
            'attachment_type': 'default'
        })


if __name__ == '__main__':
    unittest.main()
