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
TURN_P = 0.4
TURN_D = 1

for var_name, val in env_vars:
    os.environ[var_name] = val
screen_width = 480
screen_centre = screen_width / 2
screen_height = 640

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
MAX_SPEED = 1
STEERING_OFFSET = 0.0  #more positive make it turn left
STRAIGHT_TOLERANCE = 0.2
ACC_RATE = 0.2
CROP_WIDTH = 360
i = 0
TIMEOUT = 4.0
START_TIME = time.clock()
END_TIME = START_TIME + TIMEOUT
found = False
turn_number = 0
TURN_WIDTH = 120
try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        if time.clock() > END_TIME:
           raise KeyboardInterrupt
        frame = np.rot90(frameBuf.array)        
        video.truncate(0)
        frame = frame[(screen_centre - CROP_WIDTH/2):(screen_centre + CROP_WIDTH/2), 220:380]
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
            found = True
            #if found, comptue the centre and move the cursor there
            #print(corners)
            found_y = sum([arr[0] for arr in corners[0][0]])  / 4
            found_x = sum([arr[1] for arr in corners[0][0]])  / 4
            width = abs(corners[0][0][1][0]-corners[0][0][2][0]+corners[0][0][4][0]-corners[0][0][3][0])/2
            if width > TURN_WIDTH:
                if turn_number is 0:
                    turn_number +=1
                    ninty_right()
                elif turn_number is 1:
                    turn_number +=1
                    s_right()
                elif turn_number is 2:
                    turn_number +=1
                    s_left()
                elif turn_number is 3:
                    turn_number +=1
                    ninty_left()
                else
                    print('finished!')
                    drive.move(0,0)
                    END_TIME = time.clock()
            pygame.mouse.set_pos(int(found_x), int(found_y))
            t_error = (CROP_WIDTH/2 - found_x) / (CROP_WIDTH / 2)
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
            print(camera.exposure_speed)
        else:
            found = False
            speed = max(0, speed - ACC_RATE)
            drive.move(STEERING_OFFSET, speed)
            last_t_error = 0 
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(frame)
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
        if found:
         img_name = str(i) + "Fimg.jpg"
        else:
         img_name = str(i) + "NFimg.jpg"
        cv2.imwrite(img_name, gray)
        i += 1
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    drive.move(0,0)
    pygame.quit()
    cv2.destroyAllWindows()
