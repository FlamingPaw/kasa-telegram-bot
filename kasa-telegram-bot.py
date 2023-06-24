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
from threading import Thread, Event
from time import sleep
from sys import exit

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
onsec = 0
laston = int(time.time())
last_users = []
p = None
reply_markup = None
config = None
appRun = Event()
sysRun = Event()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await startMessage(update, context)
    await startPlug()


async def startMessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Turn the Plug:", reply_markup=reply_markup)
    window["tg_log"].print("Answering '/start' command.")
    window["tg_live"].update("Turn the Plug:")


async def startPlug() -> None:
    await p.turn_off()  # Turn the plug off


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global onsec
    global laston
    global last_users
    global cam

    # Parses the CallbackQuery and updates the message text.
    query = update.callback_query

    if query.message.chat.type == constants.ChatType.PRIVATE:
        action_username = query.message.chat.username
    elif (
        query.message.chat.type == constants.ChatType.GROUP
        or query.message.chat.type == constants.ChatType.SUPERGROUP
    ):
        action_username = query.from_user.username
    else:
        window["tg_log"].print(
            "The ChatType of " + query.message.chat.type + " is not supported yet."
        )

    last_users_text = ""
    user_history = int(config.get("TELEGRAM", "user_history"))

    if user_history > 0:
        last_users.append([action_username, query.data])

        for user, action in last_users[-user_history:]:
            if action == "webcam-photo":
                last_users_text += "\n" + user + " captured a webcam photo."
            else:
                last_users_text += (
                    "\n"
                    + user
                    + " turned the plug on for "
                    + config.get("TELEGRAM", action)
                    + " "
                    + config.get("BOT", "time_label")
                    + "."
                )
        last_users_text += "\n"

    await p.update()  # Request the update
    await query.answer()

    if (
        query.data == "button_1" or query.data == "button_2" or query.data == "button_3"
    ):  # If the off button was pressed
        await plugTimer(
            update,
            context,
            int(config.get("TELEGRAM", query.data)),
            action_username,
            last_users_text,
        )
    elif query.data == "webcam-photo":  # If the webcam capture button was pressed
        query.data = "Capturing webcam image"
        await query.edit_message_text(
            text=f"Currently {query.data} by @"
            + action_username
            + ".\n"
            + last_users_text
            + "\nOn for "
            + str(onsec)
            + " total "
            + config.get("BOT", "time_label")
            + " this session.\nTurn the Plug:",
            reply_markup=reply_markup,
        )
        window["tg_live"].update(
            "Currently "
            + query.data
            + " by @"
            + action_username
            + ".\n"
            + last_users_text
            + "\nOn for "
            + str(onsec)
            + " total "
            + config.get("BOT", "time_label")
            + " this session."
        )
        window["bot_log"].print(query.data)
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
            if p.is_on:
                query.data = "on"
            else:
                query.data = "off"
            window["tg_live"].update(
                "Currently "
                + query.data
                + " by @"
                + action_username
                + ".\n"
                + last_users_text
                + "\nOn for "
                + str(onsec)
                + " total "
                + config.get("BOT", "time_label")
                + " this session."
            )
            window["tg_log"].print(action_username + " requested webcam image.")
            await context.application.bot.send_message(
                query.message.chat_id,
                text=f"Currently {query.data} by @"
                + action_username
                + ".\n"
                + last_users_text
                + "\nOn for "
                + str(onsec)
                + " total "
                + config.get("BOT", "time_label")
                + " this session.\nTurn the Plug:",
                reply_markup=reply_markup,
            )

        # If captured image is corrupted, moving to else part
        else:
            window["bot_log"].print("Failed to capture image from webcam.")

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    try:
        await query.edit_message_text(
            text=f"Currently {query.data} by @"
            + action_username
            + ".\n"
            + last_users_text
            + "\nOn for "
            + str(onsec)
            + " total "
            + config.get("BOT", "time_label")
            + " this session.\nTurn the Plug:",
            reply_markup=reply_markup,
        )  # Update the message text
        window["tg_live"].update(
            "Currently "
            + query.data
            + " by @"
            + action_username
            + ".\n"
            + last_users_text
            + "\nOn for "
            + str(onsec)
            + " total "
            + config.get("BOT", "time_label")
            + " this session."
        )
    except Exception:
        pass


async def plugTimer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    timesec,
    action_username,
    last_users_text,
) -> None:
    global onsec, laston, config

    now = int(time.time())

    # Parses the CallbackQuery and updates the message text.
    query = update.callback_query

    await p.update()  # Request the update

    if p.is_off:
        window["bot_log"].print(
            "Turning plug on for "
            + str(timesec)
            + " "
            + config.get("BOT", "time_label")
            + "..."
        )
        window["tg_log"].print(
            action_username
            + " turned the plug on for "
            + str(timesec)
            + " "
            + config.get("BOT", "time_label")
            + "."
        )
        await p.turn_on()  # Turn the plug on
        # onsec = onsec + (now - laston)
        laston = int(time.time())
        try:
            await query.edit_message_text(
                text=f"Currently on for "
                + str(config.get("TELEGRAM", query.data))
                + " "
                + config.get("BOT", "time_label")
                + " by @"
                + action_username
                + ".\n"
                + last_users_text
                + "\nOn for "
                + str(onsec)
                + " total "
                + config.get("BOT", "time_label")
                + " this session.\nTurn the Plug:",
                reply_markup=reply_markup,
            )  # Update the message text
            window["tg_live"].update(
                "Currently on for "
                + str(config.get("TELEGRAM", query.data))
                + " "
                + config.get("BOT", "time_label")
                + " by @"
                + action_username
                + ".\n"
                + last_users_text
                + "\nOn for "
                + str(onsec)
                + " total "
                + config.get("BOT", "time_label")
                + " this session."
            )
        except Exception:
            pass
        time.sleep(timesec)
        await p.turn_off()  # Turn the plug off
        now = int(time.time())
        onsec = onsec + (now - laston)
        laston = 0
        query.data = "off"
        window["bot_log"].print("Turned plug off.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Displays info on how to use the bot.
    await update.message.reply_text(
        "Use /start to use this bot.\n\nCreated by @FlamingPaw\nRun your own at https://github.com/FlamingPaw/kasa-telegram-bot"
    )
    window["tg_log"].print("Answering '/help' command.")


def start_bot() -> None:
    global application, config, appRun, window
    while True:
        if appRun.is_set():
            config = ConfigParser()

            if not os.path.exists("config.ini"):
                default_cfg_data = {
                    "KASA": {"ip": "192.168.xxx.xxx"},
                    "TELEGRAM": {
                        "bot_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                        "user_history": "3",
                        "button_1": "2",
                        "button_2": "5",
                        "button_3": "10",
                    },
                    "WEBCAM": {
                        "enabled": "false",
                        "port": "0",
                        "resolution_height": "1920",
                        "resolution_width": "1080",
                    },
                    "BOT": {
                        "time_label": "Seconds",
                    },
                }
                config.read_dict(default_cfg_data)

                with open("config.ini", "w") as configfile:
                    config.write(configfile)
                window["bot_log"].print("Config not found, creating default...")
                sg.popup_auto_close(
                    "Configure Telegram Bot ID in config.ini to continue."
                )
                exit()
            else:
                config.read("config.ini")

            asyncio.run(launch())

            application = (
                Application.builder().token(config.get("TELEGRAM", "bot_token")).build()
            )

            application.add_handler(CommandHandler("start", start))
            application.add_handler(CallbackQueryHandler(button))
            application.add_handler(CommandHandler("help", help_command))

            window.find_element("status").Update("Running")
            window["bot_log"].print("READY!")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            application.run_polling()
        else:
            sleep(1)


async def launch():
    global reply_markup, p, config, onsec, laston, last_users, cam
    window["bot_log"].print("Starting to discover Kasa devices...")
    found_devices = await Discover.discover()

    if len(found_devices) == 0:
        window["bot_log"].print(
            "No KASA devices could be found on the network. Using coinfig.ini"
        )
        kasaip = config.get("KASA", "ip")
    elif len(found_devices) == 1:
        window["bot_log"].print("Automatically found one device, using it.")
        for x in found_devices:
            kasaip = x
    else:
        window["bot_log"].print("Automatically found more than one device.")
        kasaip = config.get("KASA", "ip")
        if kasaip in found_devices:
            window["bot_log"].print("Device in config.ini found. Using it.")
        else:
            window["bot_log"].print(
                "Device configured in config.ini was not found on the network. Here are the discovered devices, please update config.ini with one from this list."
            )
            for attr, value in found_devices.items():
                window["bot_log"].print(
                    "MAC: " + get_mac_address(ip=attr) + " - IP: " + attr
                )
            sg.popup_auto_close("Configure Kasa ip in config.ini to continue.")

    window["bot_log"].print("Using device with IP: " + kasaip)
    p = SmartPlug(kasaip)
    await startPlug()
    # Sends a message with three inline buttons attached.
    # TODO: Make this dynamic. The button controller can already accept any value.
    keyboard = [
        [
            InlineKeyboardButton(
                config.get("TELEGRAM", "button_1")
                + " "
                + config.get("BOT", "time_label"),
                callback_data="button_1",
            ),
            InlineKeyboardButton(
                config.get("TELEGRAM", "button_2")
                + " "
                + config.get("BOT", "time_label"),
                callback_data="button_2",
            ),
            InlineKeyboardButton(
                config.get("TELEGRAM", "button_3")
                + " "
                + config.get("BOT", "time_label"),
                callback_data="button_3",
            ),
        ],
    ]

    if config.get("WEBCAM", "enabled") == "true":
        window["bot_log"].print("Config instructed to use Webcam, adding button.")
        keyboard = [
            keyboard[0]
            + [InlineKeyboardButton("Webcam Photo", callback_data="webcam-photo")]
        ]
        # initialize the camera
        # If you have multiple cameras connected with current device, assign a value in webcam_port config according to that.
        cam_port = config.get("WEBCAM", "port")
        window["bot_log"].print("Using camera " + cam_port)
        cam = cv.VideoCapture(int(cam_port))
        cam.set(cv.CAP_PROP_FRAME_WIDTH, int(config.get("WEBCAM", "resolution_height")))
        cam.set(cv.CAP_PROP_FRAME_HEIGHT, int(config.get("WEBCAM", "resolution_width")))
        cam.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*"MJPG"))
    else:
        window["bot_log"].print("Webcam NOT being used.")

    reply_markup = InlineKeyboardMarkup(keyboard)


def gui():
    global appRun, window, sysRun
    theme_dict = {
        "BACKGROUND": "#2B475D",
        "TEXT": "#FFFFFF",
        "INPUT": "#F2EFE8",
        "TEXT_INPUT": "#000000",
        "SCROLL": "#F2EFE8",
        "BUTTON": ("#000000", "#C2D4D8"),
        "PROGRESS": ("#FFFFFF", "#C7D5E0"),
        "BORDER": 0,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    }

    sg.theme_add_new("Dashboard", theme_dict)
    sg.theme("Dashboard")

    BORDER_COLOR = "#C7D5E0"
    DARK_HEADER_COLOR = "#1B2838"
    BPAD_LEFT = ((20, 10), (0, 0))
    BPAD_LEFT_INSIDE = (0, (10, 0))
    BPAD_RIGHT = ((10, 20), (10, 0))

    top_banner = [
        [
            sg.Text(
                "Pre-release v0.2",
                font="Any 20",
                background_color=DARK_HEADER_COLOR,
                expand_x=True,
                expand_y=True,
            )
        ]
    ]

    block_1 = [
        [sg.Text("Bot Controls", font="Any 20")],
        [sg.Text("Bot Status: "), sg.Text("Stopped", key="status")],
        [sg.Button("Start"), sg.Button("Stop", disabled=True), sg.Exit()],
    ]

    block_2 = [
        [sg.Text("Bot Output", font="Any 20")],
        [
            sg.Multiline(
                size=(80, 20),
                disabled=True,
                write_only=True,
                key="bot_log",
                expand_x=True,
                expand_y=True,
            )
        ],
    ]
    block_3 = [
        [sg.Text("Telegram Logs", font="Any 20")],
        [
            sg.Multiline(
                size=(80, 20),
                disabled=True,
                write_only=True,
                key="tg_log",
                expand_x=True,
                expand_y=True,
            )
        ],
    ]
    block_4 = [
        [sg.Text("Telegram Live", font="Any 20")],
        [
            sg.Multiline(
                size=(80, 20),
                disabled=True,
                write_only=True,
                key="tg_live",
                expand_x=True,
                expand_y=True,
            )
        ],
    ]

    layout = [
        [
            sg.Frame(
                "",
                [
                    [
                        sg.Frame(
                            "",
                            top_banner,
                            size=(960, 60),
                            pad=BPAD_LEFT_INSIDE,
                            border_width=0,
                            background_color=DARK_HEADER_COLOR,
                            expand_x=True,
                            expand_y=True,
                        )
                    ]
                ],
            )
        ],
        [
            sg.Frame(
                "",
                [
                    [
                        sg.Frame(
                            "",
                            block_2,
                            size=(450, 150),
                            pad=BPAD_LEFT_INSIDE,
                            border_width=0,
                            expand_x=True,
                            expand_y=True,
                        )
                    ],
                    [
                        sg.Frame(
                            "",
                            block_1,
                            size=(450, 150),
                            pad=BPAD_LEFT_INSIDE,
                            border_width=0,
                            expand_x=True,
                            expand_y=True,
                            element_justification="c",
                        )
                    ],
                    [
                        sg.Frame(
                            "",
                            block_3,
                            size=(450, 320),
                            pad=BPAD_LEFT_INSIDE,
                            expand_x=True,
                            expand_y=True,
                        )
                    ],
                ],
                pad=BPAD_LEFT,
                background_color=BORDER_COLOR,
                border_width=0,
                expand_x=True,
                expand_y=True,
            ),
            sg.Frame(
                "",
                block_4,
                size=(450, 320),
                pad=BPAD_RIGHT,
                expand_x=True,
                expand_y=True,
            ),
        ],
        [sg.Sizegrip(background_color=BORDER_COLOR)],
    ]

    window = sg.Window(
        "Kasa Telegram Bot",
        layout,
        margins=(0, 0),
        background_color=BORDER_COLOR,
        no_titlebar=False,
        resizable=True,
    )
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()
        if event == "Start":
            appRun.set()

            window.find_element("Start").Update(disabled=True)
            window.find_element("Stop").Update(disabled=False)
            window.find_element("status").Update("Starting...")
        if event == "Stop":
            window.find_element("Start").Update(disabled=False)
            window.find_element("Stop").Update(disabled=True)
            window.find_element("status").Update("Stopped")
            sysRun.set()
        if event in (None, "Exit"):
            sysRun.set()
            break
    if application is not None and application.running:
        sysRun.set()
    window.close()


if __name__ == "__main__":
    t1 = Thread(target=gui)
    t1.daemon = True
    t1.start()

    t2 = Thread(target=start_bot)
    t2.daemon = True
    t2.start()

    while True:
        if not sysRun.is_set():
            sleep(1)
        else:
            exit()
