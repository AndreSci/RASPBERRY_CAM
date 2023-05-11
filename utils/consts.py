import os 

CLASS_ID = ['_', 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'E', 'H', 'K', 'M', 'P', 'T', 'X', 'Y']
CONF_LVL = 0.7

PLATES_WIDTH_INPUT = 640
PLATES_HEIGHT_INPUT = 640

NUMS_WIDTH_INPUT = 160
NUMS_HEIGHT_INPUT = 160

SCORE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.45
CONFIDENCE_THRESHOLD = 0.45
CONST_MAX_HEIGHT = 35

NUMS_SCORE_THRESHOLD = 1.5260739e-05
NUMS_NMS_THRESHOLD = 1.5260739e-05
NUMS_CONFIDENCE_THRESHOLD = 1.5260739e-05
NUMS_CONST_MAX_HEIGHT = 35

PATH = os.getcwd()

PLATES_MODEL_PATH = os.path.join(PATH, "content", "Plates", "frameDetection640.onnx")
NUMS_MODEL_PATH = os.path.join(PATH, "content",  "Nums", "last.onnx")

IMAGES_PATH = os.path.join(PATH, "Images")
TEMP_PATH = os.path.join(PATH, "temp")



