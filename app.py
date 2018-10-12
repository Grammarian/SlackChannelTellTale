"""
This file handles all the infra-structure of running a Slack bot: 
    - gather config from environment variables
    - running the HTTP server
    - listening for events
    - setup connections

All actual bot logic is in the Processor class
"""

import os
import logging
import redis

from flask import Flask
from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient

from bing_image_client import BingImageClient
from processor import Processor
from slack_client_wrapper import SlackClientWrapper

APP_NAME = "ChannelTellTale"

# Get environment settings 
# getenv() is used for optional settings; os.environ[] is used for required settings
DEBUG = bool(os.getenv("DEBUG"))
PORT = os.getenv("PORT") or 3000
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]
TARGET_CHANNEL_ID = os.environ["TARGET_CHANNEL_ID"]
CHANNEL_PREFIXES = os.getenv("CHANNEL_PREFIXES", "").split()  # whitespace separated list
REDIS_URL = os.getenv("REDIS_URL")
JIRA_URL = os.getenv("JIRA_URL")  # e.g. https://atlassian.mycompany.com
BING_API_KEY = os.getenv("BING_API_KEY")

# Initialize logging
FORMAT = "%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(thread)d | %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG if DEBUG else logging.INFO)
_logger = logging.getLogger(APP_NAME)
 
# Log some settings
_logger.info("STARTING %s", APP_NAME)
_logger.info("DEBUG: %s", DEBUG)
_logger.info("PORT: %s", PORT)
_logger.info("CHANNEL_PREFIXES: %s", CHANNEL_PREFIXES)
_logger.info("TARGET_CHANNEL_ID: %s", TARGET_CHANNEL_ID)
_logger.info("REDIS_URL: %s", REDIS_URL)
_logger.info("JIRA_URL: %s", JIRA_URL)
_logger.info("BING_API_KEY: %s", BING_API_KEY)

# Initialize our web server and slack interfaces
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(SLACK_VERIFICATION_TOKEN, "/slack/events", server=app)
_redis = redis.from_url(REDIS_URL) if REDIS_URL else None
_wrapper = SlackClientWrapper(SlackClient(SLACK_BOT_TOKEN), _logger)
_image_search = BingImageClient(BING_API_KEY) if BING_API_KEY else None
_processor = Processor(TARGET_CHANNEL_ID, CHANNEL_PREFIXES, _wrapper, _redis, jira=JIRA_URL, image_searcher=_image_search)

# -------------------------
# Slack event handling


@slack_events_adapter.on("channel_created")
def handle_channel_created(event_data):
    """
    Event callback when a new channel is created
    """
    _logger.info("received channel_rename event: %s", repr(event_data))
    _processor.process_channel_event("create", event_data)


@slack_events_adapter.on("channel_rename")
def handle_channel_renamed(event_data):
    """
    Event callback when a channel is renamed
    """
    _logger.info("received channel_rename event: %s", repr(event_data))
    _processor.process_channel_event("rename", event_data)


# -------------------------
# Normal selector handling

@app.route("/")
def slash_handler():
    return APP_NAME


@app.route("/ping")
def ping_handler():
    channel = {
        "id": "CCLUV8FFH",
        "name": "#fun-star-citizen",
        "purpose": {
            "value": "Discuss all things concerning Star Citizen space simulation game"
        }
    }
    _processor._post_notification_intro_message(channel)
    return "pong"


def main():
    _logger.info("Starting %s server at %s", APP_NAME, PORT)
    app.run(port=PORT, debug=DEBUG)


if __name__ == "__main__":
    main()

# ------------------------
# Playing 

# hack_channel = "#jpp-notify-ttd-aws"

# @app.route("/poke")
# def poke_handler():
#     fancy_message = {
#         "fallback": "fallback message",
#         "pretext": "A new channel has been created :tada:",
#         "author_name": "joe",
#         "title": "fixed title",
#         "text": "fixed test message",
#         "attachment_type": "default",
#         "callback_id": "poking_around",
#         "actions": [
#             {
#                 "name": "game",
#                 "text": "Chess",
#                 "type": "button",
#                 "value": "chess"
#             },
#             {
#                 "name": "game",
#                 "text": "Falken's Maze",
#                 "type": "button",
#                 "value": "maze"
#             },
#             {
#                 "name": "game",
#                 "text": "Thermonuclear War",
#                 "style": "danger",
#                 "type": "button",
#                 "value": "war",
#                 "confirm": {
#                     "title": "Are you sure?",
#                     "text": "Wouldn't you prefer a good game of chess?",
#                     "ok_text": "Yes",
#                     "dismiss_text": "No"
#                 }
#             }
#         ]
#     }
#     _logger.info("sending message: %s", repr(fancy_message))
#     slack_client.api_call("chat.postMessage", channel=hack_channel, attachments=[fancy_message])
#     return "sending poke message"

# @app.route("/interactive", methods=["GET", "POST"])
# def interactive_handler():
#         # If a GET request is made, return 404.
#     if request.method == 'GET':
#         return make_response("These are not the slackbots you're looking for.", 404)

#     # Parse the request payload into JSON
#     event_data = json.loads(request.form["payload"])
#     _logger.info("interactive_handler: %s", repr(event_data))

#     actions = event_data.get("actions")
#     if actions and len(actions):
#         action = actions[0]
#         response_message = {
#             "fallback": "Button was clicked",
#             "pretext": "You clicked the '%s' button" % action.get("value", "???"),
#         }
#         slack_client.api_call("chat.postMessage", channel=hack_channel, attachments=[response_message])
#     else:
#         _logger.info("payload was missing 'actions'")

#     return "finished interactive message"

# end playing
# ------------

