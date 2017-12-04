
#!/usr/bin/env python
# coding: Latin

# Load library functions we want
import time
import os
import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')

# import ThunderBorg
import threading
import pygame
from pygame.locals import*
import picamera
import picamera.array
import cv2
import numpy
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
colour = 'blue'

# camera settings
imageWidth = 320  # Camera image width
imageHeight = 240  # Camera image height
SCREEN_SIZE = imageHeight, imageWidth
frameRate = 3  # Camera image capture frame rate

# Auto drive settings
autoMaxPower = 0.5  # Maximum output in automatic mode
autoMinPower = 0.1  # Minimum output in automatic mode
autoMinArea = 10  # Smallest target to move towards
autoMaxArea = 3000  # Largest target to move towards
autoFullSpeedArea = 50  # Target size at which we use the maximum allowed output

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
        # View the original image seen by the camera.
        if debug:
            frame = pygame.surfarray.make_surface(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            screen.fill([0, 0, 0])
            timenow = time.clock()
            timestep = timenow - self.oldtime
            font = pygame.font.Font(None, 24)
            label = font.render(str(timestep), 1, (250,250,250))
            screen.blit(frame, (0, 0))
            screen.blit(label, (10,10))
            pygame.display.update()
            self.oldtime = timenow
 
        # Blur the image
        image = cv2.medianBlur(image, 5)
        #if debug:
        #    cv2.imshow('blur', image)
        #    cv2.waitKey(0)
 
        # Convert the image from 'BGR' to HSV colour space
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        #if debug:
        #    cv2.imshow('cvtColour', image)
        #    cv2.waitKey(0)

        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        # method will extract the colour we are interested in (between 0 and 180)
        # In testing, the Hue value for red is between 95 and 125
        # Green is between 50 and 75
        # Blue is between 20 and 35
        # Yellow is... to be found!
        if colour == "red":
            imrange = cv2.inRange(image, numpy.array((95, 127, 64)), numpy.array((125, 255, 255)))
        elif colour == "green":
            imrange = cv2.inRange(image, numpy.array((50, 127, 64)), numpy.array((75, 255, 255)))
        elif colour == 'blue':
            imrange = cv2.inRange(image, numpy.array((20, 64, 64)), numpy.array((35, 255, 255)))
 
        # I used the following code to find the approximate 'hue' of the ball in
        # front of the camera
        # for crange in range(0,170,10):
        # imrange = cv2.inRange(image, numpy.array((crange, 64, 64)), numpy.array((crange+10, 255, 255)))
        # print(crange)
        # cv2.imshow('range',imrange)
        # cv2.waitKey(0)
 
        # View the filtered image found by 'imrange'
        #if debug:
        #    cv2.imshow('imrange', imrange)
        #    cv2.waitKey(0)
 
        # Find the contours
        contourimage, contours, hierarchy = cv2.findContours(imrange, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        #if debug:
        #    cv2.imshow('contour', contourimage)
        #    cv2.waitKey(0)

        # Go through each contour
        foundArea = -1
        foundX = -1
        foundY = -1
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + (w / 2)
            cy = y + (h / 2)
            area = w * h
            if foundArea < area:
                foundArea = area
                foundX = cx
                foundY = cy
        if foundArea > 0:
            ball = [foundX, foundY, foundArea]
        else:
            ball = None
        pygame.mouse.set_pos(foundY, foundX)
        # Set drives or report ball status
        self.SetSpeedFromBall(ball)

    # Set the motor speed from the ball position
    def SetSpeedFromBall(self, ball):
        forward = 0.0
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area < autoMinArea:
                drive.move(0, 0)
                print('Too small / far')
                print('%.2f, %.2f' % (forward, turn))
            elif area > autoMaxArea:
                drive.move(0, -0.15)
                print('Close enough, backing off')
                print('%.2f, %.2f' % (forward, turn))
            else:
                if area < autoFullSpeedArea:
                    forward = 1.0
                else:
                    forward = 1.0 / (area / autoFullSpeedArea)
                forward *= autoMaxPower - autoMinPower
                forward += autoMinPower
                turn = (imageCentreX - x) / imageCentreX / 5
                drive.move(turn, forward)
                print('%.2f, %.2f' % (forward, turn))
        else:
            # no ball, turn right
            drive.move(0, 0)
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
camera.resolution = (imageWidth, imageHeight)
camera.framerate = frameRate
imageCentreX = imageWidth / 2.0
imageCentreY = imageHeight / 2.0

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
    
#why's this net except here?
except:
    ## Unexpected error, shut down!
    e = sys.exc_info()[0]
    print
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
##TB.MotorsOff()
##TB.SetLedShowBattery(False)
##TB.SetLeds(0,0,0)
print('Program terminated.')
