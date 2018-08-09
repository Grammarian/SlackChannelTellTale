import os
import logging
import pprint

from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient

# Constants
CHANNEL_PREFIXES = ["api-", "bi-", "bug-", "dat", "dev-", "ftr-", "im-", "prj-", "scrum", "tf-", "tpc-", "jpp-"]
MESSAGE = "*%s* just created a new channel :tada:\n<#%s|%s>\nIts purpose is: %s"
COLORS = ["#ff1744", "#f50057", "#d500f9", "#651fff", "#3d5afe", "#2979ff", "#00b0ff", "#00e5ff", "#1de9b6", "#00e676", "#76ff03", "#ffea00", "#ffc400", "#ff9100", "#ff3d00" ]

# Get environment settings
DEBUG = bool(os.environ.get("DEBUG"))
PORT = os.environ.get("PORT") or 3000
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]
TARGET_CHANNEL_ID = os.environ["TARGET_CHANNEL_ID"]

# Initialize logging
FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(thread)d | %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)
_logger = logging.getLogger("ChannelTellTale")
 
# Initialize our slack interfaces
slack_events_adapter = SlackEventAdapter(SLACK_VERIFICATION_TOKEN, "/slack/events")
slack_client = SlackClient(SLACK_BOT_TOKEN)

event_count = 0


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


@slack_events_adapter.on("channel_created")
def handle_channel_created(event_data):
    """
    Event callback when a new channel is created
    """
    global event_count
    event_count += 1
    _logger.info("received event (%d): %s", event_count, repr(event_data))

    # Make sure the event structure is sensible
    channel = nested_get(event_data, "event", "channel")
    if not channel or \
       "id" not in channel or \
       "name" not in channel or \
       "creator" not in channel:
        _logger.error("ignored... event was missing require attributes")
        return

    # Is the new channel one of the ones that we want to report?
    channel_name = channel["name"]
    if not any(channel_name.startswith(prefix) for prefix in CHANNEL_PREFIXES):
        _logger.info("ignored... channel name doesn't start with the appropriate prefix: %s", channel_name)
        return

    # Fetch the full info about the channel
    channel_info = slack_client.api_call("channels.info", channel=channel["id"])    
    if not channel_info or not channel_info.get("ok"):
        _logger.error("ignored... fetching of channel failed: %s", pprint.pformat(channel_info))
        return

    # Fetch the full info about the creator of the channel
    creator_info = slack_client.api_call("users.info", user=channel["creator"])
    if not creator_info or not creator_info.get("ok"):
        _logger.error("ignored... fetching of creator failed: %s", pprint.pformat(creator_info))
        return

    # Log for debugging if needed
    # _logger.info("channel_info: %s", pprint.pformat(channel_info))
    # _logger.info("creator_info: %s", pprint.pformat(creator_info))

    # Make a nicely format notification
    creater_id = nested_get(creator_info, "user", "id")
    creater_name = nested_get(creator_info, "user", "profile", "real_name_normalized")
    creater_image = nested_get(creator_info, "user", "profile", "image_24")
    channel_id = nested_get(channel_info, "channel", "id"), 
    channel_name = nested_get(channel_info, "channel", "name"), 
    channel_purpose = nested_get(channel_info, "channel", "purpose", "value")
    message = MESSAGE % (
        creater_name, 
        channel_id, 
        channel_name, 
        channel_purpose
    )
    fancy_message = {
        "fallback": message,
        "color": COLORS[event_count % len(COLORS)],
        "pretext": "A new channel has been created :tada:",
        "author_name": "%s <@%s>" % (creater_name, creater_id),
        "author_icon": creater_image,
        "title": "<#%s>" % channel_id,
        "text": channel_purpose
    }
    _logger.info("sending to %s: %s", TARGET_CHANNEL_ID, repr(fancy_message))

    # Finally, announce the new channel in the announcement channel
    slack_client.api_call("chat.postMessage", channel=TARGET_CHANNEL_ID, attachments=[fancy_message])


def main():
    _logger.info("Starting server at %d", PORT)
    _logger.info("Listening for channels created with any of these prefixes: %s", CHANNEL_PREFIXES)
    slack_events_adapter.start(port=PORT, debug=DEBUG)

if __name__ == "__main__":
    main()
 
 # Example structures
example_event = {
    u'api_app_id': u'AC4HTQVH9',
    u'authed_users': [u'UAKA6GKFF'],
    u'event': {u'channel': {u'created': 1533787143,
                            u'creator': u'UAKA6GKFF',
                            u'id': u'CC59HFBQB',
                            u'is_channel': True,
                            u'is_org_shared': False,
                            u'is_shared': False,
                            u'name': u'jpp-test-6',
                            u'name_normalized': u'jpp-test-6'},
                u'event_ts': u'1533787143.000082',
                u'type': u'channel_created'},
    u'event_id': u'EvC56C063W',
    u'event_time': 1533787143,
    u'team_id': u'T0AT6LB9B',
    u'token': u'I6SD1P4kCRrXhecjS8xC3y08',
    u'type': u'event_callback'
}
channel_info = {u'channel': {u'created': 1533784859,
              u'creator': u'UAKA6GKFF',
              u'id': u'CC5D77M5Y',
              u'is_archived': False,
              u'is_channel': True,
              u'is_general': False,
              u'is_member': False,
              u'is_mpim': False,
              u'is_org_shared': False,
              u'is_private': False,
              u'is_shared': False,
              u'members': [u'UAKA6GKFF'],
              u'name': u'jpp-test-2',
              u'name_normalized': u'jpp-test-2',
              u'previous_names': [],
              u'purpose': {u'creator': u'UAKA6GKFF',
                           u'last_set': 1533784860,
                           u'value': u'TESTING THIS AGAIN'},
              u'topic': {u'creator': u'', u'last_set': 0, u'value': u''},
              u'unlinked': 0},
 u'headers': {u'Access-Control-Allow-Origin': u'*',
              u'Cache-Control': u'private, no-cache, no-store, must-revalidate',
              u'Connection': u'keep-alive',
              u'Content-Encoding': u'gzip',
              u'Content-Length': u'273',
              u'Content-Type': u'application/json; charset=utf-8',
              u'Date': u'Thu, 09 Aug 2018 03:22:06 GMT',
              u'Expires': u'Mon, 26 Jul 1997 05:00:00 GMT',
              u'Pragma': u'no-cache',
              u'Referrer-Policy': u'no-referrer',
              u'Server': u'Apache',
              u'Strict-Transport-Security': u'max-age=31536000; includeSubDomains; preload',
              u'Vary': u'Accept-Encoding',
              u'Via': u'1.1 405a549b9f9e9738369bdac85c52a997.cloudfront.net (CloudFront)',
              u'X-Accepted-OAuth-Scopes': u'channels:read,read',
              u'X-Amz-Cf-Id': u'UmRzco5-z_7HV9ufVe7ZghR3QPndauLRPKlxUAy77Azz92D6BzujVQ==',
              u'X-Cache': u'Miss from cloudfront',
              u'X-Content-Type-Options': u'nosniff',
              u'X-OAuth-Scopes': u'identify,bot:basic',
              u'X-Slack-Backend': u'h',
              u'X-Slack-Req-Id': u'27b53ae9-b0bb-4275-8e22-231e7c0fde27',
              u'X-Via': u'haproxy-www-mbmu',
              u'X-XSS-Protection': u'0'},
 u'ok': True}
creator_info = {u'headers': {u'Access-Control-Allow-Origin': u'*',
              u'Cache-Control': u'private, no-cache, no-store, must-revalidate',
              u'Connection': u'keep-alive',
              u'Content-Encoding': u'gzip',
              u'Content-Length': u'563',
              u'Content-Type': u'application/json; charset=utf-8',
              u'Date': u'Thu, 09 Aug 2018 03:22:07 GMT',
              u'Expires': u'Mon, 26 Jul 1997 05:00:00 GMT',
              u'Pragma': u'no-cache',
              u'Referrer-Policy': u'no-referrer',
              u'Server': u'Apache',
              u'Strict-Transport-Security': u'max-age=31536000; includeSubDomains; preload',
              u'Vary': u'Accept-Encoding',
              u'Via': u'1.1 afd59cef03b7aa29391f7aa40742086f.cloudfront.net (CloudFront)',
              u'X-Accepted-OAuth-Scopes': u'users:read,read',
              u'X-Amz-Cf-Id': u'zaUBHM7svbuznaKnHQJVj4907xX4E0LkwYO44Wu_fGc6SUIlYVPoWQ==',
              u'X-Cache': u'Miss from cloudfront',
              u'X-Content-Type-Options': u'nosniff',
              u'X-OAuth-Scopes': u'identify,bot:basic',
              u'X-Slack-Backend': u'h',
              u'X-Slack-Req-Id': u'8154bce6-9281-438b-994a-87e567b458eb',
              u'X-Via': u'haproxy-www-azqr',
              u'X-XSS-Protection': u'0'},
 u'ok': True,
 u'user': {u'color': u'84b22f',
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
           u'profile': {u'avatar_hash': u'b413a925836f',
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
                        u'title': u'Developer'},
           u'real_name': u'Phillip Piper',
           u'team_id': u'T0AT6LB9B',
           u'tz': u'Australia/Canberra',
           u'tz_label': u'Australian Eastern Standard Time',
           u'tz_offset': 36000,
           u'updated': 1532934256}}