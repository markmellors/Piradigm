import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')
import cv2
import numpy as np
import cv2.aruco as aruco

#small_dict = aruco.generateCustomDictionary(6, 3)
small_dict = aruco.Dictionary_create(6, 3)
'''
    drawMarker(...)
        drawMarker(dictionary, id, sidePixels[, img[, borderBits]]) -> img
'''
             
print(small_dict)

# second parameter is id number
# last parameter is total image size
img = aruco.drawMarker(small_dict, 2, 700)
cv2.imwrite("marker_2.jpg", img)
              

#number= 10
#dimension=7;
#cv::aruco::Dictionary dictionary = cv::aruco::generateCustomDictionary(number, dimension);
#cv::Mat store=dictionary.bytesList;
#cv::FileStorage fs("dic_save.yml", cv::FileStorage::WRITE);
#fs << "MarkerSize" << dictionary.markerSize;
#fs << "MaxCorrectionBits" << dictionary.maxCorrectionBits;
#fs << "ByteList" << dictionary.bytesList;
#fs.release(
