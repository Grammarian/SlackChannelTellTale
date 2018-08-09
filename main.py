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
