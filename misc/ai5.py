import cv2
import threading

import utils.consts as consts
import numpy as np
import datetime
from misc.timer import timer_function

from ultralytics import YOLO

# define some constants
CONFIDENCE_THRESHOLD = 0.8
GREEN = (0, 255, 0)

PLATES_INITED_MODEL = YOLO(consts.PLATES_Y8_MODEL_PATH)
NUMBERS_INITED_MODEL = YOLO(consts.NUMS_Y8_MODEL_PATH)


def num_to_rus(numbers: list):
    ru_number = list()

    for num in numbers:
        if num[0] == 0:
            num[0] = 'О'
        elif num[0].isdigit():
            continue

        if not num[1].isdigit() or num[2].isdigit() or num[3].isdigit():
            continue

        ru_number.append(num)

    return ru_number


class DetectNumber:

    @staticmethod
    def find_number(frame):

        frame = cv2.resize(frame, (consts.NUMS_WIDTH_INPUT, consts.NUMS_HEIGHT_INPUT))
        recon_items = NUMBERS_INITED_MODEL(frame, verbose=False,
                                           conf=consts.CONFIDENCE_THRESHOLD, save=False, stream=True)
        list_of_x_and_classes = []

        res = ""

        for result in recon_items:

            boxes = result.boxes.cpu().numpy()
            classes = boxes.cls

            for i in range(len(boxes)):
                list_of_x_and_classes.append((boxes.xyxy[i][0], result.names[int(classes[i])]))
                # print(f"class = {result.names[int(classes[i])]}, x={boxes.xyxy[i][0]}")
            list_of_x_and_classes.sort()

            if list_of_x_and_classes:
                for _, cls in list_of_x_and_classes:
                    res += cls

        return res
        # Boxes object for bbox outputs


class AiClass(DetectNumber):
    def __init__(self):
        global NUMBERS_INITED_MODEL, PLATES_INITED_MODEL

        self.model_plates = PLATES_INITED_MODEL
        self.model_number = NUMBERS_INITED_MODEL

        self.lock_thread_plate = threading.Lock()
        self.lock_thread_num = threading.Lock()
        self.allow_recognition_by_name = dict()

        self.labels = list()

        # Сюда записываем последние распознанные номера
        # {cam1: dict(numbers: ['A100AA77','Y100AA'], parsed: true/false), }
        self.lock_change_nums = threading.Lock()
        self.recon_numbers = dict()

        self.allow_rec_lock = threading.Lock()
        self.allow_recognition = dict()

        self.start_recon = dict()
        self.threads_for_recon = dict()
        self.cams_frame = dict()

        self.lock_box_rectangle = threading.Lock()

        self.detections = dict()

    # done
    def __plates_process_recon(self, frame):
        """ Перед отправкой в нейронку нужно произвести с ней манипуляции"""
        # run the YOLO model on the frame

        recon_items = self.model_plates(frame, verbose=False)

        biggest = list()

        for data in recon_items[0].boxes.data.tolist():
            # extract the confidence (i.e., probability) associated with the detection
            confidence = data[4]

            # filter out weak detections by ensuring the
            # confidence is greater than the minimum confidence
            if float(confidence) < CONFIDENCE_THRESHOLD:
                continue

            # if the confidence is greater than the minimum confidence,
            # draw the bounding box on the frame
            xmin, ymin, xmax, ymax = int(data[0]), int(data[1]), int(data[2]), int(data[3])

            if not biggest:
                biggest = [xmin, ymin, xmax, ymax]
            elif (biggest[2] - biggest[0]) < (xmax - xmin):
                biggest = [xmin, ymin, xmax, ymax]

        return biggest

    def recon_number(self, cam_name) -> list:
        """ Возвращает номер в виде списка элементов номера """
        result_of_numbers = list()

        if len(self.detections[cam_name]) == 4:
            xmin, ymin, xmax, ymax = self.detections[cam_name]

            # Вырезаем номер из кадра
            crop_img = self.cams_frame[cam_name][ymin:ymax, xmin:xmax]

            if consts.DEBUG_MODE:
                cv2.imshow(f'{cam_name}', crop_img)
                cv2.waitKey(1)

            result_of_numbers = self.find_number(crop_img)

        return result_of_numbers

    # done
    def take_recon_numbers(self) -> dict:

        with self.lock_change_nums:
            copy_rec = dict()

            # Проверяем на новые события
            for it in self.recon_numbers:
                if not self.recon_numbers[it]['parsed']:
                    copy_rec[it] = self.recon_numbers[it].copy()
                    self.recon_numbers[it]['parsed'] = True

            return copy_rec

    # ФУНКЦИЯ СТАРТ
    def find_plates(self, frame, cam_name: str):
        """ Функция начала распознавания номера в отдельном потоке """
        if cam_name not in self.allow_recognition_by_name:
            self.allow_recognition_by_name[cam_name] = True

        if self.allow_recognition_by_name[cam_name]:
            self.allow_recognition_by_name[cam_name] = False

            self.cams_frame[cam_name] = frame.copy()

            with self.allow_rec_lock:
                self.allow_recognition[cam_name] = True

            if cam_name not in self.threads_for_recon:
                # тогда пробуем создать поток для камеры
                try:
                    self.start_recon[cam_name] = True

                    self.threads_for_recon[cam_name] = \
                        threading.Thread(target=self.__thread_find, args=[cam_name, ])

                    self.threads_for_recon[cam_name].start()

                    print(f"БЫЛ СОЗДАН ПОТОК ДЛЯ КАМЕРА: {cam_name}")
                except Exception as ex:
                    print(f"EXCEPTION\tAiClass.find_plates\tИсключение вызвала "
                          f"попытка создания потока для распознавания: {ex}")
                    self.allow_recognition_by_name[cam_name] = True

    # Функция для запуска в отдельном потоке для каждой камеры
    def __thread_find(self, cam_name: str):

        while self.start_recon[cam_name]:  # Если нет команды остановить поток

            if self.allow_recognition[cam_name]:  # Если True начать искать номер
                self.allow_recognition[cam_name] = False

                # Получаем время для статистики скорости распознавания
                start_time = datetime.datetime.now()

                try:
                    with self.lock_thread_plate:

                        # run the YOLO model on the frame

                        self.detections[cam_name] = self.__plates_process_recon(self.cams_frame[cam_name])

                        # TODO убрать в релизе, если нужно...
                        # Показываем кадр результат тестов +5%-10% к времени распознания
                        if consts.DEBUG_MODE:
                            self.__img_show(cam_name)

                    with self.lock_thread_num:
                        number = self.recon_number(cam_name)

                        if len(number) > 0:
                            number = ''.join(number)
                            # # TODO реализовать на разные страны

                            if len(number) > consts.LEN_FOR_NUMBER:
                                # Получаем время
                                today = datetime.datetime.now()
                                # date_time = today.strftime("%Y-%m-%d/%H.%M.%S")

                                end_time = datetime.datetime.now()
                                delta_time = (end_time - start_time).total_seconds()

                                with self.lock_change_nums:
                                    self.recon_numbers[cam_name] = {'numbers': [number, ],
                                                                    'parsed': False,
                                                                    'date_time': today,
                                                                    'recognition_speed': delta_time}

                except Exception as ex:
                    print(f"EXCEPTION\tAiClass.__thread_find\tИсключение в работе распознавания номера: {ex}")
                    self.allow_recognition_by_name[cam_name] = True  # Дублирование

                self.allow_recognition_by_name[cam_name] = True

    # done
    def __img_show(self, cam_name):
        """ Функция выводик кадр в отдельном окне с размеченным номером """
        if consts.DEBUG_MODE:
            with self.lock_box_rectangle:
                if len(self.detections[cam_name]) == 4:
                    xmin, ymin, xmax, ymax = self.detections[cam_name]
                    cv2.rectangle(self.cams_frame[cam_name], (xmin, ymin), (xmax, ymax), GREEN, 2)

            # Показываем кадр с нарисованным квадратом
            cv2.imshow(f'show: {cam_name}', self.cams_frame[cam_name])
            cv2.waitKey(10)
