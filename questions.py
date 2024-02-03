import logging
import os
import re

import redis
from dotenv import load_dotenv


logger = logging.getLogger(__file__)


class Quiz():
    questions_total = 0

    def __init__(self, quiz_text, storage):
        self.storage = storage
        qa_pairs = re.findall(r'\n\n+Вопрос \d+:\n([\s\S]*?)'
                              r'\n\n+Ответ:\n([\s\S]*?)\n\n+', quiz_text)
        self.dict = {question_number: qa_pair for question_number, qa_pair
                     in enumerate(qa_pairs)}
        self.questions_total = len(self.dict)

    def get_next_question(self, player):
        question_number = self.storage.hget(player, 'question_number')
        if question_number is None:
            question_number = 0
        else:
            question_number = (int(question_number) + 1) % self.questions_total
        self.storage.hset(player, 'question_number', question_number)
        (question, _) = self.dict[question_number]
        return question

    def get_right_answer(self, player):
        question_number = self.storage.hget(player, 'question_number')
        if question_number is None:
            raise IndexError("list index out of range")
        (_, answer) = self.dict[int(question_number)]
        return answer


def parse_quiz_text(quiz_text):
    qa_pairs = re.findall(r'\n\n+Вопрос \d+:\n([\s\S]*?)'
                          r'\n\n+Ответ:\n([\s\S]*?)\n\n+', quiz_text)
    return {question_number: qa_pair for question_number, qa_pair
            in enumerate(qa_pairs)}
