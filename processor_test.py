import unittest
from mock import MagicMock

from processor import Processor

class TestProcessor(unittest.TestCase):

    def test_create(self):
        event = {
            "type": "event_callback",
            "event": {
                "event_ts": "1537991036.000100",
                "type": "channel_created",
                "channel": {
                    "name_normalized": "dev-so-trial-notify",
                    "name": "dev-so-trial-notify",
                    "creator": "U0BPCEYR4",
                    "created": 1537991036,
                    "id": "CD1USGKT7",
                }
            }
        }
        slack_client = MagicMock()
        redis_client = None
        logger = MagicMock()

        processor = Processor("target", [], slack_client, redis_client, logger)
        processor.process_channel_event("create", event)
        self.assertTrue(logger.error.called)
        # print(logger.method_calls)


if __name__ == '__main__':
    unittest.main()