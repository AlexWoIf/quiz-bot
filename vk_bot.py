import logging
import os
import traceback
from enum import IntEnum

import redis
import vk_api as vk
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

import questions
from logger_handlers import TelegramLogsHandler


RIGHT_ANSWER_TEXT = 'Правильно! Поздравляю! Для следующего вопроса нажми ' \
                    '«Новый вопрос»'
WRONG_ANSWER_TEXT = 'Неправильно… Попробуешь ещё раз?'
GIVE_UP_MESSAGE = 'Жаль что ты не знаешь. Вот правильный ответ:\n' \
                  '{answer}\n Попробуешь еще раз?'

BUTTON_NEXT_QUESTION = 'Новый вопрос'
BUTTON_GIVE_UP = 'Сдаться'


logger = logging.getLogger(__file__)


class Status(IntEnum):
    ANSWERED = 0
    WAIT_FOR_ANSWER = 1


def return_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(BUTTON_NEXT_QUESTION,
                        color=VkKeyboardColor.PRIMARY)
    keyboard.add_button(BUTTON_GIVE_UP,
                        color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def send_new_question(player, quiz):
    question = quiz.get_next_question(player)
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        keyboard=return_keyboard(),
        random_id=get_random_id()
    )
    return Status.WAIT_FOR_ANSWER


def check_answer(text, player, quiz):
    answer = quiz.get_right_answer(player)
    if text.upper() != answer.upper().split('.')[0]:
        vk_api.messages.send(
            user_id=event.user_id,
            message=WRONG_ANSWER_TEXT,
            keyboard=return_keyboard(),
            random_id=get_random_id()
        )
        return Status.WAIT_FOR_ANSWER
    vk_api.messages.send(
        user_id=event.user_id,
        message=RIGHT_ANSWER_TEXT,
        keyboard=return_keyboard(),
        random_id=get_random_id()
    )
    return Status.ANSWERED


def give_up(player, quiz):
    answer = quiz.get_right_answer(player)
    vk_api.messages.send(
        user_id=event.user_id,
        message=GIVE_UP_MESSAGE.format(answer=answer),
        keyboard=return_keyboard(),
        random_id=get_random_id()
    )
    return send_new_question(player, quiz)


def dispatch(event, vk_api, quiz, status):
    text = event.text
    player = f'vk:{event.user_id}'
    if status == Status.WAIT_FOR_ANSWER:
        if text == 'Сдаться':
            return give_up(player, quiz)
        else:
            return check_answer(text, player, quiz)
    if text == 'Новый вопрос':
        return send_new_question(player, quiz)
    vk_api.messages.send(
        user_id=event.user_id,
        message='Для игры нажмите "Новый вопрос"',
        keyboard=return_keyboard(),
        random_id=get_random_id()
    )
    return status


if __name__ == '__main__':
    load_dotenv(override=True)
    loglevel = os.getenv('LOG_LEVEL', default='INFO')
    log_chat = os.getenv('LOG_TG_CHAT_ID')
    log_tg_token = os.getenv('LOG_TG_BOT_TOKEN')
    logger.setLevel(loglevel)
    if log_chat:
        if not log_tg_token:
            log_tg_token = os.getenv('TELEGRAM_BOT_TOKEN')
        logger.addHandler(TelegramLogsHandler(log_tg_token, log_chat))
    logger.info('Start logging')

    redis_host = os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDIS_PASSWORD')

    storage = redis.Redis(host=redis_host, port=redis_port,
                          password=redis_password)

    quiz_filepath = os.getenv('QUIZ_FILEPATH')
    with open(quiz_filepath, "r", encoding="UTF8") as quiz_file:
        file_contents = quiz_file.read()
    quiz = questions.Quiz(file_contents, storage)

    api_key = os.getenv('VK_API_KEY')
    quiz_filepath = os.getenv('QUIZ_FILEPATH')

    vk_session = vk.VkApi(token=api_key)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    status = Status.ANSWERED

    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    player = f'vk:{event.user_id}'
                    user_status = storage.hget(player, 'status')
                    user_status = (0 if user_status is None
                                   else int(user_status))
                    status = Status(user_status)
                    status = dispatch(event, vk_api, quiz, status)
                    storage.hset(player, 'status', int(status))
        except Exception as error:
            logger.error({'Error': error, 'Traceback': traceback.format_exc()})
