import logging
import os
import time
import requests

from dotenv import load_dotenv
from logging.handlers import StreamHandler

import telegram

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
handler = StreamHandler('my_logger.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info('Сообщение отправлено в Telegram')


def get_api_answer(current_timestamp):
    """Запрос данных с сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError


def check_response(response):
    """Проверка ответа сервера."""
    if not response:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
        raise ValueError
    if isinstance(response, dict):
        homework = response.get('homeworks')
    else:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
        raise TypeError
    if isinstance(homework, list):
        if response.get('homeworks') is not None:
            return response.get('homeworks')
        else:
            logger.error('Отсутствие ожидаемых ключей в ответе API')
            raise KeyError
    else:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
        raise TypeError


def parse_status(homework):
    """Парсинг статусов."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is not None:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise KeyError


def check_tokens():
    """Проверка наличия токенов."""
    if PRACTICUM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"PRACTICUM_TOKEN"'
                        'Программа принудительно остановлена.')
    if TELEGRAM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_TOKEN"'
                        'Программа принудительно остановлена.')
    if TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_CHAT_ID"'
                        'Программа принудительно остановлена.')
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        raise ValueError
    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)
        else:
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)


if __name__ == '__main__':
    main()
