import os
import logging
import random
import time
import redis

from flask import Flask
from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient

# Constants
MESSAGE = "*%s* just created a new channel :tada:\n<#%s|%s>\nIts purpose is: %s"
COLORS = ["#ff1744", "#f50057", "#d500f9", "#651fff", "#3d5afe", "#2979ff", "#00b0ff", "#00e5ff", "#1de9b6", "#00e676", "#76ff03", "#ffea00", "#ffc400", "#ff9100", "#ff3d00" ]

# Get environment settings
DEBUG = bool(os.getenv("DEBUG"))
PORT = os.getenv("PORT") or 3000
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]
TARGET_CHANNEL_ID = os.environ["TARGET_CHANNEL_ID"]
CHANNEL_PREFIXES = os.getenv("CHANNEL_PREFIXES", "").split() # whitespace separated list
REDIS_URL = os.getenv("REDIS_URL")
 
# Initialize logging
FORMAT = '%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(thread)d | %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG if DEBUG else logging.INFO)
_logger = logging.getLogger("ChannelTellTale")
 
# Log some settings
_logger.info("STARTING")
_logger.info("DEBUG: %s", DEBUG)
_logger.info("PORT: %s", PORT)
_logger.info("CHANNEL_PREFIXES: %s", CHANNEL_PREFIXES)
_logger.info("TARGET_CHANNEL_ID: %s", TARGET_CHANNEL_ID)
_logger.info("REDIS_URL: %s", REDIS_URL)

# Initialize our web server and slack interfaces
app = Flask(__name__)

# Initialize our slack interfaces
slack_events_adapter = SlackEventAdapter(SLACK_VERIFICATION_TOKEN, "/slack/events", server=app)
slack_client = SlackClient(SLACK_BOT_TOKEN)

# Initialize redis cache
_redis = redis.from_url(REDIS_URL) if REDIS_URL is not None else None
_non_redis_cache = {}


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


def remember_channel(channel):
    """
    Remember the given channel. Return a bool indicating if we've already seen it
    """
    if _redis:
        return _remember_channel_redis(channel)
    else:
        return _remember_channel_non_redis(channel)


def _remember_channel_redis(channel):
    """
    Remember the given channel using redis. Return a bool indicating if we've already seen it
    """        
    redis_channel_key = "channel:%s" % channel["id"]
    is_new = _redis.setnx(redis_channel_key, channel.get("created"))
    if is_new:
        # We don't want our redis instance to just continue growing, so
        # delete the key after 24 hours
        _redis.expire(redis_channel_key, 24*60*60) 
    return not is_new


def _remember_channel_non_redis(channel):
    """
    Remember the given channel without redis. Return a bool indicating if we've already seen it.
    This isn't perfect but it's (probably) better than nothing :)
    """        
    channel_id = channel["id"]
    if channel_id in _non_redis_cache:
        return True
    _non_redis_cache[channel_id] = channel.get("created")
    return False


def get_channel_info(channel_id):
    """
    Fetch information about the given channel from slack
    """
    channel_info = slack_client.api_call("channels.info", channel=channel_id)    
    if channel_info and channel_info.get("ok"):
        return channel_info

    _logger.error("fetching of channel %s failed: %s", channel_id, repr(channel_info))
    return None


def insistent_get_channel_info(channel_id):
    """
    Repeatedly attempt to fetch information about the given channel from slack

    We particularly want the purpose of the channel, but Slack sometimes separates
    the creation of the channel from the setting of the purpose, so we have to do
    a little waiting dance. It could be that the channel was created without a 
    purpose, so don't try too hard
    """
    channel_info = get_channel_info(channel_id) 
    if not channel_info:
        return None
    attempts = 0
    while attempts < 3 and not nested_get(channel_info, "channel", "purpose", "value"):
        attempts += 1
        _logger.info("attempt %d: waiting for channel %s to find its purpose in life", attempts, channel_id)
        time.sleep(1) 
        channel_info = get_channel_info(channel_id) 
        if not channel_info:
            return None

    return channel_info


@slack_events_adapter.on("channel_created")
def handle_channel_created(event_data):
    """
    Event callback when a new channel is created
    """
    _logger.info("received event: %s", repr(event_data))

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
    if CHANNEL_PREFIXES and not any(channel_name.startswith(x) for x in CHANNEL_PREFIXES):
        _logger.info("ignored... channel name doesn't start with the appropriate prefix: %s", channel_name)
        return

    # Have we received an creation event about this channel before?
    if remember_channel(channel):
        _logger.info("ignored... we've already processed this channel: %s", channel_name)
        return

    # Fetch the full info about the creator of the channel
    creator_info = slack_client.api_call("users.info", user=channel["creator"])
    if not creator_info or not creator_info.get("ok"):
        _logger.error("ignored... fetching of creator failed: %s", repr(creator_info))
        return

    # Try hard to fetch the full info about the channel
    channel_info = insistent_get_channel_info(channel["id"]) 
    if not channel_info:
        return

    # Log for debugging if needed
    _logger.info("channel_info: %s", repr(channel_info))
    _logger.info("creator_info: %s", repr(creator_info))

    # Make a nicely format notification
    creater_id = nested_get(creator_info, "user", "id")
    creater_name = nested_get(creator_info, "user", "profile", "real_name_normalized")
    creater_image = nested_get(creator_info, "user", "profile", "image_24")
    channel_id = nested_get(channel_info, "channel", "id"), 
    channel_purpose = nested_get(channel_info, "channel", "purpose", "value")
    message = MESSAGE % (
        creater_name, 
        channel_id, 
        channel_name, 
        channel_purpose
    )
    fancy_message = {
        "fallback": message,
        "color": random.choice(COLORS),
        "pretext": "A new channel has been created :tada:",
        "author_name": "%s <@%s>" % (creater_name, creater_id),
        "author_icon": creater_image,
        "title": "<#%s>" % channel_id,
        "text": channel_purpose
    }
    _logger.info("sending to %s: %s", TARGET_CHANNEL_ID, repr(fancy_message))

    # Finally, announce the new channel in the announcement channel
    slack_client.api_call("chat.postMessage", channel=TARGET_CHANNEL_ID, attachments=[fancy_message])


# Test route: http://localhost:3000/ping
@app.route("/ping")
def ping_handler():
    return "pong"

@app.route("/")
def slash_handler():
    return "channelTellTale"

def main():
    _logger.info("Starting server at %s", PORT)
    app.run(port=PORT, debug=DEBUG)

if __name__ == "__main__":
    main()
