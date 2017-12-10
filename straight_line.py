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
from drivetrain import Drivetrain  

   
env_vars = [
    ("SDL_FBDEV", "/dev/fb1"),
    ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
    ("SDL_MOUSEDRV", "TSLIB"),
]
TURN_P = 0.4
TURN_D = 1

for var_name, val in env_vars:
    os.environ[var_name] = val
screen_width = 480
screen_centre = screen_width / 2
screen_height = 640

camera = picamera.PiCamera()
camera.resolution = (screen_width, screen_height)
pygame.init()
screen = pygame.display.set_mode([240, 320])
video = picamera.array.PiRGBArray(camera)
drive = Drivetrain(timeout=120)

#create small cust dictionary
small_dict = aruco.Dictionary_create(6, 3)
print("setup complete, looking")
last_t_error = 0
speed = 0
MIN_SPEED = 0.3
MAX_SPEED = 1
STEERING_OFFSET = 0.0  #more positive make it turn left
STRAIGHT_TOLERANCE = 0.2
ACC_RATE = 0.2

try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        frame = np.rot90(frameBuf.array)        
        video.truncate(0)
        frame = frame[50:400, 220:380]
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
            #print(corners)
            found_y = sum([arr[0] for arr in corners[0][0]])  / 4
            found_x = sum([arr[1] for arr in corners[0][0]])  / 4
            pygame.mouse.set_pos(int(found_x), int(found_y))
            t_error = (screen_centre - found_x) / screen_centre
            turn = STEERING_OFFSET - TURN_P * t_error
            if last_t_error is not 0:
                #if there was a real error last time then do some damping
                turn += TURN_D *(last_t_error - t_error)
            if abs(t_error) < STRAIGHT_TOLERANCE and abs(last_t_error) < STRAIGHT_TOLERANCE:
                #if we're going straight, floor it
                speed = min(MAX_SPEED, speed + ACC_RATE)
            else:
                speed = max(speed - ACC_RATE, MIN_SPEED)
            drive.move (turn, speed)
            last_t_error = t_error
            print(t_error)
        else:
            speed = max(0, speed - ACC_RATE)
            drive.move(STEERING_OFFSET, speed)
            last_t_error = 0 
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
