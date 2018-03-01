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
    rect = cv2.minAreaRect(corners)
    #work out vector elements for each side
    dx1 = (c[1][0] - c[0][0])
    dy1 = (c[1][1] - c[0][1])
    dx2 = (c[2][0] - c[1][0])
    dy2 = (c[2][1] - c[1][1])
    dx3 = (c[3][0] - c[2][0])
    dy3 = (c[3][1] - c[2][1])
    dx4 = (c[1][0] - c[3][0])
    dy4 = (c[0][1] - c[3][1])
    #combine vectors for each side (rotating every other side by 90degrees) to make a single vector
    dx = dx1 - dx3 + dx1/abs(dx1)*abs(dy2 + dy4)
    dy = dy1 - dy3 + dy1/abs(dy1)*abs(dx2 + dx4)
    angle_radians = math.atan(dy/dx)
    angle_degrees = math.degrees(angle_radians)
    return rect[2]

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
            print marker_angle(corners[0][0])
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
