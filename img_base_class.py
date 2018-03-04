#!/usr/bin/env python
# coding: Latin

# this file contains all the common elements of a threaded image processing challenge
# Load library functions we want
import logging
import logging.config
import os
import time
import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')

import threading
import pygame
from pygame.locals import*
import sgc
from sgc.locals import *
import picamera
import picamera.array
import cv2
import cv2.aruco as aruco
import numpy
from fractions import Fraction
from base_challenge import BaseChallenge
CAMERA_MATRIX = numpy.array([[196.00378048362913, 0.0, 158.09985439215194], [0.0, 196.41940209255708, 123.28529641686711], [0.0, 0.0, 1.0]])
DIST_COEFFS = numpy.array([[-0.11909172334947736, -0.21275527201365405, -0.007049376606519501, -0.006678295495295815, 0.15384307954113818]])

logging.config.fileConfig('logging.ini')
logger = logging.getLogger('piradigm.' + __name__)
logger.debug('Libraries loaded')


# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self, camera=None, processor=None):
        super(ImageCapture, self).__init__()
        self.terminated = False
        self.camera = camera
        self.processor = processor
        self.start()

    def run(self):
        logger.debug('Start the stream using the video port')
        self.camera.capture_sequence(
            self.trigger_stream(),
            format='bgr',
            use_video_port=True
        )
        logger.debug('Terminating camera processing...')
        self.processor.terminated = True
        self.processor.join()
        logger.debug('Processing terminated.')
                        
    # Stream delegation loop
    def trigger_stream(self):
        while not self.terminated:
            if self.processor.event.is_set():
                time.sleep(0.01)
            else:
                yield self.processor.stream
                self.processor.event.set()


def marker_angle(corners, marker_length, marker=0):
    ''' takes just the x&y coordinates of the corners of the marker, the marker size and returns the roll angle in radians'''
    rvecs, tvecs, _objPoints = aruco.estimatePoseSingleMarkers(corners, marker_length, CAMERA_MATRIX, DIST_COEFFS)
    return rvecs[marker][0][1]

def marker_vector(corners):
    x_mid_bottom = (corners[0][0]+corners[1][0])/2
    y_mid_bottom = (corners[0][1]+corners[1][1])/2
    x_mid_top = (corners[2][0]-corners[3][0])/2
    y_mid_top = (corners[2][1]-corners[3][1])/2
    x_diff = x_mid_top - x_mid_bottom
    y_diff = y_mid_top - y_mid_bottom
    return x_diff, y_diff
    
