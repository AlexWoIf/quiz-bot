import logging
import re
import os

from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters

from logger_handlers import TelegramLogsHandler


HELLO_TEXT = 'Здравствуйте'
logger = logging.getLogger(__file__)


def parse_quiz_text(quiz_text):
    return re.findall(r'\n\n+Вопрос \d+:\n([\s\S]*?)\n\n+'
                         r'Ответ:\n([\s\S]*?)\n\n+', quiz_text)


def reply(update, context):
    logger.debug(f'Enter reply {update.message.text=}')
    text = update.message.text
    update.message.reply_text(text)


def start(update, context):
    logger.debug(f'Enter cmd_start: {update.message.text=}')
    text = HELLO_TEXT
    update.message.reply_text(text)


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
    logger.info('Start logging')
    quiz_filepath = os.getenv('QUIZ_FILEPATH')

    directory = './quiz-questions'
    with open(quiz_filepath, "r", encoding="UTF8") as my_file:
        file_contents = my_file.read()
    all_q_a = parse_quiz_text(file_contents)

    try:
        updater = Updater(tg_token)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler('start', start))
        dispatcher.add_handler(MessageHandler(Filters.text, reply))
        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.error(error)
