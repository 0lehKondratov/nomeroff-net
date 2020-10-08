import os
import time
import sys
import glob
import cv2
import numpy as np
from NomeroffNet.mcm.mcm import get_mode

from detectron2.engine import DefaultPredictor
from detectron2.engine import launch
from detectron2.engine import default_argument_parser
from detectron2.engine import default_setup 
from detectron2.config import CfgNode
from detectron2.data.datasets import register_coco_instances

def thresh_callback(src_gray, threshold=256/2):
    src_gray = cv2.blur(src_gray, (3,3))
    # Detect edges using Canny
    canny_output = cv2.Canny(src_gray, threshold, threshold * 2)
    # Find contours
    contours, _ = cv2.findContours(canny_output, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    drawing = np.zeros((canny_output.shape[0], canny_output.shape[1], 3), dtype=np.uint8)
    # Find the convex hull object for each contour
    for i in range(len(contours)):
        hull = cv2.convexHull(contours[i])
        cv2.fillConvexPoly(drawing, hull, (255, 255, 255))
    return drawing

class Detector:
    def __init__(self,
                 name        = "numberplate_train",
                 json_file = "./datasets/numberplate/train/coco_numberplate.json",
                 image_root  = "./datasets/numberplate/train",
                 name_val        = "numberplate_val",
                 json_file_val   = "./datasets/numberplate/val/coco_numberplate.json",
                 image_root_val  = "./datasets/numberplate/val"
                ):
        # registr own dataset
        try:
            register_coco_instances(name, {}, json_file, image_root)
            register_coco_instances(name_val, {}, json_file_val, image_root_val)
        except Exception as e:
            # TODO: show warning
            pass

    @classmethod
    def get_classname(cls):
        return cls.__name__

    def loadModel(self, nomeroffnet_path = "../",
                  subdir="./NomeroffNet/configs/centermask2/numberplates/",
                  config_file='centermask_numberplate_V_39_eSE_FPN_ms_3x.yaml'):
        """
        Create configs and perform basic setups.
        TODO: create folder config/centermask2/ and put all architecture them
        """
        centermask2_path= os.path.join(nomeroffnet_path, "centermask2")
        sys.path.append(centermask2_path)
        from centermask.config import get_cfg

        if get_mode() == "cpu":
            config_file = f"cpu_{config_file}"
        config_file = os.path.join(nomeroffnet_path, subdir, config_file)
        cfg = get_cfg()
        cfg.merge_from_file(config_file)
        cfg.freeze()
        self.predictor = DefaultPredictor(cfg)

    def detect_mask(self, images, verbose = 0, convex_hull=1):
        """
        TODO: multi gpu instances runtime
        """
        outputs_cpu = []
        for im in images:
            outputs = self.predictor(im)
            output_cpu = outputs["instances"].to("cpu")
            masks = np.array(output_cpu.get_fields()["pred_masks"])

            if convex_hull:
                masks = [thresh_callback((mask*255).astype(np.uint8)) for mask in masks]
            else:
                masks = [cv2.cvtColor((mask*255).astype(np.uint8), cv2.COLOR_GRAY2RGB) for mask in masks]

            #for mask in masks:
            #    print("222")
            #    print(mask.shape)
            # if mask and np.all((arr == 0))
            if len(masks):
                outputs_cpu.append(masks)
        return outputs_cpu