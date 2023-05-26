from multiprocessing import Process
import time

import requests
import datetime

from misc.video_thread import create_cams_threads

from misc.ai5 import AiClass
from misc.utility import SettingsIni
from misc.logger import Logger

from utils import consts

DUPLICATE_NUMBERS = dict()


def count_duplicate_in(number, time_recon):
    """ Функция проверяет номер был ли он распознан в ближайшее время и возвращает True или False """
    global DUPLICATE_NUMBERS

    result = True

    today = datetime.datetime.now()

    if number in DUPLICATE_NUMBERS:
        # Если между дубликатами время прошло больше заданного одобряем отправку запроса
        if (today - DUPLICATE_NUMBERS[number]['date_time']).total_seconds() > consts.CAR_REPEAT:
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


def client(settings, cameras):
    """ Клиент ра"""

    # Обьявляем логирование
    logger = Logger(settings)

    logger.add_log(f"SUCCESS\tclient\tКлиент RASPBERRY_CAM начал свою работу")  # log

    # Создаем объект для поиска номера на кадре
    plate_recon = AiClass()

    # Объект всех камер
    cam_list = create_cams_threads(cameras, logger, plate_recon)

    barrier = BarrierClass()

    while True:

        number = plate_recon.take_recon_numbers()

        request_data = {"RESULT": 'EMPTY', 'DESC': '', 'DATA': dict()}

        if number:
            number = duplicate_numbers(number)
            request_data = {"RESULT": 'SUCCESS', 'DESC': '', 'DATA': number}

            if number:  # TODO заменить на поиск в базе
                if not consts.DEBUG_MODE:
                    barrier.open()
                # вместо request пока что принты
                logger.add_log(f"SUCCESS\tclient\tRequest: {number}")  # log

        else:
            pass

        try:
            req = requests.get(f'http://{consts.SERVER_HOST}:{consts.SERVER_PORT}/OnHeartBeat',
                               json=request_data, timeout=1)

            print(req.json())
        except Exception as ex:
            print(f"Тайм-аут ошибка: {ex}")

        time.sleep(2)


def main_process():

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

    set_ini = settings.take_settings()
    process_list = list()

    for cam_name in set_ini['CAMERAS']:
        process_list.append(Process(target=client, args=(settings, {cam_name: set_ini['CAMERAS'][cam_name]})))

    for proc in process_list:
        proc.start()
        time.sleep(1)

    for proc in process_list:
        proc.join()


if __name__ == '__main__':
    main_process()

    print("Конец Процессам")
