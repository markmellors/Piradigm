from drivetrain import Drivetrain

import time

MOVE_TIME = float(5)
TURN_CORRECTION = 0.01 #0.01 good for 0.5 fwd
MAX_SPEED = 0.5
drive = Drivetrain(timeout=120)

start_time = time.clock()
drive.move(TURN_CORRECTION, MAX_SPEED)
try:
    time.sleep(MOVE_TIME)
    drive.move(0, 0)

except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
        print('\nUser shutdown')
        drive.move(0, 0)
