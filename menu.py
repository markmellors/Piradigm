import logging
import os
import sys
import time
import threading

import pygame
from pygame.locals import *
import rc

# Global variables
challenge_name = "Nothing"
challenge = None

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

def launch_challenge(challenge_type, challenge_description):
    """launch requested challenge thread"""
    #stop_threads()
    logging.info("launching %s", challenge_description)
    challenge = challenge_type
    challenge_thread = threading.Thread(target=challenge.run)
    challenge_thread.start()
    challenge_name = challenge_description


def stop_threads():
    """stop running challenge"""
    if challenge_name is not "Nothing":
        challenge.stop()
        challenge = None
        challenge_thread = None
        logging.info("stopping %s",challenge_name)
        challenge_name = "Nothing"

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
    menu_config = [
        ("Speed", 20, 10, 62, 100, WHITE),
        ("Maze", 130, 10, 62, 100, WHITE),
        ("Rainbow", 20, 77, 62, 100, WHITE),
        ("Golf", 130, 77, 62, 100, WHITE),
        ("Pi Noon", 20, 144, 62, 100, WHITE),
        ("Obstacle", 130, 144, 62, 100, WHITE),
        ("Shooting", 20, 211, 62, 100, WHITE),
        ("RC", 130, 211, 62, 100, WHITE),
        ("Exit", 20, 278, 40, 210, WHITE),
    ]

    # perform list comprehension on menu_config, wherein we call
    # make_button with the index, and individual item arguments
    # note *item performs unpacking of the tuple and provides them
    # as individual arguments to make_button
    return [
        make_button(index, *item)
        for index, item
        in enumerate(menu_config)
    ]


def make_button(index, text, xpo, ypo, height, width, colour):
    """Make a text button at the specified x, y coordinates
    with the specified colour. Also adds a border (not configurable)"""
    logging.debug("Making button with text '%s' at (%d, %d)", text, xpo, ypo)
    font = pygame.font.Font(None, 24)
    label = font.render(str(text), 1, (colour))
    screen.blit(label, (xpo, ypo))
    return dict(
        index=index,
        label=text,
        rect=pygame.draw.rect(screen, CREAM, (xpo - 5, ypo - 5, width, height), 1)
    )


def on_click(mousepos):
    """Click handling function to check mouse location"""
    logging.debug("on_click: %s", mousepos)
    # Iterate through our list of buttons and get the first one
    # whose rect returns True for pygame.Rect.collidepoint()
    try:
        button = next(obj for obj in buttons if obj['rect'].collidepoint(mousepos))
        logging.info(
            "%s clicked - launching %d",
            button["label"], button["index"]
        )
        # Call button_handler with the matched button's index value
        button_handler(button['index'])
    except StopIteration:
        logging.debug(
            "Click at pos %s did not interact with any button",
            mousepos
        )


def button_handler(number):
    """Button action handler. Currently differentiates between
    exit, rc and other buttons only"""
    logging.debug("button %d pressed", number)
    if number == 0: 
        time.sleep(1)
    if number == 7:
        launch_challenge(rc,"RC")
    if number == 8:
        stop_threads()
        logging.info("Exit button pressed. Exiting now.")
        sys.exit()


setup_environment()

logging.info("Initialising pygame")
pygame.init()

logging.info("Hiding Cursor")
pygame.mouse.set_visible(False)

logging.info("Setting screen size to %s", SCREEN_SIZE)
screen = pygame.display.set_mode(SCREEN_SIZE)
buttons = setup_menu(screen)

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
