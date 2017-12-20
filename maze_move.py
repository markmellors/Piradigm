from drivetrain import Drivetrain

import time


#straight line: 0.01 correction if at all is needed at 0.5 fwd
#straight line: 4s at speed = 1 gives about 7m on smooth floor
#straight line: 0.25s at speed = 1 gives about 0.48m on smooth floor
#straight line: 0.5s at speed = 1 gives about 0.75m on smooth floor
#straight line: 0.75s at speed = 1 gives about 1.07m on smooth floor
#straight line: 1s at speed = 1 gives about 1.38m on smooth floor

#turning: 0.16s gives 90turn at speed = 1 & -1 on smooth floor
#turning: 0.16s gives 60turn at apeed = 1 on carpet
#turning: 0.37s gives 180turn at speed = 1 on smooth floor

#arc: 0.2s of speed=1, turn=1 gives Xturn @ R


#seg_move: 0.05moves, 0.3 turn, speed = 1 gives ~0.4m radius
#seg_move: 0.05moves, 0.5 turn, speed = 1 gives ~0.3m radius
#seg_move: 0.05moves, 0.6 turn, speed = 1 gives ~0.25m radius
#seg_move: 0.05moves, 0.7 turn, speed = 1 gives ~0.2m radius


END_STRAIGHT = 0.55
LONG_STRAIGHT = 0.55
S_TURN = 0.58
NINTY_TURN = 0.39
MAX_SPEED = 1
MOVE_TIME = 0.05
TURN_TIME = 0.05
drive = Drivetrain(timeout=120)
S_CYCLES = 9
NINTY_CYCLES = 5

count = 0
try:
    drive.move(0, MAX_SPEED)
    time.sleep(END_STRAIGHT)
    while count < NINTY_CYCLES:
        drive.move(0, MAX_SPEED)
        time.sleep(MOVE_TIME)
        drive.move(NINTY_TURN, 0)
        time.sleep(TURN_TIME)
        count += 1
    count = 0
    drive.move(0, MAX_SPEED)
    time.sleep(LONG_STRAIGHT)
    while count < S_CYCLES:
        drive.move(0, MAX_SPEED)
        time.sleep(MOVE_TIME)
        drive.move(S_TURN, 0)
        time.sleep(TURN_TIME)
        count += 1
    count = 0
    while count < S_CYCLES:
        drive.move(0, MAX_SPEED)
        time.sleep(MOVE_TIME)
        drive.move(-S_TURN, 0)
        time.sleep(TURN_TIME)
        count += 1
    count = 0
    #drive.move(0,0)
    #raw_input("Press Enter to continue...")
    drive.move(0, MAX_SPEED)
    time.sleep(LONG_STRAIGHT)
    while count < NINTY_CYCLES:
        drive.move(0, MAX_SPEED)
        time.sleep(MOVE_TIME)
        drive.move(-NINTY_TURN, 0)
        time.sleep(TURN_TIME)
        count += 1
    count = 0
    drive.move(0, MAX_SPEED)
    time.sleep(END_STRAIGHT)    
    drive.move(0,0)

except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
        print('\nUser shutdown')
        drive.move(0, 0)
