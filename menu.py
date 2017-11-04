import os
import sys
import time

import pygame
from pygame.locals import *


def setup_environment():
    """Set up all the required environment variables"""
    env_vars = [
        ("SDL_FBDEV", "/dev/fb1"),
        ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
        ("SDL_MOUSEDRV", "TSLIB"),
    ]
    for var_name, val in env_vars:
        os.environ[var_name] = val


# define function for printing text in a specific place and
# with a specific colour and adding a border
def make_button(text, xpo, ypo, colour):
    font = pygame.font.Font(None, 24)
    label = font.render(str(text), 1, (colour))
    screen.blit(label, (xpo, ypo))
    pygame.draw.rect(screen, cream, (xpo - 5, ypo - 5, 100, 65), 1)


# define function that checks for mouse location
def on_click(mousepos):
    click_pos = (mousepos)
    # check to see if exit has been pressed
    if 15 <= click_pos[0] <= 115 and 5 <= click_pos[1] <= 70:
        print "Straight Line challenge launched"
        button(0)
    # now check to see if button 1 was pressed
    if 15 <= click_pos[0] <= 115 and 75 <= click_pos[1] <= 140:
        print "Rainbow challenge launched"
        button(1)
    # now check to see if button 2 was pressed
    if 15 <= click_pos[0] <= 115 and 145 <= click_pos[1] <= 210:
        print "Pi Noon challenge launched"
        button(2)
    # now check to see if button 3 was pressed
    if 15 <= click_pos[0] <= 115 and 215 <= click_pos[1] <= 280:
        print "Duck Shoot challnge launched"
        button(3)
    # now check to see if button 4 was pressed
    if 120 <= click_pos[0] <= 220 and 5 <= click_pos[1] <= 70:
        print "Minimal Maze challenge launched"
        button(4)
    # now check to see if button 5 was pressed
    if 120 <= click_pos[0] <= 220 and 75 <= click_pos[1] <= 140:
        print "Golf challenge launched"
        button(5)
    # now check to see if button 6 was pressed
    if 120 <= click_pos[0] <= 220 and 145 <= click_pos[1] <= 210:
        print "Obstacle Course challenge launched"
        button(6)
    # now check to see if button 7 was pressed
    if 120 <= click_pos[0] <= 220 and 215 <= click_pos[1] <= 280:
        print "Radio control mode launched"
        button(7)
    # now check to see if button 8 was pressed
    if 15 <= click_pos[0] <= 115 and 285 <= click_pos[1] <= 320:
        print "Exit selected"
        button(8)


# define action on pressing buttons
def button(number):
    print "You pressed button ", number
    if number == 0:    # specific script when exiting
        time.sleep(1)

    if number == 8:
        time.sleep(1)  # do something interesting here
        sys.exit()


pygame.init()
setup_environment()

# set size of the screen
size = width, height = 240, 320

# define colours
blue = 26, 0, 255
cream = 254, 255, 250
black = 0, 0, 0
white = 255, 255, 255

screen = pygame.display.set_mode(size)

# set up the fixed items on the menu
screen.fill(blue)  # change the colours if needed

# Add buttons and labels
make_button("Speed", 20, 10, white)
make_button("Maze", 125, 10, white)
make_button("Rainbow", 20, 80, white)
make_button("Golf", 125, 80, white)
make_button("Pi Noon", 20, 150, white)
make_button("Obstacle", 125, 150, white)
make_button("Shooting", 20, 220, white)
make_button("RC", 125, 220, white)
make_button("Exit", 20, 290, white)

# While loop to manage touch screen inputs
while True:
    for event in pygame.event.get():
        if event.type == pygame.MOUSEBUTTONDOWN:
            print "screen pressed"  # for debugging purposes
            pos = (event.pos[0], event.pos[1])
            # for debugging purposes - adds a small dot
            # where the screen is pressed
            # pygame.draw.circle(screen, white, pos, 2, 0)
            on_click(pos)

# ensure there is always a safe way to end the program
# if the touch screen fails

        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                sys.exit()

    pygame.display.update()
