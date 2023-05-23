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
# PLATES_INITED_MODEL = cv2.dnn.readNet('best.onnx')
NUMBERS_INITED_MODEL = cv2.dnn.readNet(consts.NUMS_MODEL_PATH)


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


def pasr_detection(x_list: list, id_char: list, confidence: list):
    """Проходим по всем элементам номера"""

    # Объединяем для упорядочивания вывода номера
    zip_res = zip(x_list, id_char, confidence)
    zip_list = list(zip_res)

    # Сортируем от меньшего к большему (то же что от левого объекта к правому)
    zip_list.sort()
    number_list = list()

    # Формируем номер
    for _, ind, conf in zip_list:
        if conf > consts.CONF_LVL:
            number_list.append(str(consts.CLASS_ID[ind]))

    return number_list


class AiClass:
    def __init__(self):
        global NUMBERS_INITED_MODEL, PLATES_INITED_MODEL

        self.model_plates = PLATES_INITED_MODEL
        self.model_number = NUMBERS_INITED_MODEL

        self.lock_thread = threading.Lock()
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

    def nums_pre_process_frame(self, frame):
        """ Перед отправкой в нейронку нужно произвеси с ней манипуляции """

        blob = cv2.dnn.blobFromImage(frame, 0.004,
                                     (consts.NUMS_WIDTH_INPUT, consts.NUMS_HEIGHT_INPUT), [0, 0, 0], 1, crop=False)
        self.model_number.setInput(blob)
        outputs = self.model_number.forward(self.model_number.getUnconnectedOutLayersNames())

        return outputs

    @staticmethod
    def __nums_post_process(input_image, outputs):
        """Вытаскиваем координаты найденных номеров из того, что отдала нам нейронка.
            Вытаскивает только те, которые прошли проверку уверенности. Отдает кадры на распознавание символов
            принимает в себя фрейм, который был отправлен в нейронку"""
        class_ids = []
        confidences = []
        boxes = []
        rows = outputs[0].shape[1]

        image_height, image_width = input_image.shape[:2]
        x_factor = image_width / consts.NUMS_WIDTH_INPUT
        y_factor = image_height / consts.NUMS_HEIGHT_INPUT

        for r in range(rows):

            row = outputs[0][0][r]
            confidence = row[4]

            if confidence >= consts.CONFIDENCE_THRESHOLD:

                classes_scores = row[5:]
                class_id = np.argmax(classes_scores)

                if classes_scores[class_id] > consts.SCORE_THRESHOLD:
                    confidences.append(confidence)
                    class_ids.append(class_id)
                    cx, cy, w, h = row[0], row[1], row[2], row[3]
                    left = int((cx - w / 2) * x_factor)
                    top = int((cy - h / 2) * y_factor)
                    width = int(w * x_factor)
                    height = int(h * y_factor)
                    box = np.array([left, top, width, height])
                    boxes.append(box)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, consts.CONFIDENCE_THRESHOLD, consts.NMS_THRESHOLD)

        # detected_num = []
        pars_x_list = []
        pars_confid = []
        pars_class_id = []

        for i in indices:
            box = boxes[i]
            left = box[0]
            pars_x_list.append(left)

            pars_confid.append(confidences[i])
            pars_class_id.append(class_ids[i])

        detected_num = pasr_detection(pars_x_list, pars_class_id, pars_confid)
        # print(f"nums = {detected_num}")

        return detected_num

    def recon_number(self, cam_name) -> list:
        """ Возвращает номер в виде списка элементов номера """
        result_of_numbers = list()

        if len(self.detections[cam_name]) == 4:
            xmin, ymin, xmax, ymax = self.detections[cam_name]

            crop_img = self.cams_frame[cam_name][ymin:ymax, xmin:xmax]
            #
            # cv2.imshow('te', crop_img)
            # cv2.waitKey(1)

            output = self.nums_pre_process_frame(crop_img)

            result_of_numbers = self.__nums_post_process(crop_img, output)

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

            with self.allow_rec_lock:
                allow_rec = self.allow_recognition[cam_name]

            if allow_rec:  # Если True начать искать номер

                with self.allow_rec_lock:
                    self.allow_recognition[cam_name] = False

                try:
                    # Получаем время для статистики скорости распознавания
                    start_time = datetime.datetime.now()

                    with self.lock_thread:

                        # run the YOLO model on the frame

                        self.detections[cam_name] = self.__plates_process_recon(self.cams_frame[cam_name])

                        # TODO убрать в релизе, если нужно...
                        # Показываем кадр результат тестов +5%-10% к времени распознания
                        self.__img_show(cam_name)

                        # TODO сюда нужно добавить распознание номера
                        number = self.recon_number(cam_name)

                        if len(number) > 0:
                            # self.labels = ["".join(num) for num in number]
                            number = ''.join(number)

                            # numbers_for_req = list()
                            # # TODO реализовать на разные страны
                            # for num in self.labels:
                            #     if len(num) > consts.LEN_FOR_NUMBER:
                            #         numbers_for_req.append(num)

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

        with self.lock_box_rectangle:

            if len(self.detections[cam_name]) == 4:
                xmin, ymin, xmax, ymax = self.detections[cam_name]
                cv2.rectangle(self.cams_frame[cam_name], (xmin, ymin), (xmax, ymax), GREEN, 2)

        # Показываем кадр с нарисованным квадратом
        cv2.imshow(f'show: {cam_name}', self.cams_frame[cam_name])
        cv2.waitKey(10)
