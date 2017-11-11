#!/usr/bin/env python
# coding: Latin-1

# Load library functions we want

from inputs import get_gamepad
#  from explorerhat import motor
import piconzero
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
        # Setup
        self.maxPower = 1.0
        self.power_left = 0.0
        self.power_right = 0.0
        self.x_axis = 0.0
        self.y_axis = 0.0
        self.pz = piconzero
        self.pz.init()
        self.name = "RC"
        self.killed = False

    def run(self):
        logging.info("running RC challenge")
        try:
            # Loop indefinitely
            startTime = time.clock()
            logging.info("start time: %s", startTime)
            while time.clock() < (startTime + self.timeOut) and not self.killed:
                logging.info("RC looping")
                time.sleep(0.01)
                events = get_gamepad()
                for event in events:
                    logging.info("event code: %s , event state: %s", event.code, event.state)
                    if event.code == "ABS_Y":
                        #if event.state > 130:
                            #logging.info("Backwards")
                        #elif event.state < 125:
                            #logging.info("Forward")
                        self.y_axis = event.state
                        if self.y_axis > 130:
                            self.y_axis = -(self.y_axis - 130)
                        elif self.y_axis < 125:
                            self.y_axis = ((-self.y_axis) + 125)
                        else:
                            self.y_axis = 0.0
                        logging.info("Y: %s", -self.y_axis)
                    if event.code == "ABS_Z":
                        #if event.state > 130:
                            #logging.info("Right")
                        #elif event.state < 125:
                            #logging.info("Left")
                        self.x_axis = event.state
                        if self.x_axis > 130:
                            self.x_axis = (self.x_axis - 130)
                        elif self.x_axis < 125:
                            self.x_axis = -((-self.x_axis) + 125)
                        else:
                            self.x_axis = 0.0
                        logging.info("X: %s", self.x_axis)
                    if event.code == "BTN_TL":
                        if event.state is True:
                            logging.info("Botton Left")
                    if event.code == "BTN_TR":
                        if event.state is True:
                            logging.info("Botton Right")
                    if event.code == "BTN_Z":
                        if event.state is True:
                            logging.info("Top right")
                    if event.code == "BTN_WEST":
                        if event.state is True:
                            logging.info("Top left")
                    if event.code == "BTN_TL2":
                        if event.state is True:
                            logging.info("Select")
                            self.pz.stop()
                            self.x_axis = 0
                            self.y_axis = 0
                    if event.code == "ABS_HAT0X":
                        if event.state == -1:
                            logging.info("D pad Left")
                            self.pz.spinLeft(100)
                        elif event.state == 1:
                            logging.info("D pad Right")
                            self.pz.spinRight(100)
                    if event.code == "ABS_HAT0Y":
                        if event.state == -1:
                            logging.info("D pad Up")
                            self.pz.forward(100)
                    elif event.state == 1:
                        logging.info("D pad Down")
                        self.pz.reverse(100)
                mixer_results = self.mixer(self.x_axis, self.y_axis)
                #print (mixer_results)
                power_left = int((mixer_results[0] / 125.0)*100)
                power_right = int((mixer_results[1] / 125.0)*100)
                #logging.info("left: %s right: %s", power_left, power_right)
                self.pz.setMotor(1, -power_right)
                self.pz.setMotor(0, power_left)
                # print(event.ev_type, event.code, event.state)
        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            logging.info("stopping")
            self.pz.stop()
            self.pz.cleanup()
            logging.info("bye")


    def mixer(self, inYaw, inThrottle,):
        left = inThrottle + inYaw
        right = inThrottle - inYaw
        scaleLeft = abs(left / 125.0)
        scaleRight = abs(right / 125.0)
        scaleMax = max(scaleLeft, scaleRight)
        scaleMax = max(1, scaleMax)
        out_left = int(self.constrain(left / scaleMax, -125, 125))
        out_right = int(self.constrain(right / scaleMax, -125, 125))
        results = [out_right, out_left]
        return results

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def stop(self):
        logging.info("RC challenge stopping")
        self.killed = True
