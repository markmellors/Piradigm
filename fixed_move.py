from drivetrain import Drivetrain

import time

MOVE_TIME = float(1)

#straight line: 0.01 correction if at all is needed at 0.5 fwd
#straight line: 4s at speed = 1 gives about 7m on smooth floor
#straight line: 0.25s at speed = 1 gives about 0.48m/0.5m on smooth floor (flat/charged)
#straight line: 0.5s at speed = 1 gives about 0.75m/0.86m on smooth floor
#straight line: 0.75s at speed = 1 gives about 1.07m/1.2m on smooth floor
#straight line: 1s at speed = 1 gives about 1.38m/1.55m on smooth floor

#turning: 0.16s gives 90turn at speed = 1 & -1 on smooth floor
#turning: 0.16s gives 60turn at apeed = 1 on carpet
#turning: 0.37s gives 180turn at speed = 1 on smooth floor

#arc: 0.2s of speed=1, turn=1 gives Xturn @ R


TURN_CORRECTION = 0
MAX_SPEED = 1
STOP_TIME = 1
drive = Drivetrain(timeout=120)
MOVE_CYCLES = 1

count = 0
try:
    while count < MOVE_CYCLES:
        drive.move(TURN_CORRECTION, MAX_SPEED)
        time.sleep(MOVE_TIME)
        drive.move(0, 0)
        time.sleep(STOP_TIME)
        count += 1
    

except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
        print('\nUser shutdown')
        drive.move(0, 0)
