"""
This file handles all the infra-structure of running a Slack bot: 
    - gather config from environment variables
    - running the HTTP server
    - listening for events
    - setup connections

All actual bot logic is in the Processor class
"""
import json
import os
import logging
import random
import redis

from flask import Flask, request, make_response
from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient

from processor import Processor
from slack_client_wrapper import SlackClientWrapper
import clippy_messages

APP_NAME = "ChannelTellTale"
VERSION = "1.1.1-2020-Sept-15"  # Update this manually on each release

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
FOMO_USERS = os.getenv("FOMO_USERS")  # "bug-im:fred.hole,joe.bloggs|approvals-:boss.man"

# Initialize logging
FORMAT = "%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(thread)d | %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG if DEBUG else logging.INFO)
_logger = logging.getLogger(APP_NAME)

# Log some settings
_logger.info("STARTING %s (%s)", APP_NAME, VERSION)
_logger.info("DEBUG: %s", DEBUG)
_logger.info("PORT: %s", PORT)
_logger.info("CHANNEL_PREFIXES: %s", CHANNEL_PREFIXES)
_logger.info("TARGET_CHANNEL_ID: %s", TARGET_CHANNEL_ID)
_logger.info("REDIS_URL: %s", REDIS_URL)
_logger.info("JIRA_URL: %s", JIRA_URL)

# Initialize our web server and slack interfaces
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(SLACK_VERIFICATION_TOKEN, "/slack/events", server=app)
_redis = redis.from_url(REDIS_URL) if REDIS_URL else None
_wrapper = SlackClientWrapper(SlackClient(SLACK_BOT_TOKEN), _logger)
_processor = Processor(TARGET_CHANNEL_ID, CHANNEL_PREFIXES, _wrapper, _redis, jira=JIRA_URL, fomo_users_as_string=FOMO_USERS)


# -------------------------
# Slack event handling


@slack_events_adapter.on("channel_created")
def handle_channel_created(event_data):
    """
    Event callback when a new channel is created
    """
    _logger.info("received channel_created event: %s", json.dumps(event_data))
    _processor.process_channel_event("create", event_data)


@slack_events_adapter.on("channel_rename")
def handle_channel_renamed(event_data):
    """
    Event callback when a channel is renamed
    """
    _logger.info("received channel_rename event: %s", json.dumps(event_data))
    _processor.process_channel_event("rename", event_data)


@app.route("/interactive", methods=["GET", "POST"])
def interactive_handler():
    """
    This is called when a user clicks on a button in an interactive message.
    """
    # If a GET request is made, return 404.
    if request.method == 'GET':
        return make_response("You still haven't found what you're looking for.", 404)

    event_data = json.loads(request.form["payload"])

    # Make sure the message came from Slack
    if event_data.get("token") != SLACK_VERIFICATION_TOKEN:
        return make_response("Bad token.", 404)

    _logger.info("received interactive event: %s", repr(event_data))
    response = _processor.process_interactive_event(event_data)
    _logger.info("process_interactive_event response: %s", repr(response))

    if response is None:
        return make_response("Bad response.", 500)
    if isinstance(response, str):
        return response
    return make_response(json.dumps(response), 200, [["Content-type", "application/json; charset=utf-8"]])


@app.route("/clippyslashcmd", methods=["GET", "POST"])
def slash_clippy_handler():
    """
    This is called when the user enters a slash command.
    """
    # If a GET request is made, return 404.
    if request.method == 'GET':
        return make_response("You still haven't found what you're looking for.", 404)

    event_data = json.loads(request.form["payload"])
    _logger.info("received slash_clippy_handler: %s", json.dumps(event_data))

    text = event_data.get("text") or ""
    blocks = clippy_messages.NEW_GROUP if text.startswith("1") else \
        clippy_messages.NEW_THREAD if text.startswith("2") else \
            random.choice([clippy_messages.NEW_GROUP, clippy_messages.NEW_THREAD])
    response = {
        "response_type": "in_channel",
        "blocks": blocks
    }
    return make_response(json.dumps(response), 200, [["Content-type", "application/json; charset=utf-8"]])


# -------------------------
# Normal selector handling

@app.route("/")
def slash_handler():
    return APP_NAME


@app.route("/ping")
def ping_handler():
    channel = {
        "id": "CCLUV8FFH",
        "creator": "acs",
        "name": "jpp-home-automation",
        "purpose": {
            "value": "Discuss home automation using Google Home and Amazon Alexa"
        }
    }
    _processor._april_fools_day(channel)
    return "pong"


# ------------------------
# Playing 

hack_channel = "#jpp-notify-ttd-aws"


@app.route("/poke")
def poke_handler():
    fancy_message = {
        "title": "Is this a good image for this channel?",
        "attachment_type": "default",
        "callback_id": "choose_photo",
        "actions": [
            {
                "name": "photo",
                "text": "Yes, that's great",
                "type": "button",
                "style": "primary",
                "value": "yes"
            },
            {
                "name": "photo",
                "text": "No, show something else",
                "type": "button",
                "value": "no"
            },
            {
                "name": "photo",
                "text": "Stop suggesting",
                "style": "danger",
                "type": "button",
                "value": "stop",
            }
        ]
    }
    _logger.info("sending message: %s", repr(fancy_message))
    result = _wrapper.client.api_call("chat.postMessage", channel=hack_channel, unfurl_media=True,
                                      text="I found this image based on these keywords: 'lesson', 'yeti', 'bidding'.\n\n"
                                           "http://www.cutenessoverflow.com/wp-content/uploads/2016/06/a.jpg",
                                      attachments=[fancy_message])
    _logger.info("result: %s", repr(result))
    return "sending poke message"


@app.route("/poke2")
def poke2_handler():
    fancy_message = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "A group has been created that you might want to join:"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Group*: #bug-im-373-ctv-cross-device\nAll advertiser campaigns use the CTV graph for attribution when one campaign selects it"
            }
        }
    ]
    _logger.info("sending message: %s", repr(fancy_message))
    result = _wrapper.client.api_call(
        "chat.postMessage",
        channel="UAKA6GKFF",
        as_user=True,
        blocks=fancy_message
    )
    _logger.info("result: %s", repr(result))
    return "sending poke message"


# end playing
# ------------


def main():
    _logger.info("Starting %s server at %s", APP_NAME, PORT)
    app.run(port=PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
