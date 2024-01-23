import logging
import os
import random

import vk_api as vk
from dotenv import load_dotenv
from vk_api.longpoll import VkEventType, VkLongPoll

from logger_handlers import TelegramLogsHandler


UNKNOWN_INTENT = 'Default Fallback Intent'


logger = logging.getLogger(__file__)


def reply(event, vk_api, project_id):
    text = event.text
    vk_api.messages.send(
        user_id=event.user_id,
        message=text,
        random_id=random.randint(1, 1000)
    )


if __name__ == '__main__':
    load_dotenv()
    api_key = os.getenv('VK_API_KEY')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

    vk_session = vk.VkApi(token=api_key)
    vk_api = vk_session.get_api()
    loglevel = os.getenv('LOG_LEVEL', default='INFO')
    log_chat = os.getenv('LOG_TG_CHAT_ID')
    log_tg_token = os.getenv('LOG_TG_BOT_TOKEN')
    logger.setLevel(loglevel)
    if log_chat:
        if not log_tg_token:
            log_tg_token = os.getenv('TELEGRAM_BOT_TOKEN')
        logger.addHandler(TelegramLogsHandler(log_tg_token, log_chat))
    logger.info('Start logging')

    longpoll = VkLongPoll(vk_session)

    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                reply(event, vk_api, project_id)
    except Exception as error:
        logger.error(error)
