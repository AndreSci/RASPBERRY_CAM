import time

import requests
import datetime

from misc.video_thread import create_cams_threads

from misc.ai import AiClass
from misc.utility import SettingsIni
from misc.logger import Logger

DUPLICATE_NUMBERS = dict()


def count_duplicate_in(number, time_recon):
    """ Функция проверяет номер был ли он распознан в ближайшее время и возвращает True или False """
    global DUPLICATE_NUMBERS

    result = True

    today = datetime.datetime.now()

    if number in DUPLICATE_NUMBERS:
        # Если между дубликатами время прошло больше заданного одобряем отправку запроса
        if (today - DUPLICATE_NUMBERS[number]['date_time']).total_seconds() > 15:
            DUPLICATE_NUMBERS[number]['date_time'] = today
        else:
            result = False
    else:
        DUPLICATE_NUMBERS[number] = {'date_time': time_recon}

    # print(DUPLICATE_NUMBERS)

    return result


def duplicate_numbers(recon_numbers: dict):
    """ Принимает в себя словарь распознанных номеров, проверяет на повторы по времени и изменяет его """

    result = dict()

    for it in recon_numbers:

        for number in recon_numbers[it]['numbers']:
            if count_duplicate_in(number, recon_numbers[it]['date_time']):
                result[it] = recon_numbers[it].copy()
                result[it]['date_time'] = str(recon_numbers[it]['date_time'].strftime("%Y-%m-%d/%H.%M.%S"))

    return result


def client(logger: Logger, settings_ini: SettingsIni):
    """ Клиент ра"""
    set_ini = settings_ini.take_settings()

    logger.add_log(f"SUCCESS\tclient\tКлиент RASPBERRY_CAM начал свою работу")  # log

    # Создаем объект для поиска номера на кадре
    plate_recon = AiClass()

    cam_list = create_cams_threads(set_ini['CAMERAS'], logger, plate_recon)

    while True:

        result = dict()
        try:
            result = plate_recon.take_recon_numbers()
        except Exception as ex:
            logger.add_log(f"EXCEPTION\tclient--plate_recon.take_recon_numbers()\t"
                           f"Исключение вызвано при попытке получить результат распознания номеров: {ex}")

        if result:
            result = duplicate_numbers(result)
            request_data = {"RESULT": 'SUCCESS', 'DESC': '', 'DATA': result}

            if result:
                # вместо request пока что принты
                logger.add_log(f"SUCCESS\tclient\tRequest: {result}")  # log
            else:
                print("Не удалось найти новые номера")
        else:
            pass

        time.sleep(0.2)


def main():

    # Подгружаем данные из settings.ini
    settings = SettingsIni()
    result = settings.create_settings()

    fail_col = '\033[91m'
    # end_c = '\033[0m'

    # Проверка успешности загрузки данных
    if not result["result"]:
        print(f"{fail_col}")
        print(f"Ошибка запуска сервиса - {result['desc']}")
        input()
        raise Exception("Service error")

    # Обьявляем логирование
    logger = Logger(settings)

    # Запуск сервера фласк
    client(logger, settings)


if __name__ == '__main__':
    main()
