import os
import sys
import json
import asyncio
import matplotlib.image as mpimg
from termcolor import colored
import warnings
warnings.filterwarnings('ignore')

# change this property
NOMEROFF_NET_DIR = os.path.abspath('../../')

# specify the path to Mask_RCNN if you placed it outside Nomeroff-net project
MASK_RCNN_DIR = os.path.join(NOMEROFF_NET_DIR, 'Mask_RCNN')

MASK_RCNN_LOG_DIR = os.path.join(NOMEROFF_NET_DIR, 'logs')
MASK_RCNN_MODEL_PATH = os.path.join(NOMEROFF_NET_DIR, "models/mask_rcnn_numberplate_0700.h5")
OPTIONS_MODEL_PATH =  os.path.join(NOMEROFF_NET_DIR, "models/numberplate_options_2019_03_05.h5")

# If you use gpu version tensorflow please change model to gpu version named like *-gpu.pb
mode =  "cpu" if  "NN_MODE" not in os.environ else os.environ["NN_MODE"] if os.environ["NN_MODE"]=="gpu" else "cpu"
OCR_NP_UKR_TEXT =  os.path.join(NOMEROFF_NET_DIR, "models/anpr_ocr_ua_12-{}.h5".format(mode))
OCR_NP_EU_TEXT =  os.path.join(NOMEROFF_NET_DIR, "models/anpr_ocr_eu_2-{}.h5".format(mode))
OCR_NP_RU_TEXT =  os.path.join(NOMEROFF_NET_DIR, "models/anpr_ocr_ru_3-{}.h5".format(mode))

sys.path.append(NOMEROFF_NET_DIR)

from NomeroffNet import  filters, RectDetector, TextDetector, OptionsDetector, Detector, textPostprocessingAsync

nnet = Detector(MASK_RCNN_DIR, MASK_RCNN_LOG_DIR)
nnet.loadModel(MASK_RCNN_MODEL_PATH)

rectDetector = RectDetector()

optionsDetector = OptionsDetector()
optionsDetector.load(OPTIONS_MODEL_PATH)

# Initialize text detector.
textDetector = TextDetector({
    "eu_ua_2004_2015": {
        "for_regions": ["eu_ua_2015", "eu_ua_2004"],
        "model_path": OCR_NP_UKR_TEXT
    },
    "eu": {
        "for_regions": ["eu", "eu_ua_1995"],
        "model_path": OCR_NP_EU_TEXT
    },
    "ru": {
        "for_regions": ["ru"],
        "model_path": OCR_NP_RU_TEXT
    }
})


import cv2
import numpy as np

async def test(dirName, fname, y, verbose=0, max_img_w = 1280):
    img_path = os.path.join(dirName, fname)
    if verbose==1:
        print(colored("__________ \t\t {} \t\t __________".format(img_path), "blue"))
    img = mpimg.imread(img_path)
    nGood = 0
    nBad = 0
    img_path = os.path.join(dirName, fname)
    if verbose:
        print(img_path)
    img = mpimg.imread(img_path)

    # corect size for better speed
    img_w = img.shape[1]
    img_h = img.shape[0]
    img_w_r = 1
    img_h_r = 1
    if img_w > max_img_w:
        resized_img = cv2.resize(img, (max_img_w, int(max_img_w/img_w*img_h)))
        img_w_r = img_w/max_img_w
        img_h_r = img_h/(max_img_w/img_w*img_h)
    else:
        resized_img = img

    NP = nnet.detect([resized_img])

    # Generate image mask.
    cv_img_masks = await filters.cv_img_mask_async(NP)

    # Detect points.
    arrPoints = await rectDetector.detectAsync(cv_img_masks, outboundHeightOffset=3-img_w_r)
    arrPoints[..., 1:2] = arrPoints[..., 1:2]*img_h_r
    arrPoints[..., 0:1] = arrPoints[..., 0:1]*img_w_r

    # cut zones
    zones = await rectDetector.get_cv_zonesBGR_async(img, arrPoints)
    toShowZones = rectDetector.get_cv_zonesRGB(img, arrPoints)

    # find standart
    regionIds, stateIds = optionsDetector.predict(zones)
    regionNames = optionsDetector.getRegionLabels(regionIds)
    if verbose:
        print(regionNames)

    # find text with postprocessing by standart
    textArr = textDetector.predict(zones, regionNames)
    textArr = await textPostprocessingAsync(textArr, regionNames)
    if verbose:
        print(textArr)

    for yText in y:
        if yText in textArr:
            print(colored("OK: TEXT:{} \t\t\t RESULTS:{} \n\t\t\t\t\t in PATH:{}".format(yText, textArr, img_path), 'green'))
            nGood += 1
        else:
            print(colored("NOT OK: TEXT:{} \t\t\t RESULTS:{} \n\t\t\t\t\t in PATH:{} ".format(yText, textArr, img_path), 'red'))
            nBad += 1
    return nGood, nBad


async def run():
    dirName = "../images/"
    testData = {
        "0.jpeg": ["AI5255EI"],
        "1.jpeg": ["HH7777CC"],
        "2.jpeg": ["AT1515CK"],
        "3.jpeg": ["BX0578CE"],
        "4.jpeg": ["AC4249CB"],
        "5.jpeg": ["BC3496HC"],
        "6.jpeg": ["BC3496HC"],
        "7.jpeg": ["AO1306CH"],
        "8.jpeg": ["AE1077CO"],
        "9.jpeg": ["AB3391AK"],
        "10.jpeg": ["BE7425CB"],
        "11.jpeg": ["BE7425CB"],
        "12.jpeg": ["AB0680EA"],
        "13.jpeg": ["AB0680EA"],
        "14.jpeg": ["BM1930BM"],
        "15.jpeg": ["AI1382HB"],
        "16.jpeg": ["AB7333BH"],
        "17.jpeg": ["AB7642CT"],
        "18.jpeg": ["AC4921CB"],
        "19.jpeg": ["BC9911BK"],
        "20.jpeg": ["BC7007AK"],
        "21.jpeg": ["AB5649CI"],
        "22.jpeg": ["AX2756EK"],
        "23.jpeg": ["AA7564MX"],
        "24.jpeg": ["AM5696CK"],
        "25.jpeg": ["AM5696CK"],
    }

    gGood = 0
    gBad = 0
    i = 0
    for fileName in testData.keys():
        nGood, nBad = await test(dirName, fileName, testData[fileName], verbose=0)
        gGood += nGood
        gBad += nBad
        i += 1
    total = gGood + gBad
    print("TOTAL GOOD: {}".format(gGood/total))
    print("TOTAL BED: {}".format(gBad/total))

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
result = loop.run_until_complete(run())

run()