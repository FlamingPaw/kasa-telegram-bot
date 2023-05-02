#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
#
# https://github.com/FlamingPaw/kasa-telegram-bot

from kasa import SmartPlug
from kasa import Discover
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram import __version__ as TG_VER
from getmac import get_mac_address
from configparser import ConfigParser
import os
import time
import asyncio
import logging

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

onsec = 0
laston = int(time.time())
last_users = []

config = ConfigParser()

if not os.path.exists('config.ini'):
    config['KASA'] = {'ip': '192.168.xxx.xxx'}
    config['TELEGRAM'] = {'bot_token': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
    config['TELEGRAM'] = {'user_history': '3'}

    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    logging.info('Config not found, creating default...')
    input("Configure Telegram Bot ID in config.ini to continue. Press any key to end...")
    exit()
else:
    config.read('config.ini')

logging.info('Starting to discover Kasa devices...')
found_devices = asyncio.run(Discover.discover())

if(len(found_devices) == 0):
    logging.error('No KASA devices could be found on the network. Using coinfig.ini')
    kasaip = config.get('KASA', 'ip')
elif(len(found_devices) == 1):
    logging.info('Automatically found one device, using it.')
    for x in found_devices:
        kasaip = x
else:
    logging.info('Automatically found more than one device.')
    kasaip = config.get('KASA', 'ip')
    if kasaip in found_devices:
        logging.info('Device in config.ini found. Using it.')
    else:
        print()
        logging.error('Device configured in config.ini was not found on the network. Here are the discovered devices, please update config.ini with one from this list.')
        print()
        for attr, value in found_devices.items():
            print('MAC: ' + get_mac_address(ip=attr) + ' - IP: ' + attr)
        print()
        input("Configure Kasa ip in config.ini to continue. Press any key to end...")
        exit()

logging.info('Using device with IP: ' + kasaip)
p = SmartPlug(kasaip)
# Sends a message with three inline buttons attached.
keyboard = [
    [
        InlineKeyboardButton("ON", callback_data="on"),
        InlineKeyboardButton("OFF", callback_data="off"),
        InlineKeyboardButton("ON FOR 2 SEC", callback_data="2s-on"),
    ],
]

reply_markup = InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Turn the Plug:", reply_markup=reply_markup)
    await p.turn_off() # Turn the plug off

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global onsec
    global laston
    global last_users

    # Parses the CallbackQuery and updates the message text.
    query = update.callback_query
    
    if(query.message.chat.type == constants.ChatType.PRIVATE):
        action_username = query.message.chat.username
    elif(query.message.chat.type == constants.ChatType.GROUP or query.message.chat.type == constants.ChatType.SUPERGROUP):
        action_username = query.from_user.username
    else:
        logger.error("The ChatType of " + query.message.chat.type + " is not supported yet.")

    last_users_text = ''
    user_history = int(config.get('TELEGRAM', 'user_history'))

    if (user_history > 0):
        last_users.append([action_username, query.data])

        for user,action in last_users[-user_history:]:
            last_users_text += "\n" + user + " turned the plug " + action + "."
        last_users_text += "\n"


    await p.update()  # Request the update
    await query.answer()

    now = int(time.time())

    if(query.data == "on"): # If the on button was pressed
        if p.is_off:
            await p.turn_on() # Turn the plug on
            laston = int(time.time())
    elif(query.data == "off"): # If the off button was pressed
        if p.is_on:
            await p.turn_off() # Turn the plug off
            onsec = onsec + (now - laston)
            laston = 0
    elif(query.data == "2s-on"): # If the off button was pressed
        if p.is_off:
            await p.turn_on() # Turn the plug on
            # onsec = onsec + (now - laston)
            laston = int(time.time())
            try:
                await query.edit_message_text(text=f"Currently {query.data} by @" + action_username + ".\n" + last_users_text + "\nOn for " + str(onsec) + " total seconds this session.\nTurn the Plug:", reply_markup=reply_markup) # Update the message text
            except Exception:
                pass
            time.sleep(2)
            await p.turn_off() # Turn the plug off
            now = int(time.time())
            onsec = onsec + (now - laston)
            laston = 0
            query.data = 'off'

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    try:
        await query.edit_message_text(text=f"Currently {query.data} by @" + action_username + ".\n" + last_users_text + "\nOn for " + str(onsec) + " total seconds this session.\nTurn the Plug:", reply_markup=reply_markup) # Update the message text
    except Exception:
        pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Displays info on how to use the bot.
    await update.message.reply_text("Use /start to use this bot.\n\nCreated by @FlamingPaw\nRun your own at https://github.com/FlamingPaw/kasa-telegram-bot")

def main() -> None:
    # Run the bot.
    # Create the Application and pass it your bot's token.
    bot_token = config.get('TELEGRAM', 'bot_token')
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot until the user presses Ctrl-C
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application.run_polling()

if __name__ == "__main__":
    main()