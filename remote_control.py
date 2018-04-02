
# !/usr/bin/env python
# coding: Latin-1

from approxeng.input.selectbinder import ControllerResource
import math
import time
import logging
import pygame
from pygame.locals import*
from base_challenge import BaseChallenge
from img_base_class import hsv2rgb
logger = logging.getLogger('piradigm.' + __name__)



class RC(BaseChallenge):
    def __init__(self, drive=None, timeout=120, screen=None, joystick=None):
        time.sleep(0.01)
        self.exponential = 2
        self.hue = 0
        self.saturation = 0
        self.value = 255
        super(RC, self).__init__(name='RC', drive=drive, timeout=timeout, logger=logger)
        if not joystick:
            logger.info("No joystick available for RC, stopping")
            self.stop()
        else:    
            self.joystick = joystick

    def joystick_handler(self, button):
        if button['r1']:
            self.drive.move(0,0)
            self.timeout = 0
            print "stopping"
        if button['l1']:
            self.drive.lights(on=False)
            print "Turned headlights off"
        if button['l2']:
            rgb_colour = hsv2rgb(self.hue, self.saturation, self.value)
            self.drive.lights(on=True, rgb=rgb_colour)
            print "Turned headlights on"
        if button['triangle']:
            self.saturation +=25
            if self.saturation>255: self.saturation = 255
            rgb_colour = hsv2rgb(self.hue, self.saturation, self.value)
            self.drive.lights(on=True, rgb=rgb_colour)
            print "Turned headlight saturation up"
        if button['square']:
            self.hue -=10
            if self.hue<0: self.hue += 180
            rgb_colour = hsv2rgb(self.hue, self.saturation, self.value)
            self.drive.lights(on=True, rgb=rgb_colour)
            print "Turned headlight hue down"
        if button['cross']:
            self.saturation -=25
            if self.saturation<0: self.saturation = 0
            rgb_colour = hsv2rgb(self.hue, self.saturation, self.value)
            self.drive.lights(on=True, rgb=rgb_colour)
            print "Turned headlight saturation down"
        if button['circle']:
            self.hue +=10
            if self.hue>180: self.hue -= 180
            rgb_colour = hsv2rgb(self.hue, self.saturation, self.value)
            self.drive.lights(on=True, rgb=rgb_colour)
            print "Turned headlight hue up"

    def run(self):
        self.logger.info("running %s challenge" % self.name)
        try:
            try:
                while self.joystick.connected and not self.should_die:
                    self.joystick_handler(self.joystick.check_presses())
                    rx, ry = self.joystick['rx', 'ry']
                    logger.debug("joystick L/R: %s, %s" % (rx, ry))
                    rx = self.exp(rx, self.exponential)
                    ry = self.exp(ry, self.exponential)
                    self.drive.move(rx, ry)
                    time.sleep(0.05)


                # Joystick disconnected...
                self.logger.info('Connection to joystick lost')
            except IOError:
                # No joystick found, wait for a bit before trying again
                logging.info('Unable to find any joysticks')
                time.sleep(0.1)


        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            self.logger.info("killed from keyboard")
        finally:
            self.logger.info("stopping")
            self.drive.stop()
            self.logger.info("bye")
            pygame.event.post(pygame.event.Event(USEREVENT+1,message="challenge finished"))

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def exp(self, demand, exp):
        # function takes a demand speed from -1 to 1 and converts it to a response value
        # with an exponential function. exponential is -inf to +inf, 0 is linear
        exp = 1/(1 + abs(exp)) if exp < 0 else exp + 1
        return math.copysign((abs(demand)**exp), demand)
