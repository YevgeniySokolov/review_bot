import os
import sys
import time
import logging
from logging import StreamHandler

import requests
from dotenv import load_dotenv
import telegram

from exceptions import OtherStatusCode, APIRequestException, TelegramException

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

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
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        raise ValueError('Пустая строка')


def send_message(bot, message):
    """Отправка сообщения в чат Telegram."""
    logger.debug('Начало отправки сообщения в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        raise TelegramException('Сбой при отправке сообщения в Telegram')
    logger.debug('Сообщение успешно отправлено в Telegram')


def get_api_answer(timestamp):
    """запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    logger.debug('Начало запроса к API')
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS,
                                         params=payload)
    except Exception as error:
        raise APIRequestException(f'Сбой при запросе к API: {error}. '
                                  f'Endpoint {ENDPOINT}, '
                                  f'headers {HEADERS}, '
                                  f'params {payload}')
    status_code = homework_statuses.status_code
    if status_code != 200:
        raise OtherStatusCode(f'Статус-код: {status_code}.')
    try:
        response = homework_statuses.json()
    except ValueError:
        raise ValueError('Сбой при выполнении метода .json()')
    return response


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    logger.debug('Начало проверки ответа сервера')
    if not isinstance(response, dict):
        raise TypeError(f'Некорректный тип данных. '
                        f'Тип данных: {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('В ответе API домашки нет ключа `homeworks`')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(f'Некорректный тип данных. '
                        f'Тип данных: {type(homeworks)}')
    if homeworks:
        return homeworks
    else:
        logger.debug('Отсутствие в ответе новых статусов')


def parse_status(homework):
    """Извлечение статуса конкретной домашней работы."""
    status = homework['status']
    homework_name = homework.get('homework_name')
    if not status:
        raise ValueError('Пустая строка')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Недокументированный статус')
    if homework_name is None:
        raise KeyError('Нет ключа homework_name.')
    return (f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[status]}')


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except ValueError:
        logger.critical('Отсутствие обязательных переменных окружения во '
                        'время запуска бота')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            new_message = parse_status(homeworks[0])
            send_message(bot, new_message)
            timestamp = response['current_date']
        except TypeError as err:
            msg = err.args
            logger.error(msg)
        except KeyError as err:
            msg = err.args
            logger.error(msg)
        except OtherStatusCode as err:
            msg = err.args
            logger.error(msg)
        except ValueError as err:
            msg = err.args
            logger.error(msg)
        except APIRequestException as err:
            msg = err.args
            logger.error(msg)
            if msg != message:
                send_message(bot, msg)
                message = msg
        except TelegramException as err:
            msg = err.args
            logger.error(msg)
        except Exception as error:
            logger.error(f'Неожиданный сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
