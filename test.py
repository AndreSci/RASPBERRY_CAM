import cv2
import argparse
import onnx

import yolov5
import supervision as sv

CLASS_ID = ['_', 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'E', 'H', 'K', 'M', 'P', 'T', 'X', 'Y']
CONF_LVL = 0.7


# model_recon = yolov5.load("./content/Nums/last.pt")
model_recon = yolov5.load("./content/Nums/last.onnx")


def pasr_detection(xyxy: list, id_char: list, confidence: list):

    global CLASS_ID

    number = list()

    for case in xyxy:

        number.append(case[0])

    zip_res = zip(number, id_char, confidence)
    zip_list = list(zip_res)

    zip_list.sort()

    print(zip_list)
    number_list = list()

    for _, ind, conf in zip_list:
        if conf > CONF_LVL:
            number_list.append(CLASS_ID[ind])

    print(number_list)

    return zip_list


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv8 live")
    parser.add_argument(
        "--webcam-resolution",
        default=[640, 384],
        nargs=2,
        type=int
    )
    args = parser.parse_args()
    return args


def recon_number(frame, array):

    try:

        print(f"[{array.data[1]}:{array.data[3]}, {array.data[0]}:{array.data[2]}]")
        crop_img = frame[int(array.data[1]):int(array.data[3]), int(array.data[0]):int(array.data[2])]

        crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)

        crop_img = cv2.resize(crop_img, (160, 160))
        # ret_jpg, frame_jpg = cv2.imencode('.jpg', crop_img)
        # crop_img = cv2.flip(crop_img, 1)
        result = model_recon(crop_img, (160, 160))
        # cv2.imshow("yolov5", crop_img)

        res = sv.Detections.from_yolov5(result)

        print(res)

        pasr_detection(res.xyxy, res.class_id, res.confidence)

    except Exception as ex:
        print(f"Исключение: {ex}")


def main():
    args = parse_arguments()
    frame_width, frame_height = args.webcam_resolution

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    # model = YOLO("yolov8n.pt")
    model = yolov5.load("./content/Plates/best.pt")
    # model = YOLO("./content/Plates/best.pt")

    box_annotator = sv.BoxAnnotator(
        thickness=2,
        text_thickness=2,
        text_scale=1
    )
    #
    # zone_polygon = (ZONE_POLYGON * np.array(args.webcam_resolution)).astype(int)
    # zone = sv.PolygonZone(polygon=zone_polygon, frame_resolution_wh=tuple(args.webcam_resolution))
    # zone_annotator = sv.PolygonZoneAnnotator(
    #     zone=zone,
    #     color=sv.Color.green(),
    #     thickness=2,
    #     text_thickness=4,
    #     text_scale=2
    # )
    index = 9

    detections = None
    labels = None

    while True:
        # Получаем ret = статус и frame = кадр
        ret, frame = cap.read()
        index += 1
        # model = разметка нейронной схемы
        # result = model(frame, agnostic_nms=True)[0]
        if ret:
            # frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

            if index == 10:
                index = 0
            result = model(frame)
            # detections = sv.Detections.from_yolov8(result)
            detections = sv.Detections.from_yolov5(result)

            for xyxy, _, _, _, _ in detections:
                recon_number(frame, xyxy)

            # print(detections)
            labels = [f"CarNumber" for _, _, _, _, _ in detections]
            # labels = [f"{model.model.named_modules()} {confidence:0.2f}" for _, confidence, class_id, _ in detections]

            # метод дорисовывает поля и вероятность
            frame = box_annotator.annotate(
                scene=frame,
                detections=detections,
                labels=labels
            )

                # поиск зон в кадре
                # zone.trigger(detections=detections)
                # frame = zone_annotator.annotate(scene=frame)

            #cv2.imshow("yolov5", frame)


        if (cv2.waitKey(30) == 27):
            break


def main2():

    box_annotator = sv.BoxAnnotator(
        thickness=0,
        text_thickness=1,
        text_scale=1
    )


    frame = cv2.imread("./test_number.png")

    crop_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    crop_img = cv2.resize(crop_img, (224, 224))
    # ret_jpg, frame_jpg = cv2.imencode('.jpg', crop_img)
    # crop_img = cv2.flip(crop_img, 1)
    result = model_recon(crop_img, (160, 160))
    # cv2.imshow("yolov5", crop_img)

    res = sv.Detections.from_yolov5(result)

    print(res)
    pasr_detection(res.xyxy, res.class_id, res.confidence)
    number = list()
    for it in res.class_id:
        number.append(CLASS_ID[it])

    labels = [1,2,3,4,5,6,7,8,9,10,11,12,13]

    frame = box_annotator.annotate(
        scene=crop_img,
        detections=res,
        labels=labels
    )
    ret_jpg, frame_jpg = cv2.imencode('.jpg', frame)
    # with open('./test.jpg', 'w') as file:
    #     file.write(frame_jpg)
    cv2.imwrite('./test_im.jpg', frame)


def main3():
    from misc.ai import AiClass

    ai_class = AiClass()
    #
    # args = parse_arguments()
    # frame_width, frame_height = args.webcam_resolution

    capture = cv2.VideoCapture('test_vid.mp4')
    # capture.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    # capture.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    index = 5

    while True:

        if not capture.isOpened():
            break

        ret, frame = capture.read()  # читать всегда кадр

        if ret and index == 5:
            index = 0
            ai_class.find_plate(frame)

        cv2.imshow("yolov5", frame)
        index += 1

        if (cv2.waitKey(30) == 27):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main3()
