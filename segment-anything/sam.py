import ssl
import pickle
import matplotlib.pyplot as plt
import numpy as np
import os

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
import cv2

# if error run Update Shell Profile.command from python folder

def show_anns(anns):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    ax = plt.gca()
    ax.set_autoscale_on(False)

    img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
    img[:,:,3] = 0
    for ann in sorted_anns:
        m = ann['segmentation']
        color_mask = np.concatenate([np.random.random(3), [0.35]])
        img[m] = color_mask
    ax.imshow(img)
    
checkpoint = "sam_vit_b_01ec64.pth"
model_type = "vit_b"
img_path = "sample_image2.jpg"


if not os.path.exists(checkpoint):
  os.system('wget https://dl.fbaipublicfiles.com/segment_anything/'+checkpoint)

exit()

img = cv2.imread(img_path)

sam = sam_model_registry[model_type](checkpoint=checkpoint)
mask_generator = SamAutomaticMaskGenerator(sam,
																						points_per_side=32,
																						pred_iou_thresh=0.86,
																						stability_score_thresh=0.92,
																						crop_n_layers=1,
																						crop_n_points_downscale_factor=2,
																						min_mask_region_area=100,  # Requires open-cv to run post-processing
																				)


print('Generating mask...')
masks = mask_generator.generate(img)

with open('mask.pickle', 'wb') as handle:
    pickle.dump(masks, handle, protocol=-1)
#print(masks)

plt.figure(figsize=(2,2))
plt.imshow(img)
show_anns(masks)
plt.axis('off')

plt.savefig('mask.jpg',dpi=200)
#plt.show() 

