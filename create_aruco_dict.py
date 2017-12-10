import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')
import cv2
import numpy as np
import cv2.aruco as aruco

#small_dict = aruco.generateCustomDictionary(6, 3)
NUM_OF_MARKERS = 6
small_dict = aruco.Dictionary_create(NUM_OF_MARKERS, 3)
'''
    drawMarker(...)
        drawMarker(dictionary, id, sidePixels[, img[, borderBits]]) -> img
'''
             
print(small_dict)

# second parameter is id number
# last parameter is total image size
for i in range(0, NUM_OF_MARKERS):
    img = aruco.drawMarker(small_dict, i, 700)
    img_name = "marker_" + str(i) + ".jpg"
    print (img_name)
    cv2.imwrite(img_name, img)
              

