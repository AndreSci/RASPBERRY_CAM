import time

import requests

from misc.video_thread import ThreadVideoRTSP
from misc.video_thread import create_cams_threads

from misc.ai import AiClass
from misc.utility import SettingsIni
from misc.logger import Logger
from main import web_flask
import ctypes


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
            request_data = {"RESULT": 'SUCCESS', 'DESC': '', 'DATA': result}

            # вместо request пока что принты
            logger.add_log(f"SUCCESS\tclient\tRequest: {result}")  # log
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
