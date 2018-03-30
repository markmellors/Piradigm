
# !/usr/bin/env python
# coding: Latin-1

from approxeng.input.selectbinder import ControllerResource
import math
import time
import logging
from base_challenge import BaseChallenge

logger = logging.getLogger('piradigm.' + __name__)



class RC(BaseChallenge):
    def __init__(self, timeout=120, screen=None, joystick=None):
        time.sleep(0.01)
        self.exponential = 2
        super(RC, self).__init__(name='RC', timeout=timeout, logger=logger)
        if not joystick:
            logger.info("No joystick available for RC, stopping")
            self.stop()
        else:    
            self.joystick = joystick

    def run(self):
        self.logger.info("running %s challenge" % self.name)
        try:
            try:
                while self.joystick.connected and not self.should_die:
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

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def exp(self, demand, exp):
        # function takes a demand speed from -1 to 1 and converts it to a response value
        # with an exponential function. exponential is -inf to +inf, 0 is linear
        exp = 1/(1 + abs(exp)) if exp < 0 else exp + 1
        return math.copysign((abs(demand)**exp), demand)
