#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Basic example for a bot that awaits an answer from the user. It's built upon
# the state_machine_bot.py example
# This program is dedicated to the public domain under the CC0 license.

import os
import datetime
import logging
from pytz import timezone

from telegram import ForceReply, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, \
    CallbackQueryHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


# Define the different states a chat can be in
MENU, AWAIT_CONFIRMATION, AWAIT_INPUT = range(3)

local_tz = timezone(os.environ['TIMEZONE'])

NOW, SOON, LATER, NEVER = "<5", "<30", "not now", "not today"

# States are saved in a dict that maps chat_id -> state
last = dict()
state = dict()
# Sometimes you need to save data temporarily
context = dict()
# This dict is used to store the settings value for the chat.
# Usually, you'd use persistence for this (e.g. sqlite).
values = dict()

LATECOMER_NOTIFICATION_SECONDS = int(os.getenv("LATECOMER_NOTIFICATION_SECONDS", "60"))

reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(NOW, callback_data=NOW),
                                        InlineKeyboardButton(SOON, callback_data=SOON)  ],
                                        [InlineKeyboardButton(LATER, callback_data=LATER),
                                        InlineKeyboardButton(NEVER, callback_data=NEVER)
                                            ]])

def render_ready(users):
    msg = "*READY CHECK*\n"
    for key in users:
        user = users[key]
        fname = user['user'].first_name
        #lname = user['user'].last_name
        state = user['state']
        msg += fname + ': ' + state + "\n"
    return msg

def ready_check(bot, update):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    if chat_id in state:
        for key in state[chat_id]['users']:
            state[chat_id]['users'][key]['state'] = '???'
    else:
        state[chat_id] = dict()
        state[chat_id]['users'] = dict()

    state[chat_id]['time'] = datetime.datetime.now()


    msg = bot.sendMessage(chat_id, text=render_ready(state[chat_id]['users']), reply_markup=reply_markup, parse_mode='markdown')

    state[chat_id]['message'] = msg.message_id

def in_response(bot, update):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    if chat_id in state:
        text = update.message.text.split(' ',1)[1]
        try:
            text = text + render_in(int(text))
        except:
            text = text + render_in2(0)
        state[chat_id]['users'][user_id] = dict()
        state[chat_id]['users'][user_id]['user'] = update.message.from_user
        state[chat_id]['users'][user_id]['state'] = text
    else:
        state[chat_id] = dict()
        state[chat_id]['users'] = dict()
        bot.sendMessage(chat_id, text='Start a check with /ready first')

    print("###")
    bot.editMessageText(text=render_ready(state[chat_id]['users']),
                        chat_id=chat_id,
                        message_id=state[chat_id]['message'],
                        parse_mode='markdown',
                        reply_markup=reply_markup)


def confirm_value(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    text = query.data
    user_state = state.get(user_id, MENU)
    user_context = context.get(user_id, None)

    checkTime = state[chat_id]['time']
    time = datetime.datetime.now()
    checkDistance = (time-checkTime).seconds

    if query.data == NOW and checkDistance > LATECOMER_NOTIFICATION_SECONDS:
        fname = query.from_user.first_name
        bot.sendMessage(chat_id, text= fname + ' will be here soon!')

    #bot.answerCallbackQuery(query.id, text="Ok!")
    if text[:1] == '<':
        text = text + render_in(int(text[1:]))

    state[chat_id]['users'][user_id] = dict()
    state[chat_id]['users'][user_id]['user'] = query.from_user
    state[chat_id]['users'][user_id]['state'] = text

    bot.editMessageText(text=render_ready(state[chat_id]['users']),
                        chat_id=chat_id,
                        message_id=query.message.message_id,
                        parse_mode='markdown',
                        reply_markup=reply_markup)

def render_in(mins):
    time = datetime.datetime.now()
    time = time + datetime.timedelta(minutes=mins)
    loc_time = local_tz.localize(time)
    return ' *( -> ' + loc_time.strftime('%H:%M') + ' )*'

def render_in2(mins):
    time = datetime.datetime.now()
    time = time + datetime.timedelta(minutes=mins)
    loc_time = local_tz.localize(time)
    return ' _( @ ' + loc_time.strftime('%H:%M') + ' )_'


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text="Use /ready to initiate a ready check")


def error(bot, update, error):
    logging.warning('Update "%s" caused error "%s"' % (update, error))

# Create the Updater and pass it your bot's token.
updater = Updater(os.environ['TELEGRAM_TOKEN'])

# The command
updater.dispatcher.add_handler(CommandHandler('ready', ready_check))
updater.dispatcher.add_handler(CommandHandler('in', in_response))
# The confirmation
updater.dispatcher.add_handler(CallbackQueryHandler(confirm_value))
updater.dispatcher.add_handler(CommandHandler('start', help))
updater.dispatcher.add_handler(CommandHandler('help', help))
updater.dispatcher.add_error_handler(error)

# Start the Bot
updater.start_polling()

# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
# SIGTERM or SIGABRT
updater.idle()
