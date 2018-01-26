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
import time
   
env_vars = [
    ("SDL_FBDEV", "/dev/fb1"),
    ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
    ("SDL_MOUSEDRV", "TSLIB"),
]
#0.02, 0.02 barely any detectable response
#0.5, 0.02 some response, no damping
#0.5, 0.2 nearly enough damping
#0.5, 0.3 either over or under damped!
#0.5, 0.25 too much hdamping
TURN_P = 0.4
TURN_D = 0.2

for var_name, val in env_vars:
    os.environ[var_name] = val
screen_width = 320
screen_centre = screen_width / 2
screen_height = 240

camera = picamera.PiCamera()
camera.resolution = (screen_width, screen_height)
camera.framerate = 30
camera.iso = 800
camera.shutter_speed = 12000
pygame.init()
screen = pygame.display.set_mode([240, 320])
video = picamera.array.PiRGBArray(camera)
drive = Drivetrain(timeout=120)

#create small cust dictionary
small_dict = aruco.Dictionary_create(6, 3)
print("setup complete, looking")
last_t_error = 0
speed = 0
MIN_SPEED = 0
STRAIGHT_SPEED = 0.15
STEERING_OFFSET = 0.0  #more positive make it turn left
CROP_WIDTH = 320
i = 0
TIMEOUT = 30.0
START_TIME = time.clock()
END_TIME = START_TIME + TIMEOUT
found = False
turn_number = 0
TURN_TARGET = 10
TURN_WIDTH = 60
NINTY_TURN = 0.4 #0.4 (0.1, 0.1) works 10/10. 0.45(0.1,0.1) works 50%
MAX_SPEED = 0
SETTLE_TIME = 0.1
TURN_TIME = 0.1
MARKER1 = 3
MARKER2 = 5
target_id = MARKER1
MAX_TURN_SPEED = 0.35
loop_start_time=0

def turn_right():
    drive.move(NINTY_TURN, 0)
    time.sleep(TURN_TIME)
    drive.move(0,0)
    time.sleep(SETTLE_TIME)

def turn_left():
    drive.move(-NINTY_TURN, 0)
    time.sleep(TURN_TIME)
    drive.move(0,0)
    time.sleep(SETTLE_TIME)

try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        if time.clock() > END_TIME or turn_number > TURN_TARGET:
           raise KeyboardInterrupt
        frame = (frameBuf.array)
        video.truncate(0)
        frame = frame[30:190, (screen_centre - CROP_WIDTH/2):(screen_centre + CROP_WIDTH/2)]
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
            if ids[0][0] == target_id:
                found = True
                #if found, comptue the centre and move the cursor there
                #print(corners)
                found_x = sum([arr[0] for arr in corners[0][0]])  / 4
                found_y = sum([arr[1] for arr in corners[0][0]])  / 4
                width = abs(corners[0][0][0][0]-corners[0][0][1][0]+corners[0][0][3][0]-corners[0][0][2][0])/2
                print ('marker width %s' % width)
                if width > TURN_WIDTH:
                    #marker approached, start looking for new target marker
                    target_id = MARKER1 + MARKER2 - target_id
                    turn_number += 1
                    print ('Close to marker making turn %s' % turn_number)
                pygame.mouse.set_pos(int(found_y), int(found_x))
                t_error = (CROP_WIDTH/2 - found_x) / (CROP_WIDTH / 2)
                turn = STEERING_OFFSET + TURN_P * t_error
                if last_t_error is not 0:
                    #if there was a real error last time then do some damping
                    turn -= TURN_D *(last_t_error - t_error)
                turn = min(max(turn,-MAX_TURN_SPEED),MAX_TURN_SPEED)
                drive.move (turn, STRAIGHT_SPEED)
                last_t_error = t_error
                #print(camera.exposure_speed)
                print time.clock()-loop_start_time
                loop_start_time = time.clock()
            else:
                if target_id == MARKER1:
                    turn_right()
                else:
                    turn_left()
                found = False
                last_t_error = 0 
        else:
            #if marker was found, then probably best to stop and look
            if found:
                drive.move(0,0)
            else:
            #otherwise, go looking for the marker
                if target_id == MARKER1:
                    turn_right()
                else:
                    turn_left()
            found = False
            last_t_error = 0   
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(cv2.flip(frame,1))
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
        if found:
         img_name = str(i) + "Fimg.jpg"
        else:
         img_name = str(i) + "NFimg.jpg"
        #filesave for debugging: 
        #cv2.imwrite(img_name, gray)
        i += 1
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    drive.move(0,0)
    pygame.quit()
    cv2.destroyAllWindows()
