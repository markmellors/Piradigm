""" Menu script for Piradigm
Usage:
  menu.py [--timeout=<seconds>]
  menu.py -h | --help | --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --timeout=<seconds>  Challenge timeout time in seconds. [default: 120].
"""
import logging
import logging.config
import os
import sys
import time
import threading

from docopt import docopt
import random
import pygame
from pygame.locals import *
import sgc
from sgc.locals import *
from remote_control import RC

VERSION = '0.1rc'

arguments = docopt(__doc__, version=VERSION)

# Global variables

# screen size
SCREEN_SIZE = width, height = 240, 320

# colours
BLUE = 26, 0, 255
SKY = 100, 50, 255
CREAM = 254, 255, 250
BLACK = 0, 0, 0
WHITE = 255, 255, 255

logging_ini_path = os.path.join(sys.path[0], 'logging.ini')
logging.config.fileConfig(logging_ini_path)
logger = logging.getLogger('piradigm')

class Menu():

    def __init__(self, *args, **kwargs):
        """Set up all the required environment variables"""
        env_vars = [
            ("SDL_FBDEV", "/dev/fb1"),
            ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
            ("SDL_MOUSEDRV", "TSLIB"),
        ]
        for var_name, val in env_vars:
            os.environ[var_name] = val
        self.timeout = kwargs.pop('timeout', 120)

    def launch_challenge(self, new_challenge):
        """launch requested challenge thread"""
        logger.info("launching new challenge")
        self.challenge_thread = threading.Thread(target=new_challenge.run)
        self.challenge_thread.daemon = True
        self.challenge_thread.start()
        logger.info("challenge launched - thread count: %d" % threading.active_count())
        return new_challenge

    def stop_threads(self, current_challenge):
        """stop running challenge"""
        if self.challenge_thread:
            current_challenge.stop()
            self.challenge_thread.join()

        logger.info("challenge stopped - thread count: %d" % threading.active_count())

        current_challenge = None
        logger.info("stopped running challenge")

    def setup_menu(self, surface, background_colour=BLACK):
        """Set up the menu on the specified surface"""
        # flood fill the surface with the background colour
        surface.fill(background_colour)

        # set up the fixed items on the menu
        # Add buttons and labels
        menu_config = [
            ("Speed", 6, 6, BLUE, WHITE), #, 62, 100, WHITE),
            ("Maze", 122, 6, BLUE, WHITE), #, 62, 100, WHITE),
            ("Rainbow", 6, 70, BLUE, WHITE), #, 62, 100, WHITE),
            ("Golf", 122, 70, BLUE, WHITE), #, 62, 100, WHITE),
            ("Pi Noon", 6, 134, BLUE, WHITE), #, 62, 100, WHITE),
            ("Obstacle", 122, 134, BLUE, WHITE), #, 62, 100, WHITE),
            ("Shooting", 6, 198, BLUE, WHITE), #, 62, 100, WHITE),
            ("RC", 122, 198, BLUE, WHITE), #, 62, 100, WHITE),
            ("Exit", 6, 262, BLUE, WHITE), #, 40, 210, WHITE),
            ("Stop", 122, 262, BLUE, WHITE),
        ]

        # perform list comprehension on menu_config, wherein we call
        # make_button with the index, and individual item arguments
        # note *item performs unpacking of the tuple and provides them
        # as individual arguments to make_button
        return [
            self.make_button(index, *item)
            for index, item
            in enumerate(menu_config)
        ]

    def make_button(self, index, text, xpo, ypo, colour, text_colour):
        """Make a text button at the specified x, y coordinates"""
        logger.debug("Making button with text '%s' at (%d, %d)", text, xpo, ypo)
        return dict(
            index=index,
            label=text,
            btn = sgc.Button(label=text, pos=(xpo, ypo), col=colour, label_col=text_colour)
        )

    def on_click(self, mousepos):
        """Click handling function to check mouse location"""
        logger.debug("on_click: %s", mousepos)
        # Iterate through our list of buttons and get the first one
        # whose rect returns True for pygame.Rect.collidepoint()
        try:
            button = next(obj for obj in self.buttons if obj['rect'].collidepoint(mousepos))
            logger.info(
                "%s clicked - launching %d",
                button["label"], button["index"]
            )
            # Call button_handler with the matched button's index value
            new_challenge = self.button_handler(button['index'])
            return new_challenge
        except StopIteration:
            logger.debug(
                "Click at pos %s did not interact with any button",
                mousepos
            )
            return None

    def button_handler(self, number):
        """Button action handler. Currently differentiates between
        exit, rc and other buttons only"""
        logger.debug("button %d pressed", number)
        time.sleep(0.01)
        if number < 7:
            logger.info("other selected")
            return "Other"
        elif number == 7:
            logger.info("launching RC challenge")
            new_challenge = RC(timeout=self.timeout)
            return new_challenge
        elif number == 8:
            logger.info("Exit button pressed. Exiting now.")
            return "Exit"
        else:
            return None

    def run(self):
        logger.info("Initialising pygame")
        pygame.init()
        pygame.font.init()
        clock = pygame.time.Clock()
        logger.info("Hiding Cursor")
        pygame.mouse.set_visible(False)

        logger.info("Setting screen size to %s", SCREEN_SIZE)
        self.screen = sgc.surface.Screen(SCREEN_SIZE)
        self.buttons = self.setup_menu(self.screen)
        for btn in self.buttons:
           btn['btn'].add(btn['index'])
        running_challenge = None
        #highlight a random button
        self.buttons[random.randint(0,9)]['btn']._draw_rect = True
        
        # While loop to manage touch screen inputs
        while True:
            time = clock.tick(30)
            pygame.display.update()
            sgc.update(time)
            for event in pygame.event.get():
                sgc.event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    logger.debug("screen pressed: %s", event.pos)
                    pos = (event.pos[0], event.pos[1])
                    # for debugging purposes - adds a small dot
                    # where the screen is pressed
                    # pygame.draw.circle(screen, WHITE, pos, 2, 0)
                    requested_challenge = self.on_click(pos)
                    logger.info("requested challenge is %s", requested_challenge)
                    if requested_challenge:
                        logger.info("about to stop a thread if there's one running")
                        if running_challenge:
                            logger.info("about to stop thread")
                            self.stop_threads(running_challenge)

                    if requested_challenge is not None and requested_challenge is not "Exit" and requested_challenge is not "Other":
                        running_challenge = self.launch_challenge(requested_challenge)
                        logger.info("challenge %s launched", running_challenge.name)

                    if requested_challenge == "Exit":
                        sys.exit()
                # ensure there is always a safe way to end the program
                # if the touch screen fails
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        sys.exit()


if __name__ == "__main__":
    menu = Menu(timeout=int(arguments['--timeout']))
    menu.run()
