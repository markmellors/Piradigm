import logging
import os
import sys
import time

import pygame
from pygame.locals import *

# Global variables

# screen size
SCREEN_SIZE = width, height = 240, 320

# colours
BLUE = 26, 0, 255
CREAM = 254, 255, 250
BLACK = 0, 0, 0
WHITE = 255, 255, 255

logging.basicConfig(
    filename='piradigm.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s'
)


def setup_environment():
    """Set up all the required environment variables"""
    env_vars = [
        ("SDL_FBDEV", "/dev/fb1"),
        ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
        ("SDL_MOUSEDRV", "TSLIB"),
    ]
    for var_name, val in env_vars:
        os.environ[var_name] = val


def setup_menu(surface, background_colour=BLUE):
    """Set up the menu on the specified surface"""
    # flood fill the surface with the background colour
    surface.fill(background_colour)

    # set up the fixed items on the menu
    # Add buttons and labels
    make_button("Speed", 20, 10, WHITE)
    make_button("Maze", 125, 10, WHITE)
    make_button("Rainbow", 20, 80, WHITE)
    make_button("Golf", 125, 80, WHITE)
    make_button("Pi Noon", 20, 150, WHITE)
    make_button("Obstacle", 125, 150, WHITE)
    make_button("Shooting", 20, 220, WHITE)
    make_button("RC", 125, 220, WHITE)
    make_button("Exit", 20, 290, WHITE)


def make_button(text, xpo, ypo, colour):
    """Make a text button at the specified x, y coordinates
    with the specified colour. Also adds a border (not configurable)"""
    logging.debug("Making button with text '%s' at (%d, %d)", text, xpo, ypo)
    font = pygame.font.Font(None, 24)
    label = font.render(str(text), 1, (colour))
    screen.blit(label, (xpo, ypo))
    pygame.draw.rect(screen, CREAM, (xpo - 5, ypo - 5, 100, 65), 1)


def on_click(mousepos):
    """Click handling function to check mouse location"""
    logging.debug("on_click: %s", mousepos)
    click_pos = (mousepos)
    # check to see if exit has been pressed
    if 15 <= click_pos[0] <= 115 and 5 <= click_pos[1] <= 70:
        logging.info("Straight Line challenge launched")
        button(0)
    # now check to see if button 1 was pressed
    if 15 <= click_pos[0] <= 115 and 75 <= click_pos[1] <= 140:
        logging.info("Rainbow challenge launched")
        button(1)
    # now check to see if button 2 was pressed
    if 15 <= click_pos[0] <= 115 and 145 <= click_pos[1] <= 210:
        logging.info("Pi Noon challenge launched")
        button(2)
    # now check to see if button 3 was pressed
    if 15 <= click_pos[0] <= 115 and 215 <= click_pos[1] <= 280:
        logging.info("Duck Shoot challenge launched")
        button(3)
    # now check to see if button 4 was pressed
    if 120 <= click_pos[0] <= 220 and 5 <= click_pos[1] <= 70:
        logging.info("Minimal Maze challenge launched")
        button(4)
    # now check to see if button 5 was pressed
    if 120 <= click_pos[0] <= 220 and 75 <= click_pos[1] <= 140:
        logging.info("Golf challenge launched")
        button(5)
    # now check to see if button 6 was pressed
    if 120 <= click_pos[0] <= 220 and 145 <= click_pos[1] <= 210:
        logging.info("Obstacle Course challenge launched")
        button(6)
    # now check to see if button 7 was pressed
    if 120 <= click_pos[0] <= 220 and 215 <= click_pos[1] <= 280:
        logging.info("Radio control mode launched")
        button(7)
    # now check to see if button 8 was pressed
    if 15 <= click_pos[0] <= 115 and 285 <= click_pos[1] <= 320:
        logging.info("Exit selected")
        button(8)


def button(number):
    """Button action handler. Currently differentiates between
    exit and other buttons only"""
    logging.debug("button %d pressed", number)
    if number == 0:    # specific script when exiting
        time.sleep(1)

    if number == 8:
        time.sleep(1)  # do something interesting here
        logging.info("Exit button pressed. Exiting now.")
        sys.exit()


setup_environment()

logging.info("Initialising pygame")
pygame.init()

logging.info("Setting screen size to %s", SCREEN_SIZE)
screen = pygame.display.set_mode(SCREEN_SIZE)
setup_menu(screen)

# While loop to manage touch screen inputs
while True:
    for event in pygame.event.get():
        if event.type == pygame.MOUSEBUTTONDOWN:
            logging.debug("screen pressed: %s", event.pos)
            pos = (event.pos[0], event.pos[1])
            # for debugging purposes - adds a small dot
            # where the screen is pressed
            # pygame.draw.circle(screen, WHITE, pos, 2, 0)
            on_click(pos)

# ensure there is always a safe way to end the program
# if the touch screen fails
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                sys.exit()

    pygame.display.update()
