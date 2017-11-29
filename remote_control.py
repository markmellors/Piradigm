
#!/usr/bin/env python
# coding: Latin-1

from approxeng.input.selectbinder import ControllerResource
import piconzero
import math
import time
import logging
import random

logging.basicConfig(
    filename='piradigm.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s'
)

logger = logging.getLogger(__name__)


class RC():
    def __init__(self, timeout=120):
        time.sleep(0.01)
        logging.info("initialising RC")
        self.timeout = timeout
        self.start_time = None
        self.pz = piconzero
        self.pz.init()
        self.motor_max = 100
        self.slow_speed = 20
        self.deadband = 1
        self.boost_cycles = 1
        self.boost_dwell = 9
        self.exponential = 2
        self.name = "RC"
        self.killed = False

    def run(self):
        logging.info("running RC challenge")
        try:
            self.start_time = time.clock()
            logging.info("start time: %s", self.start_time)
            try:
                with ControllerResource() as joystick:
                    logging.info('Found a joystick and connected')
                    left_counter = 0
                    right_counter = 0
                    while joystick.connected and not self.should_die:
                        rx, ry = joystick['rx', 'ry']
                        logging.debug("joystick L/R: %s, %s" % (rx, ry))
                        rx = self.exp(rx , self.exponential)
                        ry = self.exp(ry , self.exponential)
                        steering_left, steering_right = self.steering(rx, ry)                     
                        motor_left, motor_right = self.get_motor_values(steering_left, steering_right)
                        left_counter, motor_left = self.dither(left_counter, motor_left)
                        right_counter, motor_right = self.dither(right_counter, motor_right)  
                        logging.debug("steering L/R: %s, %s" % (steering_left, steering_right))
                        logging.debug("motor value L/R: %s, %s" % (motor_left, motor_right))
                        logging.debug("counter: %s, %s" % (left_counter, right_counter))
                        self.pz.setMotor(1, motor_right)
                        self.pz.setMotor(0, motor_left)
                        time.sleep(0.05)

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

    @property
    def should_die(self):
        # TODO this should be monitored by the calling thread using a
        # combination of Timer threads and is_alive()
        timed_out = time.clock() >= (self.start_time + self.timeout)
        return timed_out or self.killed

    def steering(self, x, y):
        """Steering algorithm taken from
        https://electronics.stackexchange.com/a/293108"""
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

    def dither(self, counter, speed):
    #function takes a speed and occassionally adds a boost, helpful at very low speeds
    #counter is between 0 and (self.boot_cycles + self.boost_dwell) and is used to 
    #schedule boosts. speed si ebtween -1 and +1. modified speed and counter are returned
        if self.deadband < abs(speed) < self.slow_speed:
            speed = int(speed - math.copysign(1, speed))
            counter += 1
            if counter < self.boost_cycles:
                speed = speed + int(math.copysign(self.slow_speed, speed))
            elif counter > (self.boost_cycles + self.boost_dwell):
                counter = 0
        return (counter, speed)

    def exp(self, demand, exp):
    #function takes a demand speed from -1 to 1 and converts it to a response value
    # with an exponential function. exponential is -inf to +inf, 0 is linear
        exp = 1/(1 + abs(exp)) if exp < 0 else exp + 1
        return math.copysign((abs(demand)**exp), demand)
