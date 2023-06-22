# kasa-telegram-bot
A telegram bot used to interface with Kasa devices.
This is not a general purpose bot, and is made specifically to turn on or off a single Kasa plug via telegram.
NOTE: This is still very much a work in progress. If you want a working program, use the [Latest Release](https://github.com/FlamingPaw/kasa-telegram-bot/releases/latest/download/kasa-telegram-bot.exe)

# Usage
You can download the windows executable from [Latest Release](https://github.com/FlamingPaw/kasa-telegram-bot/releases/latest/download/kasa-telegram-bot.exe) or you can run the Python file yourself. See manual install for how.

# Config
Upon running the bot for the first time, a `config.ini` file will be created. Inside are two sections `KASA` and `TELEGRAM`. These will need to be configured.

## IP
If you only have one Kasa plug, the bot will most likely be able to auto-discover it. If there are more than one Kasa plug, or the bot is not able to auto-discover your plug, set it's IP address at `ip =`. If auto-discover is able to find more than one Kasa plug, it will list the plugs and their ip addresses when you try and run the bot without configuring.

## Bot Token
A bot token is a string that authenticates your bot (not your account) on the bot API. Each bot has a unique token which can also be revoked at any time via [@BotFather](https://t.me/botfather).

Obtaining a token is as simple as contacting [@BotFather](https://t.me/botfather), issuing the /newbot command and following the steps until you're given a new token. You can find a step-by-step guide [here](https://core.telegram.org/bots/features#creating-a-new-bot).

Your token will look something like this:

4839574812:AAFD39kkdpWt3ywyRZergyOLMaJhac60qc
Make sure to save your token in a secure place, treat it like a password and don't share it with anyone.
Take that token, and place it in `config.ini` at `bot_token =`

## User History
This is the number of history lines to show under the current status. 0 disables this.

# Manual Install
1. Download Python from https://www.python.org/downloads/
2. Download pip from https://pip.pypa.io/en/stable/installation/
3. Run `pip install -r requirements.txt` to install required libraries.
4. Run the python file `kasa-telegram-bot.py`

# Todo:
- Create GUI (started, see 'gui' branch)
- Make config.ini auto-populate specific missing entries. (eg, new feature added)
- Create controls and logs via gui
