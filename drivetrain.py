# !/usr/bin/env python
# coding: Latin-1

import piconzero
import math
import time
import logging

logging.basicConfig(
    filename='piradigm.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s'
)

logger = logging.getLogger(__name__)


class DriveTrain():
    def __init__(self, timeout=120):
        time.sleep(0.01)
        logging.info("initialising drivetrain")
        self.timeout = timeout
        self.start_time = time.clock()
        self.pz = piconzero
        self.pz.init()
        time.sleep(0.5)
        self.pz.setOutputConfig(0,2)
        self.motor_max = 100
        # battery voltage check constants
        self.BATT_CONSTANTS = {
            "adc_gain": 0.02909,
            "adc_offset": -15.06,
            "adc_pin": 3,
            "min_v": 7.45
        }
        self.pz.setInputConfig(self.BATT_CONSTANTS['adc_pin'], 1)
        time.sleep(0.01)
        self.slow_speed = 20
        self.deadband = 1
        self.boost_cycles = 1
        self.boost_dwell = 9
        self.name = "Drivetrain"

        # value to set if motor speed should be held consistent across battery discharge
        self.should_normalise_motor_speed = True
        self.killed = False
        self.left_counter = 0
        self.right_counter = 0
        self.trigger_angle = {
            'fire': 100,
            'cock': 140,
            'safe': 150,
        }
        self.safe_trigger = self.trigger_angle.get('safe')
        # Initialise self.average_batt_v with current_batt_v
        self.average_batt_v = self.current_batt_v

    def move(self, forward, turn):
        steering_left, steering_right = self.steering(forward, turn)
        motor_left, motor_right = self.get_motor_values(steering_left, steering_right)
        self.left_counter, motor_left = self.dither(self.left_counter, motor_left)
        self.right_counter, motor_right = self.dither(self.right_counter, motor_right)
        logging.debug("steering L/R: %s, %s" % (steering_left, steering_right))
        logging.debug("motor value L/R: %s, %s" % (motor_left, motor_right))
        logging.debug("counter: %s, %s" % (self.left_counter, self.right_counter))
        # smooth out transients
        self.average_batt_v = 0.9 * self.average_batt_v + 0.1 * self.current_batt_v
        if (self.average_batt_v > self.BATT_CONSTANTS['min_v']):
            if self.should_normalise_motor_speed:
                motor_right = int(float(motor_right) * self.BATT_CONSTANTS['min_v'] / self.average_batt_v)
                motor_left = int(float(motor_left) * self.BATT_CONSTANTS['min_v'] / self.average_batt_v)
            self.pz.setMotor(1, motor_right)
            self.pz.setMotor(0, motor_left)
        else:
            logging.info("stopping, battery too low for motors, at: %.2f", self.average_batt_v)
            self.pz.setMotor(1, 0)
            self.pz.setMotor(0, 0)

    def trigger(self, position):
        self.pz.setOutput(0, self.trigger_angle.get(position, self.safe_trigger))
       
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

    @property
    def current_batt_v(self):
        """uses an ADC channel to read battery voltage"""
        voltage_at_pin = float(self.pz.readInput(self.BATT_CONSTANTS['adc_pin']))
        return self.BATT_CONSTANTS['adc_gain'] * voltage_at_pin + self.BATT_CONSTANTS['adc_offset']

    def get_motor_values(self, steering_left, steering_right):
        motor_left = int(steering_left * self.motor_max) * -1
        motor_right = int(steering_right * self.motor_max) * -1

        return (motor_left, motor_right)

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def stop(self):
        logging.info("DriveTrain stopping")
        self.pz.stop()
        self.pz.cleanup()
        self.killed = True

    def dither(self, counter, speed):
        # function takes a speed and occassionally adds a boost, helpful at very
        # low speeds counter is between 0 and (self.boot_cycles + self.boost_dwell)
        # and is used to schedule boosts. speed is between -1 and +1. modified
        # speed and counter are returned
        if self.deadband < abs(speed) < self.slow_speed:
            speed = int(speed - math.copysign(1, speed))
            counter += 1
            if counter < self.boost_cycles:
                speed = speed + int(math.copysign(self.slow_speed, speed))
            elif counter > (self.boost_cycles + self.boost_dwell):
                counter = 0
        return (counter, speed)
