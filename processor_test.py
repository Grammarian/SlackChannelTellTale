import unittest
from mock import MagicMock

from processor import Processor




class TestProcessor(unittest.TestCase):

    CHANNEL_INFO_SUCCESS = {
        'ok': True,
        'channel': {
            'created': 1533784859,
            'creator': 'UAKA6GKFF',
            'id': 'CC5D77M5Y',
            'is_channel': True,
            'is_private': False,
            'members': ['UAKA6GKFF'],
            'name': 'jpp-test-2',
            'name_normalized': 'jpp-test-2',
            'previous_names': [],
            'purpose': {
                'creator': 'UAKA6GKFF',
                'last_set': 1533784860,
                'value': 'TESTING THIS AGAIN'
            },
            'topic': {
                'creator': u'UAKA6GKFF',
                'last_set': 0,
                'value': 'Channel topic'
            },
        }
    }

    USER_INFO_SUCCESS = {
        u'ok': True,
        u'user': {
            u'color': u'84b22f',
            u'deleted': False,
            u'id': u'UAKA6GKFF',
            u'is_admin': False,
            u'is_app_user': False,
            u'is_bot': False,
            u'is_owner': False,
            u'is_primary_owner': False,
            u'is_restricted': False,
            u'is_ultra_restricted': False,
            u'name': u'phillip.piper',
            u'profile': {
                u'avatar_hash': u'b413a925836f',
                u'display_name': u'phillip.piper',
                u'display_name_normalized': u'phillip.piper',
                u'email': u'phillip.piper@thetradedesk.com',
                u'first_name': u'Phillip',
                u'image_1024': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_1024.jpg',
                u'image_192': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_192.jpg',
                u'image_24': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_24.jpg',
                u'image_32': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_32.jpg',
                u'image_48': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_48.jpg',
                u'image_512': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_512.jpg',
                u'image_72': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_72.jpg',
                u'image_original': u'https://avatars.slack-edge.com/2018-05-07/360275784695_b413a925836f89c22c8b_original.jpg',
                u'is_custom_image': True,
                u'last_name': u'Piper',
                u'phone': u'+61-405615498',
                u'real_name': u'Phillip Piper',
                u'real_name_normalized': u'Phillip Piper',
                u'skype': u'',
                u'status_emoji': u'',
                u'status_expiration': 0,
                u'status_text': u'',
                u'status_text_canonical': u'',
                u'team': u'T0AT6LB9B',
                u'title': u'Developer'
            },
            u'real_name': u'Phillip Piper',
            u'team_id': u'T0AT6LB9B',
            u'tz': u'Australia/Canberra',
            u'tz_label': u'Australian Eastern Standard Time',
            u'tz_offset': 36000,
            u'updated': 1532934256
        }
    }

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
        slack_client.user_info.return_value = self.USER_INFO_SUCCESS
        slack_client.channel_info.return_value = self.CHANNEL_INFO_SUCCESS
        logger = MagicMock()

        processor = Processor("target", [], slack_client, logger=logger)
        processor.process_channel_event("create", event)
        self.assertTrue(logger.error.called)
        print(slack_client.method_calls)
        print(logger.method_calls)


if __name__ == '__main__':
    unittest.main()
