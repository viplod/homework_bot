import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from config import (ENDPOINT, HEADERS, HOMEWORK_STATUSES, PRACTICUM_TOKEN,
                    RETRY_TIME, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
from exceptions import (EndpointResponseExceptionError,
                        SendMessageExceptionError)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.error('Сообщение не отправлено в Telegram', error)
        raise SendMessageExceptionError(
            f'Ошибка отправки сообщения в Telegram {error}'
        )
    logger.info('Сообщение отправлено в Telegram', message)


def get_api_answer(current_timestamp):
    """Запрос данных с сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if response.status_code == HTTPStatus.OK:
        return response.json()
    logger.error(
        'Недоступен эндпоинт '
        'https://practicum.yandex.ru/api/user_api/homework_statuses/ '
        'статус ответа=', response.status_code)
    raise EndpointResponseExceptionError(f'Недоступен эндпоинт {ENDPOINT}')


def check_response(response):
    """Проверка ответа сервера."""
    if not response:
        logger.error('Отсутствуют данные в ответе API')
        raise ValueError
    if not isinstance(response, dict):
        logger.error('Неверные тип данных response в ответе API')
        raise TypeError
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        logger.error('Неверные тип данных ключа homeworks в ответе API')
        raise TypeError
    if response.get('homeworks') is None:
        logger.error('Отсутствует ключ homeworks в ответе API')
        raise KeyError
    return response.get('homeworks')


def parse_status(homework):
    """Парсинг статусов."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error('Отсутствие ожидаемый ключ homework_name в ответе API')
    homework_status = homework.get('status')
    if homework_status is None:
        logger.error('Отсутствие ожидаемый ключ status в ответе API')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logger.error(f'Недокументированный статус домашней работы,'
                     f'обнаруженный в ответе API, {homework_status}')
        raise KeyError
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    return all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Отсутствует обязательная переменная окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        else:
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug('Отсутствие в ответе новых статусов')
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    handler_stdout = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler_stdout)
    logger.setLevel(logging.INFO)
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Принудительное завершение работы программы')
