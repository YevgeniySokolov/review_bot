import os
import sys
import time
import logging
from logging import StreamHandler, Handler

import requests
from dotenv import load_dotenv
import telegram

from exceptions import UnknownError, NotAuthenticated, EndpointAccess

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

bot = telegram.Bot(token=TELEGRAM_TOKEN)


class TelegramBotHandler(Handler):
    """Обработка логов для чата Telegram."""

    def __init__(self, chat_id):
        """Создание экземпляра обработчика."""
        super().__init__()
        self.chat_id = chat_id
        self.record_flag = ''

    def emit(self, record):
        """Отправка логов в чат Telegram."""
        if self.record_flag == '':
            if record.levelname == "ERROR":
                bot.send_message(
                    self.chat_id,
                    self.format(record)
                )
                self.record_flag = record.message
        else:
            if (record.message != self.record_flag
               and record.levelname == "ERROR"):
                bot.send_message(
                    self.chat_id,
                    self.format(record)
                )
                self.record_flag = record.message


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
telegram_handler = TelegramBotHandler(TELEGRAM_CHAT_ID)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
telegram_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(telegram_handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN == '' or TELEGRAM_TOKEN == '':
        logger.critical('Отсутствие обязательных переменных окружения во '
                        'время запуска бота')
        raise ValueError('Empty string')


def send_message(bot, message):
    """Отправка сообщения в чат Telegram."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp):
    """запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if 'code' in response:
        if response['code'] == 'UnknownError':
            logger.error('Неожиданный статус домашней работы, обнаруженный в '
                         'ответе API')
            raise UnknownError(response['error']['error'])
        else:
            logger.error('Отсутствие ожидаемых ключей в ответе API')
            raise NotAuthenticated(response['message'] + ' '
                                   + response['source'])
    return response['homeworks']


def parse_status(homework):
    """Извлечение статуса конкретной домашней работы."""
    for status in HOMEWORK_VERDICTS:
        if homework['status'] == status:
            homework_name = homework['homework_name']
            verdict = HOMEWORK_VERDICTS['status']
            return (f'Изменился статус проверки работы "{homework_name}". '
                    f'{verdict}')


def main():
    """Основная логика работы бота."""
    check_tokens()

    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
        except EndpointAccess as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        except Exception:
            logger.error('Любые другие сбои при запросе к эндпоинту')

        homeworks = check_response(response)
        if homeworks != []:
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
