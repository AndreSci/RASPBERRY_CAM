import time

import cv2
import threading

from misc.logger import Logger
from misc.ai6 import AiClass
from utils import consts


class ThreadVideoRTSP:
    """ Класс получения видео из камеры"""
    def __init__(self, cam_name: str, url, plate_recon: AiClass,
                 camera_speed=consts.CAM_SPEED, recon_freq=consts.RECON_FREQ):
        # Настройки камеры
        self.url = url
        self.cam_name = cam_name
        # Частота кадров и с какой периодичность отправлять на распознание (camera_speed * recon_freq)
        self.camera_speed = camera_speed
        self.recon_freq = recon_freq

        self.last_frame = b''

        self.th_do_frame_lock = threading.Lock()

        self.allow_read_frame = True
        self.no_exception_in_read_frame = True  # Случай если было исключение в работе с получением кадра
        self.do_frame = False

        self.url_frame = f'./temp/frame_{self.cam_name}.jpg'

        self.thread_is_alive = False
        self.thread_object = None

        # Ссылка на объект классна распознавания
        self.plate_recon = plate_recon

    def start(self, logger: Logger):

        if not self.thread_is_alive:
            self.allow_read_frame = True
            self.no_exception_in_read_frame = True

            logger.add_log(f"EVENT\tПопытка подключиться к камере: {self.cam_name} - {self.url}")

            with self.th_do_frame_lock:
                self.thread_object = threading.Thread(target=self.__start, daemon=True, args=[logger, ])
                self.thread_object.start()
                self.thread_is_alive = True
        else:
            logger.add_log(f"WARNING\tНе удалось запустить поток для камеры {self.cam_name} - {self.url}, "
                           f"занят другим делом.")

    def __start(self, logger: Logger):
        """ Функция подключения и поддержки связи с камерой """

        capture = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)

        if capture.isOpened():
            logger.add_log(f"SUCCESS\tThreadVideoRTSP.start()\t"
                                                            f"Создано подключение к {self.cam_name} - {self.url}")

        frame_fail_cnt = 0
        frame_index = 0

        try:
            while True:
                if not capture.isOpened():
                    break

                ret, frame = capture.read()  # читать кадр

                with self.th_do_frame_lock:

                    frame_index += 1

                    if ret:
                        # if frame_index > (self.camera_speed * self.recon_freq) and ret:

                        frame_index = 0
                        frame_fail_cnt = 0

                        self.plate_recon.find_plates(frame, self.cam_name)

                    elif not ret:
                        # Собираем статистику неудачных кадров
                        time.sleep(0.02)
                        frame_fail_cnt += 1

                        # Если много неудачных кадров останавливаем поток и пытаемся переподключить камеру
                        if frame_fail_cnt == 50:
                            logger.add_log(f"WARNING\tThreadVideoRTSP.start()\t"
                                           f"{self.cam_name} - "
                                           f"Слишком много неудачных кадров, повторное переподключение к камере.")
                            break
                    else:
                        frame_fail_cnt = 0

        except Exception as ex:
            logger.add_log(f"EXCEPTION\tThreadVideoRTSP.__start\t"
                           f"Исключение вызвала ошибка в работе с видео потоком для камеры {self.cam_name}: {ex}")
            self.no_exception_in_read_frame = False

        logger.add_log(f"WARNING\tThreadVideoRTSP.start()\t{self.cam_name} - Камера отключена: {self.url}")
        self.thread_is_alive = False

        try:
            # Освобождаем
            capture.release()
        except Exception as ex:
            logger.add_log(f"EXCEPTION\tThreadVideoRTSP.start()\t"
                            f"{self.cam_name} - Исключение вызвал метод освобождения capture.release(): {ex}")

        # Если разрешено чтение кадров переподключаем камеру
        if self.allow_read_frame:
            self.start(logger)
        cv2.destroyAllWindows()

    def take_frame(self):
        """ Функция выгружает байт-код кадра из файла """

        return self.last_frame


def create_cams_threads(cams_from_settings: dict, logger: Logger, plate_recon: AiClass) -> dict:
    """ Функция создает словарь с объектами класса ThreadVideoRTSP и запускает от их имени потоки """
    cameras = dict()

    for key in cams_from_settings:
        cameras[key] = ThreadVideoRTSP(key, cams_from_settings[key], plate_recon)
        cameras[key].start(logger)

    return cameras
