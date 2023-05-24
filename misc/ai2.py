import cv2
import threading

import utils.consts as consts
import numpy as np
import datetime
from misc.timer import timer_function

PLATES_INITED_MODEL = cv2.dnn.readNet(consts.PLATES_MODEL_PATH)
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

        self.detect_plates = ''
        self.labels = list()

        # Сюда записываем последние распознанные номера
        # {cam1: dict(numbers: ['A100AA77','Y100AA'], parsed: true/false), }
        self.lock_change_nums = threading.Lock()
        self.recon_numbers = dict()

        self.lock_read_pl_on_fr = threading.Lock()
        self.plates_on_frame = {'box': dict(), 'frames_detected': []}

        self.show_frame = ''

        self.allow_recognition = dict()
        self.stop_recon = dict()
        self.threads_for_recon = dict()
        self.cams_frame = dict()

        self.lock_box_rectangle = threading.Lock()
        self.box = dict()

    @timer_function
    def plates_pre_process_frame(self, frame):
        """ Перед отправкой в нейронку нужно произвести с ней манипуляции"""
        # outputs = []
        blob = cv2.dnn.blobFromImage(frame, 0.004,
                                     (consts.PLATES_WIDTH_INPUT, consts.PLATES_HEIGHT_INPUT),
                                     [0, 0, 0], 1,
                                     crop=False)

        print("тут 1")
        self.model_plates.setInput(blob)
        print("тут 2")

        # outputs = self.model_plates.forward(self.model_plates.getUnconnectedOutLayersNames())
        print(self.model_plates.getLayerTypes())
        outputs = self.model_plates.forward(self.model_plates.getUnconnectedOutLayersNames())
        print("тут 3")
        return outputs

    def nums_pre_process_frame(self, frame):
        """ Перед отправкой в нейронку нужно произвеси с ней манипуляции """

        blob = cv2.dnn.blobFromImage(frame, 0.004,
                                     (consts.NUMS_WIDTH_INPUT, consts.NUMS_HEIGHT_INPUT), [0, 0, 0], 1, crop=False)
        self.model_number.setInput(blob)
        outputs = self.model_number.forward(self.model_plates.getUnconnectedOutLayersNames())

        return outputs

    @staticmethod
    def __plates_size_checker(width, height):

        # print(f"{width}x{height}")
        if width > 100:

            return True
        else:
            # return width/height > 1.5
            return False

    @timer_function
    def __plates_post_process(self, input_image, outputs, cam_name) -> dict:
        """ Вытаскиваем координаты найденных номеров из того, что отдала нам нейронка.
            Вытаскивает только те, которые прошли проверку уверенности. Отдает кадры на распознавание символов
            принимает в себя фрейм, который был отправлен в нейронку """

        ret_value = dict()

        class_ids = []
        confidences = []
        boxes = []
        rows = outputs[0].shape[1]
        image_height, image_width = input_image.shape[:2]
        x_factor = image_width / consts.PLATES_WIDTH_INPUT
        y_factor = image_height / consts.PLATES_HEIGHT_INPUT

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

        frames = []

        top_plate = dict()

        for i in indices:
            box = boxes[i]
            width = box[2]
            height = box[3]

            if self.__plates_size_checker(width, height):
                left = box[0]
                top = box[1]

                # Для случая когда на кадре нужно нарисовать дирекцию номера
                ret_value['box'] = {'left': box[0], 'top': box[1], 'width': width, 'height': height}

                # Draw bounding box.
                # cv2.rectangle(input_image, (left, top), (left + width, top + height), BLUE, 3*THICKNESS)
                # cv2.rectangle(input_image, (ret_value['box']['left'], ret_value['box']['top']),
                #               (ret_value['box']['left'] + ret_value['box']['width'], ret_value['box']['top'] +
                #                ret_value['box']['height']), [0, 0, 255], 2 * 1)

                frames.append(input_image[top:top + height, left:left + width])

                if top_plate.get('width'):
                    # Если есть запись и номер больше того что найден, переписываем.
                    if top_plate['width'] < width:
                        top_plate = {'left': box[0], 'top': box[1], 'width': width, 'height': height}
                else:
                    top_plate = {'left': box[0], 'top': box[1], 'width': width, 'height': height}

        with self.lock_box_rectangle:
            # Записываем данные нового plate для кадра
            self.box[cam_name] = top_plate

        ret_value['frames_detected'] = frames
        return ret_value

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

    # Функция для запуска в отдельном потоке для каждой камеры
    def __thread_find(self, cam_name: str):

        while self.stop_recon[cam_name]:  # Если нет команды остановить поток

            if self.allow_recognition[cam_name]:  # Если True начать искать номер
                self.allow_recognition[cam_name] = False
                try:
                    # Получаем время для статистики скорости распознавания
                    start_time = datetime.datetime.now()

                    with self.lock_thread:
                        # result = self.model_plates(self.frame_1)

                        output_of_detections = self.plates_pre_process_frame(self.cams_frame[cam_name])

                        plates = self.__plates_post_process(self.cams_frame[cam_name], output_of_detections, cam_name)
                        # Находим все объекты на кадре

                        # TODO убрать в релизе, если нужно...
                        # Показываем кадр результат тестов +5%-10% к времени распознания
                        self.__img_show(cam_name)

                        with self.lock_read_pl_on_fr:
                            if plates.get('box'):
                                self.plates_on_frame[cam_name] = plates['box']
                            else:
                                self.plates_on_frame[cam_name] = []

                        numbers = list()

                        for frames_out in plates['frames_detected']:
                            numbers.append(self.recon_number(frames_out))

                        if len(numbers) > 0:
                            self.labels = ["".join(num) for num in numbers]

                            numbers_for_req = list()
                            # TODO реализовать на разные страны
                            for num in self.labels:
                                if len(num) > 7:
                                    numbers_for_req.append(num)

                            if numbers_for_req:
                                # Получаем время
                                today = datetime.datetime.now()
                                # date_time = today.strftime("%Y-%m-%d/%H.%M.%S")

                                end_time = datetime.datetime.now()
                                delta_time = (end_time - start_time).total_seconds()

                                with self.lock_change_nums:
                                    self.recon_numbers[cam_name] = {'numbers': numbers_for_req,
                                                                    'parsed': False,
                                                                    'date_time': today,
                                                                    'recognition_speed': delta_time}

                except Exception as ex:
                    print(f"EXCEPTION\tAiClass.__thread_find\tИсключение в работе распознавания номера: {ex}")
                    self.allow_recognition_by_name[cam_name] = True  # Дублирование

                self.allow_recognition_by_name[cam_name] = True

    def find_plates(self, frame, cam_name: str):
        """ Функция начала распознавания номера в отдельном потоке """
        if cam_name not in self.allow_recognition_by_name:
            self.allow_recognition_by_name[cam_name] = True

        if self.allow_recognition_by_name[cam_name]:
            self.allow_recognition_by_name[cam_name] = False

            if cam_name in self.threads_for_recon:
                # Если есть живой поток для камеры
                self.allow_recognition[cam_name] = True
                self.cams_frame[cam_name] = frame  # Дублирование
            else:
                try:
                    # тогда пробуем создать поток для камеры
                    self.stop_recon[cam_name] = True
                    self.allow_recognition[cam_name] = True

                    self.cams_frame[cam_name] = frame  # Дублирование

                    self.threads_for_recon[cam_name] = \
                        threading.Thread(target=self.__thread_find, args=[cam_name, ])

                    self.threads_for_recon[cam_name].start()

                    print(f"БЫЛ СОЗДАН ПОТОК ДЛЯ КАМ: {cam_name}")
                except Exception as ex:
                    print(f"EXCEPTION\tAiClass.find_plates\tИсключение вызвала "
                          f"попытка создания потока для распознавания: {ex}")
                    self.allow_recognition_by_name[cam_name] = True

    def recon_number(self, frame) -> list:
        """ Возвращает номер в виде списка элементов номера """
        result_of_numbers = list()

        try:
            # cv2.imwrite(os.path.join(consts.TEMP_PATH, "test.jpg"), frame)

            output_of_detection_numbers = self.nums_pre_process_frame(frame)
            # Отправляем на распознание
            result_of_numbers = self.__nums_post_process(frame, output_of_detection_numbers)

        except Exception as ex:
            print(f"EXCEPTION\tAiClass.recon_number()\t{ex}")

        return result_of_numbers

    def take_recon_numbers(self):

        with self.lock_change_nums:
            copy_rec = dict()

            # Проверяем на новые события
            for it in self.recon_numbers:
                if not self.recon_numbers[it]['parsed']:
                    copy_rec[it] = self.recon_numbers[it].copy()
                    self.recon_numbers[it]['parsed'] = True

            return copy_rec

    def take_plate_box(self, cam_name):

        if self.plates_on_frame.get(cam_name):
            with self.lock_read_pl_on_fr:
                return self.plates_on_frame[cam_name].copy()
        else:
            return []

    def draw_plates(self, frame, cam_name):
        box = self.take_plate_box(cam_name)
        # Draw bounding box.
        if box:
            cv2.rectangle(frame, (box['left'], box['top']),
                          (box['left'] + box['width'], box['top'] + box['height']), [0, 0, 255], 2 * 1)

            # Показываем кадр с нарисованным квадратом
            cv2.imshow(f'show: {cam_name}', frame)
            cv2.waitKey(10)

    def __img_show(self, cam_name):
        """ Функция выводик кадр в отдельном окне с размеченным номером """

        with self.lock_box_rectangle:
            if self.box.get(cam_name):
                if self.box[cam_name]:

                    cv2.rectangle(self.cams_frame[cam_name], (self.box[cam_name]['left'], self.box[cam_name]['top']),
                                  (self.box[cam_name]['left'] + self.box[cam_name]['width'], self.box[cam_name]['top'] +
                                   self.box[cam_name]['height']), [0, 0, 255], 2 * 1)

        # Показываем кадр с нарисованным квадратом
        cv2.imshow(f'show: {cam_name}', self.cams_frame[cam_name])
        cv2.waitKey(10)


if __name__ == '__main__':
    print(num_to_rus(['e100kk777', '0111pp999', '123pp555']))