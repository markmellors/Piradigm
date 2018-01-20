
# !/usr/bin/env python
# coding: Latin-1

from approxeng.input.selectbinder import ControllerResource
import math
import time
import logging
from drivetrain import Drivetrain

logger = logging.getLogger('piradigm.' + __name__)


class RC():
    def __init__(self, timeout=120, joystick=ControllerResource()):
        time.sleep(0.01)
        logger.info("initialising RC")
        self.timeout = timeout
        self.start_time = time.clock()
        self.exponential = 2
        self.name = "RC"
        self.killed = False
        self.drive = Drivetrain(timeout=self.timeout)
        self.joystick=joystick

    def run(self):
        logger.info("running RC challenge")
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
                logger.info('Connection to joystick lost')
            except IOError:
                # No joystick found, wait for a bit before trying again
                logger.info('Unable to find any joysticks')
                time.sleep(1.0)

        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            logger.info("killed from keyboard")
        finally:
            logger.info("stopping")
            self.drive.stop()
            logger.info("bye")

    @property
    def should_die(self):
        # TODO this should be monitored by the calling thread using a
        # combination of Timer threads and is_alive()
        timed_out = time.clock() >= (self.start_time + self.timeout)
        return timed_out or self.killed

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def stop(self):
        logger.info("RC challenge stopping")
        self.killed = True

    def exp(self, demand, exp):
        # function takes a demand speed from -1 to 1 and converts it to a response value
        # with an exponential function. exponential is -inf to +inf, 0 is linear
        exp = 1/(1 + abs(exp)) if exp < 0 else exp + 1
        return math.copysign((abs(demand)**exp), demand)
