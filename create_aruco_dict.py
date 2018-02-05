import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')
import cv2
import numpy as np
import cv2.aruco as aruco
import dill

#small_dict = aruco.generateCustomDictionary(6, 3)
NUM_OF_MARKERS = 6
small_dict = aruco.Dictionary_create(NUM_OF_MARKERS, 3)
'''
    drawMarker(...)
        drawMarker(dictionary, id, sidePixels[, img[, borderBits]]) -> img
'''
print (small_dict.markerSize)
print(small_dict)
#data = {"mS": small_dict.markerSize, "mCB": small_dict.maxCorrectionBits, "bL": small_dict.bytesList}
#print data
dill.dump(small_dict,open("markers.dill", "wb"))

loaded_dict = dill.load(open('markers.dill', "rb"))
#print new_data
#loaded_dict = aruco.Dictionary_create(0, 3)
#loaded_dict.markerSize = new_data["mS"]
#loaded_dict.maxCorrectionBits = new_data["mCB"]
#loaded_dict.bytesList = new_data["bL"]

#loaded_dict = aruco.Dictionary()
print (loaded_dict)
print (loaded_dict.markerSize)
# second parameter is id number
# last parameter is total image size
for i in range(0, NUM_OF_MARKERS):
    img = aruco.drawMarker(loaded_dict, i, 700)
    img_name = "new_marker_" + str(i) + ".jpg"
    print (img_name)
    cv2.imwrite(img_name, img)
print "done"
