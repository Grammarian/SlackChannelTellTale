NEW_GROUP = [
    {
        "type": "image",
        "image_url": "https://tenor.com/view/clip-windows-microsoft-agent-gif-11209432",
        "alt_text": "Example Image"
    },
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "Hello!",
            "emoji": True
        }
    },
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "It looks like you're trying to do something productive. Would you like me to interrupt you?",
            "emoji": True
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "1. Do you want to play Global Thermonuclear War?"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Launch now :rocket:",
                "emoji": True
            },
            "value": "click_gtw"
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "2. How about a nice game of chess?"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "The Orangutan 1. b4 :monkey:",
                "emoji": True
            },
            "value": "click_chess"
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "3. What about playing Civ 2?"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Just one more turn :clock2:",
                "emoji": True
            },
            "value": "click_civ"
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "4. Die in fire, Ghost Of MS Past!"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Light a match :fire:",
                "emoji": True
            },
            "value": "click_die"
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "I've had enough of Clippy"
                },
                "value": "click_enough"
            }
        ]
    }
]

NEW_THREAD = [
    {
        "type": "image",
        "image_url": "https://i.gifer.com/fzNE.gif",
        "alt_text": "Example Image"
    },
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "Hello!"
        }
    },
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "It looks like you've just created a discussion group."
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "1. Would you like me to create it for you?"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Umm..."
            },
            "value": "click_um"
        }
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "2. Would you like me to make you a member of the group?"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Ah... OK?"
            },
            "value": "click_ah_ok"
        }
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "3. Would you like me to distract you from productive work?"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Not really"
            },
            "value": "click_not_really"
        }
    },
    {
        "type": "divider"
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "I've had enough of Clippy"
                },
                "value": "click_enough"
            }
        ]
    }
]

RESPONSES = {
    "click_gtw": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Which side do you want to be? *<https://www.myabandonware.com/game/global-thermonuclear-war-3u4/play-42k|Global Thermonuclear War>*"
            }
        }
    ],
    "click_chess": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Unfashionable, and therefore playable: *<https://www.chesscentral.com/pages/free-chess-games/the-sokolsky-opening.html|The Orangutan Opening>*"
            }
        }
    ],
    "click_civ": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "It's online! *<https://classicreload.com/win3x-sid-meiers-civilization-ii.html|Civ 2 in the browser>*"
            }
        }
    ],
    "click_die": [
        {
            "type": "image",
            "title": {
                "type": "plain_text",
                "text": "Bill Gates fires Clippy"
            },
            "image_url": "https://media.giphy.com/media/5nsiFjdgylfK3csZ5T/giphy.gif",
            "alt_text": "Example Image"
        }
    ],
    "click_um": [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "Great! I'm glad I was able to help :thumbsup: "
            }
        }
    ],
    "click_ah_ok": [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "Awesome! I could you help you write a letter now! :envelope: :smiley:"
            }
        }
    ],
    "click_not_really": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "OK! I'm out of here :white_frowning_face:"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*<https://www.mentalfloss.com/article/504767/tragic-life-clippy-worlds-most-hated-virtual-assistant|The Tragic Life of Clippy -- The World's Most Hated Virtual Assistant>*"
            }
        }
    ],
    "click_enough": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Thank you for taking part in this year April Fool's sociological experiment. "
            }
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "Do one thing today to bring a smile to someone who's feeling low :smile:"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "*If you need inspiration:* <http://hoaxes.org/aprilfool|Best April Fool Pranks of All Time>"
                }
            ]
        }
    ]
}
