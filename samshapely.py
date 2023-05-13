from shapely.geometry import Polygon, Point
from PIL import Image
from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
import pandas as pd

# Function to select only the segmentations detected by resb.ai
def FilterSegmentations(rb_detections, SAM_detections):
    # read the pickle
    rb_detections = pd.read_pickle(rb_detections)
    # the RB detections contains this information per segmentation:
    #{
    #     "image"                 : image_info,
    #     "annotations"           : [annotation],
    # }

    # image_info {
    #     "image_id"              : int,              # Image id
    #     "width"                 : int,              # Image width
    #     "height"                : int,              # Image height
    #     "file_name"             : str,              # Image filename
    # }

    # annotation {
    #     "id"                    : int,              # Annotation id
    #     "segmentation"          : dict,             # Mask saved in COCO RLE format.
    #     "bbox"                  : [x, y, w, h],     # The box around the mask, in XYWH format
    #     "area"                  : int,              # The area in pixels of the mask
    #     "predicted_iou"         : float,            # The model's own prediction of the mask's quality
    #     "stability_score"       : float,            # A measure of the mask's quality
    #     "crop_box"              : [x, y, w, h],     # The crop of the image used to generate the mask, in XYWH format
    #     "point_coords"          : [[x, y]],         # The point coordinates input to the model to generate the mask
    # }
    
    # SAM_detections contains this information per segmentation:
    for index, row in SAM_detections.iterrows():
        # Get the mask
        mask = row['segmentation']

        for label in rb_detections:
            #{label: [x, y]}
            #get x and y
            x = rb_detections[label][0]
            y = rb_detections[label][1]
            

    return rb_detections
        