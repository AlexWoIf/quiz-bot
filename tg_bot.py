import logging
import os
import traceback
from enum import Enum

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

import questions
from logger_handlers import TelegramLogsHandler


HELLO_TEXT = 'Здравствуйте'
RIGHT_ANSWER_TEXT = 'Правильно! Поздравляю! Для следующего вопроса нажми ' \
                    '«Новый вопрос»'
WRONG_ANSWER_TEXT = 'Неправильно… Попробуешь ещё раз?'
GIVE_UP_MESSAGE = 'Жаль что ты не справились. Вот правильный ответ:\n' \
                  '{answer}\n Попробуешь еще раз?'
BUTTON_NEXT_QUESTION = 'Новый вопрос'
BUTTON_GIVE_UP = 'Сдаться'


logger = logging.getLogger(__file__)


class Status(Enum):
    ANSWERED = 0
    CHECK_ANSWER = 1


def send_new_question(update, context):
    logger.debug(f'Enter send_new_question {update.message.text=}')
    quiz = context.bot_data['quiz']
    question = quiz.get_next_question(f'tg:{update.message.from_user.id}')
    keyboard = [[BUTTON_NEXT_QUESTION, BUTTON_GIVE_UP],]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    update.message.reply_text(question, reply_markup=reply_markup)
    return Status.CHECK_ANSWER


def check_answer(update, context):
    logger.debug(f'Enter reply_question {update.message.text=}')
    quiz = context.bot_data['quiz']
    answer = quiz.get_right_answer(f'tg:{update.message.from_user.id}')
    if update.message.text.upper() != answer.upper().split('.')[0]:
        text = WRONG_ANSWER_TEXT
        update.message.reply_text(text)
        return Status.CHECK_ANSWER
    keyboard = [[BUTTON_NEXT_QUESTION, BUTTON_GIVE_UP],]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    update.message.reply_text(RIGHT_ANSWER_TEXT, reply_markup=reply_markup)
    return Status.ANSWERED


def give_up(update, context):
    logger.debug(f'Enter give_up {update.message.text=}')
    quiz = context.bot_data['quiz']
    answer = quiz.get_right_answer(f'tg:{update.message.from_user.id}')
    keyboard = [[BUTTON_NEXT_QUESTION, BUTTON_GIVE_UP],]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    update.message.reply_text(GIVE_UP_MESSAGE.format(answer=answer),
                              reply_markup=reply_markup)
    return send_new_question(update, context)


def start(update, context):
    logger.debug(f'Enter cmd_start: {update.message.text=}')
    text = HELLO_TEXT
    storage.set(update.message.from_user.id, 0)
    keyboard = [[BUTTON_NEXT_QUESTION, BUTTON_GIVE_UP],]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)
    return Status.ANSWERED


if __name__ == '__main__':
    load_dotenv()
    api_key = os.getenv('GOOGLE_CLOUD_API_KEY')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    tg_token = os.getenv('TELEGRAM_BOT_TOKEN')
    loglevel = os.getenv('LOG_LEVEL', default='INFO')
    log_chat = os.getenv('LOG_TG_CHAT_ID')
    log_tg_token = os.getenv('LOG_TG_BOT_TOKEN')
    logger.setLevel(loglevel)
    if log_chat:
        if not log_tg_token:
            log_tg_token = tg_token
        logger.addHandler(TelegramLogsHandler(log_tg_token, log_chat))
    logger.debug('Start logging')

    redis_host = os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDIS_PASSWORD')
    storage = redis.Redis(host=redis_host, port=redis_port,
                          password=redis_password)

    quiz_filepath = os.getenv('QUIZ_FILEPATH')
    with open(quiz_filepath, "r", encoding="UTF8") as quiz_file:
        file_contents = quiz_file.read()
    quiz = questions.Quiz(file_contents, storage)

    try:
        updater = Updater(tg_token)
        dispatcher = updater.dispatcher
        dispatcher.bot_data['quiz'] = quiz
        conversation = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                Status.ANSWERED: [
                    MessageHandler(Filters.text(BUTTON_NEXT_QUESTION),
                                   send_new_question),
                ],
                Status.CHECK_ANSWER: [
                    MessageHandler(Filters.text(BUTTON_GIVE_UP), give_up),
                    MessageHandler(Filters.text, check_answer),
                ],
            },
            fallbacks=[],
        )
        dispatcher.add_handler(conversation)
        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error({'Error': error, 'Traceback': traceback.format_exc()})
