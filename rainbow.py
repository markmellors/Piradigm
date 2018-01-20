
#!/usr/bin/env python
# coding: Latin

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
import numpy
from fractions import Fraction
from base_challenge import BaseChallenge

logging.config.fileConfig('logging.ini')
logger = logging.getLogger('piradigm.' + __name__)

logger.debug('Libraries loaded')
# camera settings

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen=None, camera=None, drive=None, colour="any"):
        super(StreamProcessor, self).__init__()
        self.camera = camera
        image_width, image_height = self.camera.resolution
        self.image_centre_x = image_width / 2.0
        self.image_centre_y = image_height / 2.0
        self.drive = drive
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.MAX_AREA = 4000  # Largest target to move towards
        self.MIN_CONTOUR_AREA = 3
        self._colour = colour
        self.found = False
        self.retreated = False
        self.cycle = 0
        self.last_a_error = 0
        self.last_t_error = 0
        self.AREA_P = 0.0001
        self.AREA_D = 0.0002
        self.TURN_P = 0.5
        self.TURN_D = 0.2
        self.BACK_OFF_AREA = 1000
        self.BACK_OFF_SPEED = -0.25
        self.FAST_SEARCH_TURN = 0.6
        # Why the one second sleep?
        time.sleep(1)
        self.start()

    @property
    def colour(self):
        """Set the target colour property"""
        return self._colour

    @colour.setter
    def colour(self, colour):
        self._colour = colour

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and do some processing on it
                    self.stream.seek(0)
                    self.process_image(self.stream.array, self.screen)
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

    # Image processing function
    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        # crop image to speed up processing and avoid false positives
        image = image[80:180, 0:320]
        image = cv2.medianBlur(image, 5)
        # Convert the image from 'BGR' to HSV colour space
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        # method will extract the colour we are interested in (between 0 and 180)
        colour_bounds = {
            'red': ((105, 65, 80), (125, 255, 200)),
            'green': ((46, 65, 80), (90, 255, 200)),
            'blue': ((1, 65, 80), (46, 255, 200)),
            'yellow': ((90, 66, 80), (105, 255, 200)),
        }
        default_colour_bounds = ((40, 0, 0), (180, 255, 255))
        hsv_lower, hsv_upper = colour_bounds.get(
            self.colour, default_colour_bounds
        )
        imrange = cv2.inRange(
            image,
            numpy.array(hsv_lower),
            numpy.array(hsv_upper)
        )

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
            aspect_ratio = float(h)/w
            if found_area < area and aspect_ratio < 2 and aspect_ratio > 0.5:
                found_area = area
                found_x = cx
                found_y = cy
                biggest_contour = contour
        if found_area > self.MIN_CONTOUR_AREA:
            ball = [found_x, found_y, found_area]
        else:
            ball = None
        pygame.mouse.set_pos(found_y, found_x)
        if biggest_contour is not None:
            contour_area = cv2.contourArea(biggest_contour)
            if self.screen and contour_area > self.MIN_CONTOUR_AREA:
                font = pygame.font.Font(None, 24)
                label = font.render(str(contour_area), 1, (250, 250, 250))
                self.screen.blit(label, (10, 30))
                # skate wheel at 100mm has area = 7000,
                # from centre of course is 180, far corner is 5
                pygame.display.update()
        # Set drives or report ball status
        if not self.found:
            self.drive_toward_ball(ball)
        elif not self.retreated:
            self.drive_away_from_ball(ball)


    # TODO: Move this motor control logic out of the stream processor
    # as it is challenge logic, not stream processor logic
    # (the clue is that the streamprocessor needs a drivetrain)

    # Set the motor speed from the ball position
    def drive_toward_ball(self, ball):
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area > self.MAX_AREA:
                self.drive.move(0, 0)
                logger.info('Close enough, stopping')
            else:
                # follow 0.2, /2 good
                a_error = self.MAX_AREA - area
                forward = self.AREA_P * a_error
                t_error  = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error
                if self.last_t_error is not None:
                    #if there was a real error last time then do some damping
                    turn -= self.TURN_D *(self.last_t_error - t_error)
                    forward -= self.AREA_D * (self.last_a_error - a_error)
                self.drive.move(turn, forward)
                self.last_t_error = t_error
                self.last_a_error = a_error
                print('ball, %s', t_error)
        else:
            # no ball, turn right 0.25, 0.12 ok but a bit sluggish and can get stuck in corner 0.3, -0.12 too fast, 0.3, 0 very slow. 0.25, 0.15 good
            if self.cycle > 5:
                self.drive.move(self.FAST_SEARCH_TURN, 0)
                self.cycle = 0
            else:
                self.drive.move(0, 0)
                self.cycle += 1
            logger.info('No ball')
            # reset PID errors
            self.last_t_error = None

 # drive away from the ball, back to the middle
    def drive_away_from_ball(self, ball):
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area < self.BACK_OFF_AREA:
                self.drive.move(0, 0)
                self.retreated = True
                logger.info('far enough away, stopping')
            else:
                t_error = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error - self.TURN_D *(self.last_t_error - t_error)
                self.drive.move(turn, forward)
                self.last_t_error = t_error
        else:
            # ball lost, stop
            self.found = False
            self.drive.move(0, 0)
            logger.info('ball lost')


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


class Rainbow(BaseChallenge):
    """Rainbow challenge class"""

    def __init__(self, timeout=120, screen=None):
        self.image_width = 320  # Camera image width
        self.image_height = 240  # Camera image height
        self.frame_rate = Fraction(20)  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        super(Rainbow, self).__init__(name='Rainbow', timeout=timeout, logger=logger)

    def run(self):
        # Startup sequence
        pygame.mouse.set_visible(True)
        logger.info('Setup camera')
        self.camera = picamera.PiCamera()
        self.camera.resolution = (self.image_width, self.image_height)
        self.camera.framerate = self.frame_rate
        
        logger.info('Setup the stream processing thread')
        # TODO: Remove dependency on drivetrain from StreamProcessor
        self.processor = StreamProcessor(
            screen=self.screen,
            camera=self.camera,
            drive=self.drive
        )
        # To switch target colour" on the fly, use:
        # self.processor.colour = "blue"

        logger.info('Wait ...')
        time.sleep(2)
        logger.info('Setting up image capture thread')
        self.image_capture_thread = ImageCapture(
            camera=self.camera,
            processor=self.processor
        )

        try:
            while not self.should_die:
                time.sleep(0.1)
                # TODO: Tidy this
                if self.processor.retreated and self.processor.colour is not "green":
                    if self.processor.colour is "yellow": self.processor.colour = "green"
                    if self.processor.colour is "blue": self.processor.colour = "yellow"
                    if self.processor.colour is "red": self.processor.colour = "blue"
                    self.processor.found = False
                    self.processor.retreated = False

        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            self.logger.info("killed from keyboard")
        finally:
            # Tell each thread to stop, and wait for them to end
            self.logger.info("stopping threads")
            self.image_capture_thread.terminated = True
            self.image_capture_thread.join()
            self.processor.terminated = True
            self.processor.join()
            self.camera = None
            self.logger.info("stopping drive")
            self.drive.stop()
            pygame.mouse.set_visible(False)
            self.logger.info("bye")

