import os
import sys
import time
import logging
from logging import StreamHandler

import requests
from dotenv import load_dotenv
import telegram

from exceptions import (
    UnknownError, NotAuthenticated, InternalServerError,
    NoContent
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = 158783776

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    filename='bot.log',
    filemode='w',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN is None or TELEGRAM_TOKEN is None:
        logger.critical('Отсутствие обязательных переменных окружения во '
                        'время запуска бота')
        raise ValueError('Empty string')


def send_message(bot, message):
    """Отправка сообщения в чат Telegram."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.debug('Сообщение успешно отправлено')


def get_api_answer(timestamp):
    """запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS,
                                         params=payload)
    except requests.RequestException as error:
        message = f'Сбой в работе программы: {error}'
        logger.error(message)
    if homework_statuses.status_code == 400:
        logger.error('Неожиданный статус домашней работы, обнаруженный в '
                     'ответе API')
        raise UnknownError('Wrong from_date format')
    elif homework_statuses.status_code == 401:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
        raise NotAuthenticated('Учетные данные не были предоставлены')
    elif homework_statuses.status_code == 500:
        logger.error('Internal Server Error')
        raise InternalServerError('Internal Server Error')
    elif homework_statuses.status_code == 204:
        logger.error('No Content')
        raise NoContent('No Content')
    response = homework_statuses.json()
    return response


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if type(response) is not dict:
        message = f'Некорректный тип данных. Тип данных: {type(response)}.'
        logger.error(message)
        raise TypeError
    if 'homeworks' not in response:
        logger.error('В ответе API домашки нет ключа `homeworks`')
        raise KeyError('В ответе API домашки нет ключа `homeworks`')
    if type(response['homeworks']) is not list:
        message = f'Некорректный тип данных. Тип данных: {type(response)}.'
        logger.error(message)
        raise TypeError('В ответе API домашки под ключом `homeworks` данные '
                        'приходят не в виде списка')
    return response['homeworks']


def parse_status(homework):
    """Извлечение статуса конкретной домашней работы."""
    if homework['status'] == '':
        raise ValueError('Empty string')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise KeyError('Недокументированный статус')
    if 'homework_name' not in homework:
        message = 'Нет ключа homework_name.'
        raise KeyError(message)
    for status in HOMEWORK_VERDICTS:
        if homework['status'] == status:
            homework_name = homework['homework_name']
            verdict = HOMEWORK_VERDICTS[status]
            return (f'Изменился статус проверки работы "{homework_name}". '
                    f'{verdict}')


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        response = get_api_answer(timestamp)
        homeworks = check_response(response)
        if homeworks:
            message = parse_status(homeworks[0])
            try:
                send_message(bot, message)
            except Exception:
                logger.error('Сбой при отправке сообщения в Telegram')

            logger.debug('Удачная отправка  сообщения в Telegram')
        else:
            logger.debug('Отсутствие в ответе новых статусов')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
