import logging
import sys
import time
import requests

from dotenv import load_dotenv
import telegram

import config

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
handler_stdout = logging.StreamHandler(sys.stdout)
logger.addHandler(handler_stdout)
logger.setLevel(logging.INFO)


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(config.TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.error('Сообщение не отправлено в Telegram', error)
    logger.info('Сообщение отправлено в Telegram', message)


def get_api_answer(current_timestamp):
    """Запрос данных с сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        config.ENDPOINT,
        headers=config.HEADERS,
        params=params
    )
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(
            'Недоступен эндпоинт '
            'https://practicum.yandex.ru/api/user_api/homework_statuses/ '
            'статус ответа=', response.status_code)
        raise ValueError


def check_response(response):
    """Проверка ответа сервера."""
    if not response:
        logger.error('Отсутствуют данные в ответе API')
        raise ValueError
    if isinstance(response, dict):
        homework = response.get('homeworks')
    else:
        logger.error('Неверные тип данных response в ответе API')
        raise TypeError
    if isinstance(homework, list):
        if response.get('homeworks') is not None:
            return response.get('homeworks')
        else:
            logger.error('Отсутствует ключ homeworks в ответе API')
            raise KeyError
    else:
        logger.error('Неверные тип данных ключа homeworks в ответе API')
        raise TypeError


def parse_status(homework):
    """Парсинг статусов."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error('Отсутствие ожидаемый ключ homework_name в ответе API')
    homework_status = homework.get('status')
    if homework_status is None:
        logger.error('Отсутствие ожидаемый ключ status в ответе API')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is not None:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logger.error(f'Недокументированный статус домашней работы,'
                     f'обнаруженный в ответе API, {homework_status}')
        raise KeyError


def check_tokens():
    """Проверка наличия токенов."""
    if config.PRACTICUM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"PRACTICUM_TOKEN"'
                        'Программа принудительно остановлена.')
    if config.TELEGRAM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_TOKEN"'
                        'Программа принудительно остановлена.')
    if config.TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_CHAT_ID"'
                        'Программа принудительно остановлена.')
    return (
        config.PRACTICUM_TOKEN
        and config.TELEGRAM_TOKEN
        and config.TELEGRAM_CHAT_ID
    )


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=config.TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        raise ValueError
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = int(time.time())
            time.sleep(config.RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(config.RETRY_TIME)
        else:
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug('Отсутствие в ответе новых статусов')
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)


if __name__ == '__main__':
    main()
