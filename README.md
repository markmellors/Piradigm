# Piradigm
This project is my entry for the Raspberry Pi Robot competition PiWars, 
2018. The hardware is a Tiny 4WD robot kit from Coretec Robotics, with a 
Picon zero motor controller from 4Tronix, a Raspberry Pi 3, Pi camera, 
2.8" PiTFT with touchscreen and a RockCandy wireless controller. The 
objective is to enter all the competition's challenges autonomously, 
using the camera as the only sensor. All challenges except straight line use a 0.8x wide angle lens on the camera
The robot is controlled using a Rock Candy wireless joypad. the left D pad is used to control a challenge launch menu, with the select button used to initiate the challenge.

So far the autonomous routines are in development:
Straight line: works as a script. It drives straight by tracking an Aruco marker at the end of the course. It needs a single Aruco marker printing out on A4, the robot will drivestraight towards this and stop (needs updating and integrating into the challenge launcher menu)

Minimal Maze: Has two working versions, a thread version that has fast but irratic image processing, and a more reliable non threaded version. Both versions require Aruco markers to navigate the maze. The markers need creating by running create_aruco_dict.py then printing them ~100x100mm (6 fit on a single A4 sheet). The markers need placing at the end of the first and second straights, and the start of the second to last and last straights (facing so they're square to the approaching robot), at floor level. THe markers need to be upright for their width (and therfore turn initiation point 

Over the Rainbow: This is working and integrated. The joypad start button toggles a challenge specific menu, where the colour limits for the current ball being detected can be changed. the left dpad navigates between parameters and the right dpad can change the paremeters. The selected colour limits are saved to a json file for future use.

Pi noon: This has three working versions, currently on the 'pi_noon', 'aggressive' and 'balloon' branches. pinoon and agressive detect opponents by finding the area of floor they obscure (assumed to be red or light brown). They are fairly fast but random in their movements. Balloon has a routine to rapidly calibrate the colour limits to match the oponents balloon. the calibrate mode is entered by pressing the left trigger and the vlaue stored by pressing the button above the trigger (L1). Pressing the right trigger initiates chasing the balloon. the right R1 button quits teh challenge. The Balloon branch also uses the colour of the floor to avoid driving out of the arena.

Duck shoot: Duck shoot is working quite well, provide the targets are detected clearly. It uses colour thresholding to identify the targets, assuming they are not red things on a red background. it then auto aims the gun and shoots untl they are knocked down.

Obstacle course and Slightly Deranged Golf still to be started.
