from drivetrain import Drivetrain

import time

MOVE_TIME = float(5)
TURN_CORRECTION = 0.015
drive = Drivetrain(timeout=120)

start_time = time.clock()
drive.move(TURN_CORRECTION, 1)
try:
    time.sleep(MOVE_TIME)
    drive.move(0, 0)

except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
        print('\nUser shutdown')
        drive.move(0, 0)
