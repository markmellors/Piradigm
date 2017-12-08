#!/usr/bin/env python
# coding: Latin

# Load library functions we want
import time
import os
import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')

import threading
import pygame
from pygame.locals import*
import picamera
import picamera.array
import cv2
import numpy
from fractions import Fraction
from drivetrain import Drivetrain
print('Libraries loaded')

# Global values
global running
global camera
global processor
global debug
global colour

running = True
debug = True
colour = 'green'
MIN_CONTOUR_AREA = 1

# camera settings
IMAGE_WIDTH = 320  # Camera image width
IMAGE_HEIGHT = 240  # Camera image height
SCREEN_SIZE = IMAGE_HEIGHT, IMAGE_WIDTH
frameRate = Fraction(5)  # Camera image capture frame rate

# Auto drive settings
AUTO_MAX_POWER = 0.5  # Maximum output in automatic mode
AUTO_MIN_POWER = 0.1  # Minimum output in automatic mode
AUTO_MIN_AREA = 10  # Smallest target to move towards
AUTO_MAX_AREA = 3000  # Largest target to move towards
AUTO_FULL_SPEED_AREA = 50  # Target size at which we use the maximum allowed output

env_vars = [
    ("SDL_FBDEV", "/dev/fb1"),
    ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
    ("SDL_MOUSEDRV", "TSLIB"),
]
for var_name, val in env_vars:
    os.environ[var_name] = val


# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        time.sleep(1)
        self.start()
        self.begin = 0
        self.oldtime = 0

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and do some processing on it
                    self.stream.seek(0)
                    self.ProcessImage(self.stream.array, colour, screen)
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

    # Image processing function
    def ProcessImage(self, image, colour, screen):
        # crop image to speed up processing and avoid false positives
        image = image[60:180, 0:320]
        # View the original image seen by the camera.
        if debug:
            frame = pygame.surfarray.make_surface(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            screen.fill([0, 0, 0])
            font = pygame.font.Font(None, 24)
            screen.blit(frame, (0, 0))
            timenow = time.clock()
            timestep = timenow - self.oldtime
            label = font.render(str(timestep), 1, (250,250,250))
            screen.blit(label, (10,10))
            pygame.display.update()
            self.oldtime = timenow

        # Blur the image
        image = cv2.medianBlur(image, 5)
        # Convert the image from 'BGR' to HSV colour space
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        # method will extract the colour we are interested in (between 0 and 180)
        colour_bounds = {
            'red': ((101, 65, 80), (125, 255, 200)),
            'green': ((46, 65, 80), (90, 255, 200)),
            'blue': ((1, 65, 80), (46, 255, 200)),
            'yellow': ((90, 66, 80), (101, 255, 200)),
        }
        default_colour_bounds = ((40, 0, 0), (180, 255, 255))
        hsv_lower, hsv_upper = colour_bounds.get(colour, default_colour_bounds)
        imrange = cv2.inRange(
            image,
            numpy.array(hsv_lower),
            numpy.array(hsv_upper)
        )

        # I used the following code to find the approximate 'hue' of the ball in
        # front of the camera
        # for crange in range(0,170,10):
        # imrange = cv2.inRange(image, numpy.array((crange, 64, 64)), numpy.array((crange+10, 255, 255)))
        # print(crange)
        # cv2.imshow('range',imrange)
        # cv2.waitKey(0)

        # Find the contours
        contourimage, contours, hierarchy = cv2.findContours(
            imrange, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )

        # Go through each contour
        found_area = -1
        found_x = -1
        found_y = -1
        biggest_contour = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + (w / 2)
            cy = y + (h / 2)
            area = w * h
            if found_area < area:
                found_area = area
                found_x = cx
                found_y = cy
                biggest_contour = contour
        if found_area > 0:
            ball = [found_x, found_y, found_area]
        else:
            ball = None
        pygame.mouse.set_pos(found_y, found_x)
        if biggest_contour is not None:
            contour_area = cv2.contourArea(biggest_contour)
            if contour_area > MIN_CONTOUR_AREA:
                font = pygame.font.Font(None, 24)
                label = font.render(str(contour_area), 1, (250,250,250))
                screen.blit(label, (10,30))
            # skate wheel at 100mm has area = 7000, from centre of course is 180, far corner is 5
        pygame.display.update()
        # Set drives or report ball status
        self.Set_speed_from_ball(ball)

    # Set the motor speed from the ball position
    def Set_speed_from_ball(self, ball):
        forward = 0.0
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area < AUTO_MIN_AREA:
               # drive.move(0, 0)
                print('Too small / far')
                print('%.2f, %.2f' % (forward, turn))
            elif area > AUTO_MAX_AREA:
                # drive.move(0, -0.15)
                print('Close enough, backing off')
                print('%.2f, %.2f' % (forward, turn))
            else:
                if area < AUTO_FULL_SPEED_AREA:
                    forward = 1.0
                else:
                    forward = 1.0 / (area / AUTO_FULL_SPEED_AREA)
                forward *= AUTO_MAX_POWER - AUTO_MIN_POWER
                forward += AUTO_MIN_POWER
                turn = (image_centre_x - x) / image_centre_x / 5
                # drive.move(turn, forward)
                print('%.2f, %.2f' % (forward, turn))
        else:
            # no ball, turn right
            # drive.move(0, 0)
            print('No ball')
            print('%.2f, %.2f' % (forward, turn))


# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        global camera
        global processor
        print('Start the stream using the video port')
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)
        print('Terminating camera processing...')
        processor.terminated = True
        processor.join()
        print('Processing terminated.')

    # Stream delegation loop
    def TriggerStream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()


# Startup sequence
print('Setup camera')
camera = picamera.PiCamera()
camera.resolution = (IMAGE_WIDTH, IMAGE_HEIGHT)
camera.framerate = frameRate
image_centre_x = IMAGE_WIDTH / 2.0
image_centre_y = IMAGE_HEIGHT / 2.0

print('setup pygame')
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.init()

print('Setup the stream processing thread')
processor = StreamProcessor(screen)

drive = Drivetrain(timeout=120)

print('Wait ...')
time.sleep(2)
captureThread = ImageCapture()

try:
    print('Press CTRL+C to quit')
    # Loop indefinitely until we are no longer running
    while running:
        # Wait for the interval period
        # You could have the code do other work in here
        time.sleep(1.0)
        # Disable all drives

except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
    print('\nUser shutdown')

except:
    e = sys.exc_info()[0]
    print(e)
    print('\nUnexpected error, shutting down!')

# Tell each thread to stop, and wait for them to end
running = False
captureThread.join()
processor.terminated = True
processor.join()
del camera
drive.move(0, 0)
drive.stop()
print('Program terminated.')
