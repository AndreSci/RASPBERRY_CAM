from misc.utility import SettingsIni
from misc.logger import Logger
from server import web_flask
import ctypes


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

    port = settings.settings_ini["port"]

    # Меняем имя терминала
    # TODO Убрать для Linux
    # ctypes.windll.kernel32.SetConsoleTitleW(f"Client Wheel_CAM port: {port}")

    # Обьявляем логирование
    logger = Logger(settings)

    # Запуск сервера фласк
    web_flask(logger, settings)


if __name__ == '__main__':
    main()
