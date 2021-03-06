import sys
import os
sys.path.append('/usr/local/lib/python2.7/site-packages')
import cv2
import cv2.aruco as aruco
import pygame
import numpy as np
from pygame.locals import*
import picamera
import picamera.array
import math
CAMERA_MATRIX = np.array([[196.00378048362913, 0.0, 158.09985439215194], [0.0, 196.41940209255708, 123.28529641686711], [0.0, 0.0, 1.0]])
DIST_COEFFS = np.array([[-0.11909172334947736, -0.21275527201365405, -0.007049376606519501, -0.006678295495295815, 0.15384307954113818]])
MARKER_LENGTH = 0.08 #metres


def marker_angle(corners):
    ''' takes just the x &y cordinates fo the corners of the marker and returns the angle in degrees'''
    rvecs, tvecs, _objPoints = aruco.estimatePoseSingleMarkers(corners, MARKER_LENGTH, CAMERA_MATRIX, DIST_COEFFS)
    a1 = math.degrees(rvecs[0][0][0])
    a2 = math.degrees(rvecs[0][0][1])
    a3 = math.degrees(rvecs[0][0][2])
    return math.degrees(rvecs[0][0][1])

env_vars = [
    ("SDL_FBDEV", "/dev/fb1"),
    ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
    ("SDL_MOUSEDRV", "TSLIB"),
]
for var_name, val in env_vars:
    os.environ[var_name] = val
screen_width = 240
screen_height = 320

camera = picamera.PiCamera()
camera.resolution = (screen_width, screen_height)
pygame.init()
screen = pygame.display.set_mode([screen_width, screen_height])
video = picamera.array.PiRGBArray(camera)

#create small cust dictionary
small_dict = aruco.Dictionary_create(6, 3)
print("setup complete, looking")

try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        frame = np.rot90(frameBuf.array)        
        video.truncate(0)
        
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        parameters =  aruco.DetectorParameters_create()
                                
        #print(parameters)
        '''    detectMarkers(...)
            detectMarkers(image, dictionary[, corners[, ids[, parameters[, rejectedI
            mgPoints]]]]) -> corners, ids, rejectedImgPoints
        '''
        #lists of ids and the corners beloning to each id
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, small_dict, parameters=parameters)
        if ids != None:
            #if found, comptue the centre and move the cursor there
            #print(ids[0][0])
            print marker_angle(corners)
            found_x = sum([arr[0] for arr in corners[0][0]])  / 4
            found_y = sum([arr[1] for arr in corners[0][0]])  / 4
            pygame.mouse.set_pos(int(found_y), int(found_x))
            
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(frame)
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
                                                                         
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    pygame.quit()
    cv2.destroyAllWindows()
