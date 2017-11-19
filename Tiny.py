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
                                logging.info("joystick L/R: %s, %s" % (rx, ry))
                                steering_left, steering_right = self.steering(rx, ry)
                                motor_left, motor_right = self.get_motor_values(steering_left, steering_right)
                                logging.info("steering L/R: %s, %s" % (steering_left, steering_right))
                                logging.info("motor value L/R: %s, %s" % (motor_left, motor_right))
                                self.pz.setMotor(1, motor_right)
                                self.pz.setMotor(0, motor_left)

                        # Joystick disconnected...
                        logging.info('Connection to joystick lost')
                    except IOError:
                        # No joystick found, wait for a bit before trying again
                        logging.info('Unable to find any joysticks')
                        time.sleep(1.0)

            except KeyboardInterrupt:
                # CTRL+C exit, disable all drives
                logging.info("killed from keyboard")
            finally:
                logging.info("stopping")
                self.pz.stop()
                self.pz.cleanup()
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

    def get_motor_values(self, steering_left, steering_right):
        motor_left = int(steering_left * self.motor_max) * -1
        motor_right = int(steering_right * self.motor_max) * -1

        return (motor_left, motor_right)

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def stop(self):
        logging.info("RC challenge stopping")
        self.killed = True
