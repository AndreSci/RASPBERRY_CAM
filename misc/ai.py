import cv2
import threading
import os
import utils.consts as consts
import numpy as np

PLATES_INITED_MODEL = cv2.dnn.readNet(consts.PLATES_MODEL_PATH)
NUMBERS_INITED_MODEL = cv2.dnn.readNet(consts.NUMS_MODEL_PATH)


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

        self.frame_1 = ''

        self.detect_plates = ''
        self.labels = list()
    
    def plates_pre_process_frame(self, frame):
        """ Перед отправкой в нейронку нужно произвести с ней манипуляции"""
        outputs = []
        blob = cv2.dnn.blobFromImage(frame, 0.004,
                                     (consts.PLATES_WIDTH_INPUT, consts.PLATES_HEIGHT_INPUT),
                                     [0, 0, 0], 1,
                                     crop=False)
        self.model_plates.setInput(blob)

        outputs = self.model_plates.forward(self.model_plates.getUnconnectedOutLayersNames())

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
        return width/height > 1.5

    def __plates_post_process(self, input_image, outputs):
        """ Вытаскиваем координаты найденных номеров из того, что отдала нам нейронка.
            Вытаскивает только те, которые прошли проверку уверенности. Отдает кадры на распознавание символов
            принимает в себя фрейм, который был отправлен в нейронку """

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
                    left = int((cx - w/2) * x_factor)
                    top = int((cy - h/2) * y_factor)
                    width = int(w * x_factor)
                    height = int(h * y_factor)
                    box = np.array([left, top, width, height])
                    boxes.append(box)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, consts.CONFIDENCE_THRESHOLD, consts.NMS_THRESHOLD)

        frames = []

        for i in indices:
            box = boxes[i]
            width = box[2]
            height = box[3]

            if self.__plates_size_checker(width, height):
                left = box[0]
                top = box[1]
                # Draw bounding box.
                # cv2.rectangle(input_image, (left, top), (left + width, top + height), BLUE, 3*THICKNESS)
                frames.append(input_image[top:top + height, left:left + width])

                # Class label.
                # label = "{}:{:.2f}".format(classes[class_ids[i]], confidences[i])
                # Draw label.
                # draw_label(input_image, label, left, top)
        print(f"len of plates = {len(frames)}")

        return frames

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
                    left = int((cx - w/2) * x_factor)
                    top = int((cy - h/2) * y_factor)
                    width = int(w * x_factor)
                    height = int(h * y_factor)
                    box = np.array([left, top, width, height])
                    boxes.append(box)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, consts.CONFIDENCE_THRESHOLD, consts.NMS_THRESHOLD)
        
        detected_num = []
        pars_x_list = []
        pars_confid = []
        pars_class_id = []

        for i in indices:

            box = boxes[i]
            left = box[0]
            pars_x_list.append(left)

            pars_confid.append(confidences[i])
            pars_class_id.append(class_ids[i])

        detected_num = pasr_detection(pars_x_list,  pars_class_id, pars_confid)
        print(f"nums = {detected_num}")

        return detected_num

    def find_plates(self, frame, cam_name: str):

        # Сохраняем в класс кадр
        self.frame_1 = frame

        with self.lock_thread:
            # result = self.model_plates(self.frame_1)
            
            output_of_detections = self.plates_pre_process_frame(frame)

            frames_detected = self.__plates_post_process(frame, output_of_detections)
            # Находим все объекты на кадре

            numbers = list()

            for frames_out in frames_detected:
                
                numbers.append(self.recon_number(frames_out))

            if len(numbers) > 0:
                self.labels = ["".join(num) for num in numbers]

                # TODO реализовать на разные страны
                if len(self.labels[0]) > 7:
                    print(f"{cam_name}: RUS {self.labels}")
            # else:
            #     print("Нет данных")

    def recon_number(self, frame) -> list:
        """ Возвращает номер в виде списка элементов номера """
        result_of_numbers = list()

        try:

            # print(f"[{array.data[1]}:{array.data[3]}, {array.data[0]}:{array.data[2]}]")
            crop_img = frame
            # Меняем размер под размеры нейронной сети
            crop_img = cv2.resize(crop_img, (160, 160))

            # crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)

            cv2.imwrite(os.path.join(consts.TEMP_PATH, "test.jpg"), crop_img)
            # Делаем серого цвета вырезанный участок для распознания
            
            output_of_detection_numbers = self.nums_pre_process_frame(crop_img)
            # Отправляем на распознание
            result_of_numbers = self.__nums_post_process(crop_img, output_of_detection_numbers)

        except Exception as ex:
            print(f"EXCEPTION\tAiClass.recon_number()\t{ex}")

        return result_of_numbers

    def draw_plate(self):

        # with self.lock_thread:
        # Добавляем разметку на кадр
        # ret_frame = self.box_annotator.annotate(
        #     scene=self.frame_1,
        #     detections=self.detect_plates,
        #     labels=self.labels
        # )

        return self.frame_1

    def save_plate(self, file_name, array: []):

        # today = datetime.datetime.today()
        # for_name = str(today.strftime("%Y%m%d%H%M%S%f"))
        #
        # file_name = f'{for_name}.jpg'

        try:
            if array:
                self.frame_1 = self.frame_1[int(array.data[1]):int(array.data[3]),
                                            int(array.data[0]):int(array.data[2])]

            cv2.imwrite(os.path.join(consts.TEMP_PATH, file_name), self.frame_1)

        except Exception as ex:
            print(f"EXCEPTION\tAiClass.save_plate()\tИсключение - {ex}")
