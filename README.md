# Overview

In any organisation, there are always new discussions and groups being formed. It can be impossible to even know
what people are discussing, let alone to keep up. 

This app at least lets people know what new discussions are being created.

# Hosting

This app can be run locally, via ngrok. 

More normally, it would be hosted somewhere: heroku, zeit, aws, GCE. 

It's pure python without outside dependencies, so it's esy to host.

# Configuration

This app requires a couple of pieces of configuration, supplied via environment variables:

    export TARGET_CHANNEL_ID="#your-channel"
    export SLACK_VERIFICATION_TOKEN="PUT_YOUR_TOKEN_HERE"
    export SLACK_BOT_TOKEN="PUT_YOUR_SLACKBOT_TOKEN_HERE"

