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
import cv2 as cv
import PySimpleGUI as sg
from datetime import date

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
application = None

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("START")
    await startMessage(update, context)
    await startPlug()

async def startMessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Turn the Plug:", reply_markup=reply_markup)

async def startPlug() -> None:
    await p.turn_off() # Turn the plug off

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global onsec
    global laston
    global last_users
    global cam

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
            if(action == 'webcam-photo'):
                last_users_text += "\n" + user + " captured a webcam photo."
            else:
                last_users_text += "\n" + user + " turned the plug on for " + config.get("TELEGRAM", action) + " seconds."
        last_users_text += "\n"


    await p.update()  # Request the update
    await query.answer()

    if(query.data == "button_1" or query.data == "button_2" or query.data == "button_3"): # If the off button was pressed
        await plugTimer(update, context, int(config.get("TELEGRAM", query.data)), action_username, last_users_text)
    elif(query.data == "webcam-photo"): # If the webcam capture button was pressed
        query.data = 'Capturing webcam image'
        await query.edit_message_text(text=f"Currently {query.data} by @" + action_username + ".\n" + last_users_text + "\nOn for " + str(onsec) + " total seconds this session.\nTurn the Plug:", reply_markup=reply_markup)
        # reading the input using the camera
        result, image = cam.read()
        
        # If image will detected without any error, 
        # show result
        if result:
            # saving image in local storage
            webcam_tmpfile = "kasa-telegram-bot_webcam-" + str(time.time()) + ".png"
            cv.imwrite(webcam_tmpfile, image)
            query = update.callback_query
            webcam_open = open(webcam_tmpfile, "rb")
            await context.application.bot.sendPhoto(query.message.chat_id, webcam_open),
            webcam_open.close(),
            os.remove(webcam_tmpfile)
            if(p.is_on):
                query.data = 'on'
            else:
                query.data = 'off'
            query = await context.application.bot.send_message(query.message.chat_id, text=f"Currently {query.data} by @" + action_username + ".\n" + last_users_text + "\nOn for " + str(onsec) + " total seconds this session.\nTurn the Plug:", reply_markup=reply_markup)
        
        # If captured image is corrupted, moving to else part
        else:
            print("No image detected. Please! try again")

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    try:
        await query.edit_message_text(text=f"Currently {query.data} by @" + action_username + ".\n" + last_users_text + "\nOn for " + str(onsec) + " total seconds this session.\nTurn the Plug:", reply_markup=reply_markup) # Update the message text
    except Exception:
        pass

async def plugTimer(update: Update, context: ContextTypes.DEFAULT_TYPE, timesec, action_username, last_users_text) -> None:
    global onsec
    global laston

    now = int(time.time())

    # Parses the CallbackQuery and updates the message text.
    query = update.callback_query
    
    await p.update()  # Request the update

    if p.is_off:
        await p.turn_on() # Turn the plug on
        # onsec = onsec + (now - laston)
        laston = int(time.time())
        try:
            await query.edit_message_text(text=f"Currently on for " + str(config.get("TELEGRAM", query.data)) + " seconds by @" + action_username + ".\n" + last_users_text + "\nOn for " + str(onsec) + " total seconds this session.\nTurn the Plug:", reply_markup=reply_markup) # Update the message text
        except Exception:
            pass
        time.sleep(timesec)
        await p.turn_off() # Turn the plug off
        now = int(time.time())
        onsec = onsec + (now - laston)
        laston = 0
        query.data = 'off'

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Displays info on how to use the bot.
    await update.message.reply_text("Use /start to use this bot.\n\nCreated by @FlamingPaw\nRun your own at https://github.com/FlamingPaw/kasa-telegram-bot")

onsec = 0
laston = int(time.time())
last_users = []
p = None
reply_markup = None
config = None

async def start_bot() -> None:
    global application, config, onsec, laston, last_users, reply_markup, p

    config = ConfigParser()

    if not os.path.exists('config.ini'):
        config['KASA'] = {'ip': '192.168.xxx.xxx'}
        config['TELEGRAM'] = {'bot_token': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
        config['TELEGRAM'] = {'user_history': '3'}
        config['TELEGRAM'] = {'button_1': '2'}
        config['TELEGRAM'] = {'button_2': '5'}
        config['TELEGRAM'] = {'button_3': '10'}
        config['WEBCAM'] = {'enable': 'false'}
        config['WEBCAM'] = {'port': '0'}
        config['WEBCAM'] = {'resolution_height': '1920'}
        config['WEBCAM'] = {'resolution_height': '1080'}

        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        logging.info('Config not found, creating default...')
        input("Configure Telegram Bot ID in config.ini to continue. Press any key to end...")
        exit()
    else:
        config.read('config.ini')

    bot_token = config.get('TELEGRAM', 'bot_token')

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("help", help_command))

    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await launch()

async def launch():
    global reply_markup, p, config, onsec, laston, last_users
    logging.info('Starting to discover Kasa devices...')
    found_devices = await Discover.discover()

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
    await startPlug()
    # Sends a message with three inline buttons attached.
    keyboard = [
        [
            InlineKeyboardButton(config.get('TELEGRAM', 'button_1') + " Seconds", callback_data="button_1"),
            InlineKeyboardButton(config.get('TELEGRAM', 'button_2') + " Seconds", callback_data="button_2"),
            InlineKeyboardButton(config.get('TELEGRAM', 'button_3') + " Seconds", callback_data="button_3"),
        ],
    ]

    if(config.get('WEBCAM', 'enabled') == 'true') :
        logging.info('Config instructed to use Webcam, adding button.')
        keyboard = [keyboard[0] + [InlineKeyboardButton("Webcam Photo", callback_data="webcam-photo")]]
        # initialize the camera
        # If you have multiple cameras connected with current device, assign a value in webcam_port config according to that.
        cam_port = config.get('WEBCAM', 'port')
        logging.info('Using camera ' + cam_port)
        cam = cv.VideoCapture(int(cam_port))
        cam.set(cv.CAP_PROP_FRAME_WIDTH, int(config.get('WEBCAM', 'resolution_height')))
        cam.set(cv.CAP_PROP_FRAME_HEIGHT, int(config.get('WEBCAM', 'resolution_width')))
        cam.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*"MJPG"))
    else:
        logging.info('Webcam NOT being used.')

    reply_markup = InlineKeyboardMarkup(keyboard)

async def stop_bot():
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    await application.post_shutdown()

def gui():
    today = date.today()
    theme_dict = {'BACKGROUND': '#2B475D',
                'TEXT': '#FFFFFF',
                'INPUT': '#F2EFE8',
                'TEXT_INPUT': '#000000',
                'SCROLL': '#F2EFE8',
                'BUTTON': ('#000000', '#C2D4D8'),
                'PROGRESS': ('#FFFFFF', '#C7D5E0'),
                'BORDER': 0,'SLIDER_DEPTH': 0, 'PROGRESS_DEPTH': 0}

    sg.theme_add_new('Dashboard', theme_dict)
    sg.theme('Dashboard')

    BORDER_COLOR = '#C7D5E0'
    DARK_HEADER_COLOR = '#1B2838'
    BPAD_TOP = ((20,20), (20, 10))
    BPAD_LEFT = ((20,10), (0, 0))
    BPAD_LEFT_INSIDE = (0, (10, 0))
    BPAD_RIGHT = ((10,20), (10, 0))

    top_banner = [
                [sg.Text('Dashboard', font='Any 20', background_color=DARK_HEADER_COLOR, enable_events=True, grab=False), sg.Push(background_color=DARK_HEADER_COLOR),
                sg.Text(today.strftime("%B %d, %Y"), font='Any 20', background_color=DARK_HEADER_COLOR)],
                ]

    top  = [[sg.Push(), sg.Text('A heading', font='Any 20'), sg.Push()],
                [sg.T('This Frame has a relief while the others do not')]]

    block_3 = [[sg.Text('Bot Status: '), sg.Text('Stopped', key='status')],
              [sg.Button('Start'), sg.Button('Stop', disabled=True), sg.Exit()]]


    block_2 = [[sg.Text('Block 2', font='Any 20')],
                [sg.T('This is some random text')],
                [sg.Image(data=sg.DEFAULT_BASE64_ICON, enable_events=True)]  ]

    block_4 = [[sg.Text('Block 4', font='Any 20')],
                [sg.T('You can move the window by grabbing this block (and the top banner)')],
                [sg.T('This block is a Column Element')],
                [sg.T('The others are all frames')],
                [sg.T('The Frame Element, with a border_width=0\n    and no title is just like a Column')],
                [sg.T('Frames that have a fixed size \n    handle element_justification better than Columns')]]


    layout = [
            [sg.Frame('', top_banner,   pad=(0,0), background_color=DARK_HEADER_COLOR,  expand_x=True, border_width=0, grab=True)],
            [sg.Frame('', top, size=(920, 100), pad=BPAD_TOP,  expand_x=True,  relief=sg.RELIEF_GROOVE, border_width=3)],
            [sg.Frame('', [[sg.Frame('', block_2, size=(450,150), pad=BPAD_LEFT_INSIDE, border_width=0, expand_x=True, expand_y=True, )],
                            [sg.Frame('', block_3, size=(450,150),  pad=BPAD_LEFT_INSIDE, border_width=0, expand_x=True, expand_y=True, element_justification='c')]],
                        pad=BPAD_LEFT, background_color=BORDER_COLOR, border_width=0, expand_x=True, expand_y=True),
            sg.Column(block_4, size=(450, 320), pad=BPAD_RIGHT,  expand_x=True, expand_y=True, grab=True),],[sg.Sizegrip(background_color=BORDER_COLOR)]]

    window = sg.Window('Kasa Telegram Bot', layout, margins=(0,0), background_color=BORDER_COLOR, no_titlebar=False, resizable=True)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()
        if event == 'Start':
            if application is None:
                asyncio.run(start_bot())
            else:
                asyncio.run(application.updater.start_polling())
            window.find_element('Start').Update(disabled=True)
            window.find_element('Stop').Update(disabled=False)
            window.find_element('status').Update('Running')
        if event == 'Stop':
            asyncio.run(stop_bot())
            window.find_element('Start').Update(disabled=False)
            window.find_element('Stop').Update(disabled=True)
            window.find_element('status').Update('Stopped')
        if event in (None, 'Exit'):
            break
    if application is not None and application.running:
        asyncio.run(stop_bot())
    window.close()
gui()