from flask import Flask, request, jsonify, Response

from misc.logger import Logger
from misc.utility import SettingsIni

import logging

ERROR_ACCESS_IP = 'access_block_ip'
ERROR_READ_REQUEST = 'error_read_request'
ERROR_ON_SERVER = 'server_error'


def block_flask_logs():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)


def web_flask(logger: Logger, settings_ini: SettingsIni):
    """ Главная функция создания сервера Фласк. """

    app = Flask(__name__)  # Объявление сервера

    app.config['JSON_AS_ASCII'] = False

    # Блокируем сообщения фласк
    # block_flask_logs()

    set_ini = settings_ini.take_settings()

    logger.add_log(f"SUCCESS\tweb_flask\tСервер RASPBERRY_Flask начал свою работу по")  # log

    @app.route('/OnHeartBeat', methods=['GET'])
    def take_frame():
        """ Удаляет заявку на создание пропуска если FStatusID = 1 \n
        принимает user_id, inn и fid заявки """

        json_replay = {"RESULT": "ERROR", "DESC": "", "DATA": dict()}

        # получаем данные из параметров запроса
        res_request = request.json

        try:
            # Получить кадр
            if 'DATA' in res_request:

                if res_request['DATA']:
                    json_replay['RESULT'] = 'SUCCESS'
                    print(f"Request-in: {res_request}")
                else:
                    json_replay['RESULT'] = 'EMPTY'

            print(f"Request-out: {json_replay}")

        except Exception as ex:
            logger.add_log(f"EXCEPTION\tOnHeartBeat\tОшибка работы с данными: {ex}")

        return jsonify(json_replay)

    # RUN SERVER FLASK  ------
    app.run(debug=False, host=set_ini["host"], port=int(set_ini["port"]))
