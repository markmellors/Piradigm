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
TURN_P = 0.6
TURN_D = 0.3

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
STRAIGHT_SPEED = 0.5
STEERING_OFFSET = 0.0  #more positive make it turn left
CROP_WIDTH = 320
i = 0
TIMEOUT = 30.0
START_TIME = time.clock()
END_TIME = START_TIME + TIMEOUT
found = False
turn_number = 0
TURN_TARGET = 5
TURN_WIDTH = [30, 35, 35, 30, 35, 35]

NINTY_TURN = 0.8  #0.8 works if going slowly
MAX_SPEED = 0
SETTLE_TIME = 0.05
TURN_TIME = 0.04
MAX_TURN_SPEED = 0.25
loop_start_time=0
marker_to_track=0
BRAKING_FORCE = 0.1
BRAKE_TIME = 0.05

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

def brake():
    drive.move(0,-BRAKING_FORCE)
    time.sleep(BRAKE_TIME)
    drive.move(0,0)
    
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
            #print ("found marker %s" % ids)
            if len(ids)>1:
                print "found %d markers" % len(ids),
                marker_to_track = 0
                for marker_number in range(0, len(ids)):
                    if ids[marker_number] == turn_number:
                        marker_to_track = marker_number
                print (", marker I'm looking for, is number %d" % marker_to_track)
            else:
                marker_to_track = 0
            if ids[marker_to_track][0] == turn_number:
                m = marker_to_track
                found = True
                #print corners
                #if found, comptue the centre and move the cursor there
                found_y = sum([arr[0] for arr in corners[m][0]])  / 4
                found_x = sum([arr[1] for arr in corners[m][0]])  / 4
                width = abs(corners[m][0][0][0]-corners[m][0][1][0]+corners[m][0][3][0]-corners[m][0][2][0])/2
                print ('marker width %s' % width)
                if width > TURN_WIDTH[turn_number]:
                    turn_number += 1
                    print ('Close to marker making turn %s' % turn_number)
                    if turn_number is 5:
                        print('finished!')
                        drive.move(0,0)
                        END_TIME = time.clock()
                pygame.mouse.set_pos(int(found_x), int(CROP_WIDTH-found_y))
                #print int(found_y), int(found_x)
                t_error = (CROP_WIDTH/2 - found_y) / (CROP_WIDTH / 2)
                turn = STEERING_OFFSET + TURN_P * t_error
                if last_t_error is not 0:
                    #if there was a real error last time then do some damping
                    turn -= TURN_D *(last_t_error - t_error)
                turn = min(max(turn,-MAX_TURN_SPEED), MAX_TURN_SPEED)
                print turn
                #if we're rate limiting the turn, go slow
                if abs(turn) == MAX_TURN_SPEED:
                    drive.move (turn, STRAIGHT_SPEED/3)
                else:
                    drive.move (turn, STRAIGHT_SPEED)
                last_t_error = t_error
                #print(camera.exposure_speed)
            else:
                print ("looking for marker %d" % turn_number)
                if found:
                    drive.move(0,0)
                if turn_number <= 2:
                    if turn_number == 1:
                        brake()
                    turn_right()
                else:
                    if turn_number == 4:
                        brake()
                    turn_left()
                found = False
                last_t_error = 0 
        else:
            print ("looking for marker %d" % turn_number)
            #if marker was found, then probably best to stop and look
            if found:
                drive.move(0,0)
            else:
                #otherwise, go looking
                if turn_number <= 2:
                    if turn_number == 1:
                        brake()
                    turn_right()
                else:
                    if turn_number == 4:
                        brake()
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
        cv2.imwrite(img_name, gray)
        i += 1
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    drive.move(0,0)
    pygame.quit()
    cv2.destroyAllWindows()
