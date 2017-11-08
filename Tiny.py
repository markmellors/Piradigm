#!/usr/bin/env python
# coding: Latin-1

# Load library functions we want

from inputs import get_gamepad
#  from explorerhat import motor
import piconzero as pz
import time
import logging

logging.basicConfig(
            filename='piradigm.log',
            level=logging.DEBUG,
            format='%(asctime)s %(message)s'
        )


class RC:

    def mixer(self, inYaw, inThrottle,):
        left = inThrottle + inYaw
        right = inThrottle - inYaw
        scaleLeft = abs(left / 125.0)
        scaleRight = abs(right / 125.0)
        scaleMax = max(scaleLeft, scaleRight)
        scaleMax = max(1, scaleMax)
        out_left = int(constrain(left / scaleMax, -125, 125))
        out_right = int(constrain(right / scaleMax, -125, 125))
        results = [out_right, out_left]
        return results

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def __init__(self):
        self.timeOut = 10
        # Setup
        self.maxPower = 1.0
        self.power_left = 0.0
        self.power_right = 0.0
        self.x_axis = 0.0
        self.y_axis = 0.0
        self.pz.init()
        self.self.name = "RC"
        self.self.killed = False

    def run(self):
        try:
            # Loop indefinitely
            startTime = time.clock()
            while time.clock() < (startTime + self.TimeOut) and not self.killed:
                events = get_gamepad()
                for event in events:
                    logging.info(event.code, event.state)
                    if event.code == "ABS_Y":
                        if event.state > 130:
                            logging.info("Backwards")
                        elif event.state < 125:
                            logging.info("Forward")
                        y_axis = event.state
                        if y_axis > 130:
                            y_axis = -(y_axis - 130)
                        elif y_axis < 125:
                            y_axis = ((-y_axis) + 125)
                        else:
                            y_axis = 0.0
                        logging.info("Y: " + str(-y_axis))
                    if event.code == "ABS_Z":
                        if event.state > 130:
                            logging.info("Right")
                        elif event.state < 125:
                            logging.info("Left")
                        x_axis = event.state
                        if x_axis > 130:
                            x_axis = (x_axis - 130)
                        elif x_axis < 125:
                            x_axis = -((-x_axis) + 125)
                        else:
                            x_axis = 0.0
                        logging.info("X: " + str(x_axis))
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
                            pz.stop()
                            x_axis = 0
                            y_axis = 0
                    if event.code == "ABS_HAT0X":
                        if event.state == -1:
                            logging.info("D pad Left")
                            pz.spinLeft(100)
                        elif event.state == 1:
                            logging.info("D pad Right")
                            pz.spinRight(100)
                    if event.code == "ABS_HAT0Y":
                        if event.state == -1:
                            logging.info("D pad Up")
                            pz.forward(100)
                    elif event.state == 1:
                        logging.info("D pad Down")
                        pz.reverse(100)
                mixer_results = self.mixer(x_axis, y_axis)
                #print (mixer_results)
                power_left = int((mixer_results[0] / 125.0)*100)
                power_right = int((mixer_results[1] / 125.0)*100)
                logging.info("left: " + str(power_left) + " right: " + str(power_right))
                self.pz.setMotor(1, -power_right)
                self.pz.setMotor(0, power_left)
                # print(event.ev_type, event.code, event.state)
        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            logging.info("stopping")
            self.pz.stop()
            self.pz.cleanup()
            logging.info("bye")


def stop(self):
    logging.info("RC challenge stopping")
    self.killed = True
