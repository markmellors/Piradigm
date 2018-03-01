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

def marker_angle(corners):
    ''' takes just the x &y cordinates fo the corners of the marker and returns the angle in degrees'''

    #shortened variable name for conciseness
    c = corners
    #0.01 added to avoid divide by zero errors. corner coordinates assuemd to be integers
    side_one_angle = math.atan((c[1][0] - c[0][0]) / (c[1][1] - c[0][1])+0.01)
    side_two_angle = math.atan((c[2][0] - c[1][0]) / (c[2][1] - c[1][1])+0.01)
    side_three_angle = math.atan((c[3][0] - c[2][0]) / (c[3][1] - c[2][1])+0.01)
    side_four_angle = math.atan((c[1][0] - c[3][0]) / (c[0][1] - c[3][1])+0.01)
    angle_radians = (side_one_angle + side_two_angle + side_three_angle + side_four_angle + 3.14) / 4
    angle_degrees = math.degrees(angle_radians)
    return angle_degrees

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
            print(ids[0][0])
            print(marker_angle(corners[0][0]))
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
