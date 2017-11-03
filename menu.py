import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"
pygame.init()

#define function for printing text in a specific place and with a specific colour and adding a border
def make_button(text, xpo, ypo, colour):
	font=pygame.font.Font(None,24)
	label=font.render(str(text), 1, (colour))
	screen.blit(label,(xpo,ypo))
	pygame.draw.rect(screen, cream, (xpo-5,ypo-5,200,30),1)

#define function that checks for mouse location
def on_click(mousepos):
	click_pos = (mousepos) #(pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
	#check to see if exit has been pressed
	if 15 <= click_pos[0] <= 215 and 5 <= click_pos[1] <=35:
		print "Straight Line challenge launched"
		button(0)
	#now check to see if button 1 was pressed
	if 15 <= click_pos[0] <= 215 and 40 <= click_pos[1] <=70:
                print "Minimal Maze launched"
                button(1)	
	#now check to see if button 2 was pressed
        if 15 <= click_pos[0] <= 215 and 75 <= click_pos[1] <=105:
                print "Rainbow launched"
                button(2)
	#now check to see if button 3 was pressed
        if 15 <= click_pos[0] <= 215 and 110 <= click_pos[1] <=140:
                print "Golf launched"
                button(3)
	#now check to see if button 4 was pressed
        if 15 <= click_pos[0] <= 215 and 145 <= click_pos[1] <=200:
                print "Pi Noon Launched"
                button(4)

#define action on pressing buttons
def button(number):
	print "You pressed button ",number
	if number == 0:    #specific script when exiting
		#screen.fill(black)
		#font=pygame.font.Font(None,36)
        	#label=font.render("Good Bye!", 1, (white))
        	#screen.blit(label,(105,120))
		#pygame.display.flip()
		time.sleep(1)
		#sys.exit()

	if number == 1:		
                time.sleep(1) #do something interesting here
     		#sys.exit()
		
	if number == 2:		
		time.sleep(1) #do something interesting here
                #sys.exit()
		 
	if number == 3:	
		time.sleep(1) #do something interesting here
                #sys.exit()

	if number == 4:
		time.sleep(1) #do something interesting here
                #sys.exit()
	
#set size of the screen
size = width, height = 240, 320

#define colours
blue = 26, 0, 255
cream = 254, 255, 250
black = 0, 0, 0
white = 255, 255, 255

screen = pygame.display.set_mode(size)

#set up the fixed items on the menu
screen.fill(blue) #change the colours if needed
exit=pygame.image.load("exit.tiff")
screen.blit(exit,(200,130))

#Add buttons and labels
make_button("Straight Line", 20, 10, white)
make_button("Minimal Maze", 20, 45, white)
make_button("Rainbow", 20, 80, white)
make_button("Golf", 20, 115, white)
make_button("Pi Noon", 20, 150, white)
make_button("Obstacle Course", 20, 185, white)
make_button("Duck Shoot", 20, 220, white)
make_button("Remote Control", 20, 255, white)
make_button("Exit", 20, 290, white)






#While loop to manage touch screen inputs
while 1:	
	for event in pygame.event.get():
		if event.type == pygame.MOUSEBUTTONDOWN: 
			print "screen pressed" #for debugging purposes
			pos = (event.pos[0], event.pos[1]) #(pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
			print pos #for checking
			pygame.draw.circle(screen, white, pos, 2, 0) #for debugging purposes - adds a small dot where the screen is pressed
			on_click(pos)

#ensure there is always a safe way to end the program if the touch screen fails
		
		if event.type == KEYDOWN:
			if event.key == K_ESCAPE:
				sys.exit()
	pygame.display.update()
