import cv2
import numpy as np


def detect_object(image_path):
    # Загружаем обученную нейронную сеть из файла "best.pt"
    net = cv2.dnn.readNetFromONNX('./content/Plates/best.onnx')

    # Загружаем изображение
    image = cv2.imread(image_path)

    # Делаем серого цвета вырезанный участок для распознания
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Создаем blob изображения
    blob = cv2.dnn.blobFromImage(image, 1/255.0, (320, 320), swapRB=True, crop=False)

    # Подаем blob на вход нейронной сети и получаем ее выход
    net.setInput(blob)

    net.

if __name__ == '__main__':
    detect_object('test_img.jpg')
