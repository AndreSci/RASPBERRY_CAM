import cv2
import threading
import os
import datetime

import yolov5
import supervision as sv

CLASS_ID = ['_', 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'E', 'H', 'K', 'M', 'P', 'T', 'X', 'Y']
CONF_LVL = 0.7

YOLOV5_PLATES = yolov5.load("./content/Plates/best.pt")
YOLOV5_NUMBERS = yolov5.load("./content/Nums/last.onnx")


def pasr_detection(xyxy: list, id_char: list, confidence: list):

    global CLASS_ID, CONF_LVL

    number = list()

    # Проходим по всем элементам номера
    for case in xyxy:
        number.append(case[0])

    # Объединяем для упорядочивания вывода номера
    zip_res = zip(number, id_char, confidence)
    zip_list = list(zip_res)

    # Сортируем от меньшего к большему (то же что от левого объекта к правому)
    zip_list.sort()
    number_list = list()

    # Формируем номер
    for _, ind, conf in zip_list:
        if conf > CONF_LVL:
            number_list.append(str(CLASS_ID[ind]))

    return number_list


class AiClass:
    def __init__(self):
        global YOLOV5_NUMBERS, YOLOV5_PLATES

        self.model_plates = YOLOV5_PLATES
        self.model_number = YOLOV5_NUMBERS

        self.lock_thread = threading.Lock()

        self.frame_1 = ''

        self.detect_plates = ''
        self.labels = list()

        # Определяем параметры разметки
        self.box_annotator = sv.BoxAnnotator(
            thickness=1,
            text_thickness=1,
            text_scale=1
        )

    def find_plate(self, file_name):

        # Сохраняем в класс кадр
        self.frame_1 = cv2.imread(f'./Images/{file_name}', 0)

        with self.lock_thread:
            start_time = datetime.datetime.now()

            result = self.model_plates(self.frame_1)

            end_time = datetime.datetime.now()
            delta_time = end_time - start_time

            # print(f"Время поиска номера: {delta_time.total_seconds()} ms.")
            # Находим все объекты на кадре
            self.detect_plates = sv.Detections.from_yolov5(result)

            if len(self.detect_plates.xyxy) == 1:
                self.save_plate(self.detect_plates.xyxy[0], file_name)

    def find_plates(self, frame, cam_name: str):

        # Сохраняем в класс кадр
        self.frame_1 = frame

        with self.lock_thread:
            result = self.model_plates(frame)

            # Находим все объекты на кадре
            self.detect_plates = sv.Detections.from_yolov5(result)

            numbers = list()

            for it in self.detect_plates.xyxy:
                numbers.append(self.recon_number(it, frame))

            if len(numbers) > 0:
                self.labels = ["".join(num) for num in numbers]

                # TODO реализовать на разные страны
                if len(self.labels[0]) > 7:
                    print(f"{cam_name}: RUS {self.labels}")
            # else:
            #     print("Нет данных")

    def recon_number(self, array, frame) -> list:
        """ Возвращает номер в виде списка элементов номера """
        ret_value = list()

        try:

            # print(f"[{array.data[1]}:{array.data[3]}, {array.data[0]}:{array.data[2]}]")
            crop_img = frame[int(array.data[1]):int(array.data[3]), int(array.data[0]):int(array.data[2])]

            # Делаем серого цвета вырезанный участок для распознания
            crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)

            # Меняем размер под размеры нейронной сети
            crop_img = cv2.resize(crop_img, (160, 160))
            # Отправляем на распознание
            result = self.model_number(crop_img, (160, 160))
            # Выгружаем данные
            res = sv.Detections.from_yolov5(result)

            # Отправляем на сортировку данных
            ret_value = pasr_detection(res.xyxy, res.class_id, res.confidence)

        except Exception as ex:
            print(f"EXCEPTION\tAiClass.recon_number()\t{ex}")

        return ret_value

    def draw_plate(self):

        with self.lock_thread:
            # Добавляем разметку на кадр
            ret_frame = self.box_annotator.annotate(
                scene=self.frame_1,
                detections=self.detect_plates,
                labels=self.labels
            )

        return ret_frame

    def save_plate(self, array, file_name):

        # today = datetime.datetime.today()
        # for_name = str(today.strftime("%Y%m%d%H%M%S%f"))
        #
        # file_name = f'{for_name}.jpg'

        try:

            crop_img = self.frame_1[int(array.data[1]):int(array.data[3]), int(array.data[0]):int(array.data[2])]

            cv2.imwrite(os.path.join("../temp/", file_name), crop_img)

        except Exception as ex:
            print(f"EXCEPTION\tAiClass.save_plate()\tИсключение - {ex}")
