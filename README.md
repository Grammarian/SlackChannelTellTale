# Overview

In any organisation, there are always new discussions and groups being formed. It can be impossible to even know
what people are discussing, let alone to keep up. 

This app at least lets people know what new discussions are being created.

When a new channel is created, this app will send a notification to a configured channel:

![New channel notification](/images/sshot-notification.png?raw=true "New Channel Notification")

# Hosting

This app can be run locally, via ngrok. But, more normally, it would be hosted somewhere: heroku, zeit, aws, GCE. 

It's pure python without outside dependencies, so it's easy to host wherever you want.

# Configuration

This app requires a couple of pieces of configuration, supplied via environment variables:

    export CHANNEL_PREFIXES="prefix1 prefix2" # only channels that start with one of these will trigger a notification
    export SLACK_BOT_TOKEN="PUT_YOUR_SLACKBOT_TOKEN_HERE"
    export SLACK_VERIFICATION_TOKEN="PUT_YOUR_TOKEN_HERE"
    export TARGET_CHANNEL_ID="#your-channel"
   
`CHANNEL_PREFIXES` is a whitespace separated list of prefixes -- a new channel name must begin with one of these
prefixes in order to generate a notification.

For example, if this is set to `"eng- biz- ops-"`, then a new channel `#biz-excel` would be reported, but `#pics-puppies` would not.

If this is not set or is empty, *all* new channels will generate a notification. 

`SLACK_BOT_TOKEN` is the token that allows your app to post messages. **REQUIRED**

`SLACK_VERIFICATION_TOKEN` is the token generated by the Slack integration process to ensure that your app is working and authenticated. **REQUIRED**

`TARGET_CHANNEL_ID` is the channel name where the notifications will be posted. **REQUIRED**

# Slack integrations

This project uses Slack's python api toolkit: https://github.com/slackapi/python-slack-events-api

You will need to follow the instructions given in that project about how to create an app for slack, and configure it to receive events from your Slack instance.
