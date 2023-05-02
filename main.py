from misc.video_thread import ThreadVideoRTSP
from misc.video_thread import create_cams_threads
from flask import Flask, request, jsonify, Response

from misc.logger import Logger
from misc.utility import SettingsIni
from misc.ai import AiClass

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
    block_flask_logs()

    set_ini = settings_ini.take_settings()

    logger.add_log(f"SUCCESS\tweb_flask\tСервер RASPBERRY_Flask начал свою работу")  # log

    # Создаем объект для поиска номера на кадре
    plate_recon = AiClass()

    cam_list = create_cams_threads(set_ini['CAMERAS'], logger, plate_recon)

    @app.route('/action.do', methods=['GET'])
    def take_frame():
        """ Удаляет заявку на создание пропуска если FStatusID = 1 \n
        принимает user_id, inn и fid заявки """

        json_replay = {"RESULT": "ERROR", "DESC": "", "DATA": ""}

        # получаем данные из параметров запроса
        res_request = request.args

        # cam_name = str(res_request.get('cam_name'))
        cam_name = str(res_request.get('video_in'))
        cam_name = 'cam' + cam_name[cam_name.find(':') + 1:]

        try:
            # Получить кадр
            frame = cam_list[cam_name].take_frame()
        except Exception as ex:
            frame = ''
            logger.add_log(f"EXCEPTION\ttake_frame()\tНе удалось получить кадр из камеры: {ex}")

        return Response(frame, mimetype='image/jpeg')

    @app.route('/start.cam', methods=['GET'])
    def start_cam():
        """ Включает получение видео потока от указанной каменры """

        json_replay = {"RESULT": "ERROR", "DESC": "", "DATA": ""}

        # получаем данные из параметров запроса
        res_request = request.args

        # cam_name = str(res_request.get('cam_name'))
        cam_name = str(res_request.get('name'))

        cam_list[cam_name].start(logger)

        json_replay['RESULT'] = "SUCCESS"

        return jsonify(json_replay)

    @app.route('/stop.cam', methods=['GET'])
    def stop_cam():
        """ Удаляет заявку на создание пропуска если FStatusID = 1 \n
        принимает user_id, inn и fid заявки """

        json_replay = {"RESULT": "ERROR", "DESC": "", "DATA": ""}

        # получаем данные из параметров запроса
        res_request = request.args

        cam_name = str(res_request.get('name'))

        cam_list[cam_name].stop()

        json_replay['RESULT'] = "SUCCESS"

        return jsonify(json_replay)

    # RUN SERVER FLASK  ------
    app.run(debug=False, host=set_ini["host"], port=int(set_ini["port"]))
