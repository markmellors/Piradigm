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
sys.path.append('/usr/local/lib/python2.7/site-packages')

from docopt import docopt
import random
import pygame
from pygame.locals import *
import sgc
from sgc.locals import *
from my_button import MyButton
from remote_control import RC
from rainbow import Rainbow
from marker_maze import Maze
from straightline import StraightLineSpeed
from pi_noon import PiNoon
from approxeng.input.selectbinder import ControllerResource
import cv2.aruco as aruco

VERSION = '0.3Mazing'

arguments = docopt(__doc__, version=VERSION)

# Global variables
# TODO - Kill these
BUTTON_CLICK_TIME = 0.5

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
        self.markers = aruco.Dictionary_create(6, 3)

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
            btn = MyButton(label=text, pos=(xpo, ypo), col=colour, label_col=text_colour)
        )

    def button_handler(self, event):
        """Button action handler. Currently differentiates between
        exit, rc, rainbow and other buttons only"""
        logger.debug("%s button pressed", event.label)
        if event.label is "RC":
            logger.info("launching RC challenge")
            new_challenge = RC(timeout=self.timeout, screen=self.screen, joystick=self.joystick)
            return new_challenge
        elif event.label is "Rainbow":
            logger.info("launching Rainbow challenge")
            new_challenge = Rainbow(timeout=self.timeout, screen=self.screen, joystick=self.joystick)
            return new_challenge
        elif event.label is "Maze":
            logger.info("launching Maze challenge")
            new_challenge = Maze(timeout=self.timeout, screen=self.screen, joystick=self.joystick, markers = self.markers)
            return new_challenge
        elif event.label is "Speed":
            logger.info("launching Speed challenge")
            new_challenge = StraightLineSpeed(timeout=self.timeout, screen=self.screen, joystick=self.joystick, markers = self.markers)
            return new_challenge
        elif event.label == "Pi Noon":
            logger.info("launching Pi Noon challenge")
            new_challenge = PiNoon(timeout=self.timeout, screen=self.screen, joystick=self.joystick)
            return new_challenge
        elif event.label is "Exit":
            logger.info("Exit button pressed. Exiting now.")
            return "Exit"
        else:
            logger.info("unsupported button selected (%s)", event.label)
            return "Other"

    def joystick_handler(self, button):
       if button['dright']:
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 0, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
       elif button['dleft']:
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 1, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
       elif button['ddown']:
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 0, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 0, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
       elif button['dup']:
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 1, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 1, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
       elif button['select']:
           pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
               'mod': 0, 'scancode': 28, 'key': pygame.K_RETURN, 'unicode': "u'\t'"}))
           time.sleep(BUTTON_CLICK_TIME)
           pygame.event.post(pygame.event.Event(pygame.KEYUP,{
               'mod': 0, 'scancode': 28, 'key': pygame.K_RETURN, 'unicode': "u'\t'"}))
           
       
        
    def run(self):
        logger.info("Initialising pygame")
        pygame.init()
        pygame.font.init()
        clock = pygame.time.Clock()
        logger.info("Hiding Cursor")
        pygame.mouse.set_visible(False)
        logger.info("Setting screen size to %s", SCREEN_SIZE)
        #pygame.display.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        controls = sgc.surface.Screen(SCREEN_SIZE)
        self.buttons = self.setup_menu(self.screen)
        for btn in self.buttons:
           btn['btn'].add(btn['index'])
        running_challenge = None
        
        # While loop to manage touch screen inputs
        with ControllerResource() as self.joystick:
            while True:
                time = clock.tick(30)
                pygame.display.update()
                sgc.update(time)
                if self.joystick.connected:
                    self.joystick_handler(self.joystick.check_presses())
                for event in pygame.event.get():
                    sgc.event(event)
                    if event.type== GUI:
                        if event.widget_type is "Button":
                            requested_challenge = self.button_handler(event)
                            for btn in self.buttons:
                                btn['btn'].remove(btn['index'])
                            if requested_challenge:
                                logger.info("about to stop a thread if there's one running")
                                if running_challenge:
                                    logger.info("about to stop thread")
                                    self.stop_threads(running_challenge)
                            if requested_challenge is not None and requested_challenge is not "Exit" and requested_challenge is not "Other":
                                running_challenge = self.launch_challenge(requested_challenge)
                                logger.info("challenge %s launched", running_challenge.name)
                            elif requested_challenge == "Exit":
                                sys.exit()
                    # ensure there is always a safe way to end the program
                    # if the touch screen fails
                    elif event.type== KEYDOWN:
                        if event.key == K_ESCAPE:
                            sys.exit()
                    elif event.type == (USEREVENT+1):
                        print event.message
                        self.screen.fill(BLACK)
                        for btn in self.buttons:
                            btn['btn'].add(btn['index'])


if __name__ == "__main__":
    menu = Menu(timeout=int(arguments['--timeout']))
    menu.run()
