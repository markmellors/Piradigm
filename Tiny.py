#!/usr/bin/env python
# coding: Latin-1

# Load library functions we want

from approxeng.input.selectbinder import ControllerResource
import piconzero
import math
import time
import logging

logging.basicConfig(
    filename='piradigm.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s'
)


class RC:
    def __init__(self):
        time.sleep(0.01)
        logging.info("initialising RC")
        self.timeOut = 10
        self.pz = piconzero
        self.pz.init()
        self.motor_max = 100
        self.name = "RC"
        self.killed = False

    def run(self):
        logging.info("running RC challenge")
        while True:
            try:
                startTime = time.clock()
                logging.info("start time: %s", startTime)
                while time.clock() < (startTime + self.timeOut) and not self.killed:
                    try:
                        with ControllerResource() as joystick:
                            logging.info('Found a joystick and connected')
                            while joystick.connected:
                                rx, ry = joystick['rx', 'ry']
                                power_left, power_right = self.steering(rx, ry)
                                self.pz.setMotor(1, power_right * self.motor_max)
                                self.pz.setMotor(0, power_left * self.motor_max)

                        # Joystick disconnected...
                        logging.info('Connection to joystick lost')
                    except IOError:
                        # No joystick found, wait for a bit before trying again
                        logging.info('Unable to find any joysticks')
                        time.sleep(1.0)

            except KeyboardInterrupt:
                # CTRL+C exit, disable all drives
                logging.info("stopping")
                # self.pz.stop()
                # self.pz.cleanup()
                logging.info("bye")

    def steering(self, x, y):
        """Steering algorithm taken from https://electronics.stackexchange.com/a/293108"""
        # convert to polar
        r = math.hypot(x, y)
        t = math.atan2(y, x)

        # rotate by 45 degrees
        t += math.pi / 4

        # back to cartesian
        left = r * math.cos(t)
        right = r * math.sin(t)

        # rescale the new coords
        left = left * math.sqrt(2)
        right = right * math.sqrt(2)

        # clamp to -1/+1
        left = max(-1, min(left, 1))
        right = max(-1, min(right, 1))

        return left, right

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def stop(self):
        logging.info("RC challenge stopping")
        self.killed = True
