import logging
import os
import sys
import time
import threading

import pygame
from pygame.locals import *
from Tiny import RC

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

    def launch_challenge(self, new_challenge):
        """launch requested challenge thread"""
        logging.info("launching new challenge")
        self.challenge_thread = threading.Thread(target=new_challenge.run)
        self.challenge_thread.daemon = True
        self.challenge_thread.start()
        logging.info("challenge launched - thread count: %d" % threading.active_count())
        return new_challenge

    def stop_threads(self, current_challenge):
        """stop running challenge"""
        if self.challenge_thread:
            current_challenge.stop()
            self.challenge_thread.join()

        logging.info("challenge stopped - thread count: %d" % threading.active_count())

        current_challenge = None
        logging.info("stopped running challenge")

    def setup_menu(self, surface, background_colour=BLUE):
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
            self.make_button(index, *item)
            for index, item
            in enumerate(menu_config)
        ]

    def make_button(self, index, text, xpo, ypo, height, width, colour):
        """Make a text button at the specified x, y coordinates
        with the specified colour. Also adds a border (not configurable)"""
        logging.debug("Making button with text '%s' at (%d, %d)", text, xpo, ypo)
        font = pygame.font.Font(None, 24)
        label = font.render(str(text), 1, (colour))
        self.screen.blit(label, (xpo, ypo))
        return dict(
            index=index,
            label=text,
            rect=pygame.draw.rect(self.screen, CREAM, (xpo - 5, ypo - 5, width, height), 1)
        )

    def on_click(self, mousepos):
        """Click handling function to check mouse location"""
        logging.debug("on_click: %s", mousepos)
        # Iterate through our list of buttons and get the first one
        # whose rect returns True for pygame.Rect.collidepoint()
        try:
            button = next(obj for obj in self.buttons if obj['rect'].collidepoint(mousepos))
            logging.info(
                "%s clicked - launching %d",
                button["label"], button["index"]
            )
            # Call button_handler with the matched button's index value
            new_challenge = self.button_handler(button['index'])
            return new_challenge
        except StopIteration:
            logging.debug(
                "Click at pos %s did not interact with any button",
                mousepos
            )
            return None

    def button_handler(self, number):
        """Button action handler. Currently differentiates between
        exit, rc and other buttons only"""
        logging.debug("button %d pressed", number)
        time.sleep(0.01)
        if number < 7:
            logging.info("other selected")
            return "Other"
        elif number == 7:
            logging.info("launching RC challenge")
            new_challenge = RC()
            return new_challenge
        elif number == 8:
            logging.info("Exit button pressed. Exiting now.")
            return "Exit"
        else:
            return None

    def run(self):
        logging.info("Initialising pygame")
        pygame.init()
        clock = pygame.time.Clock()
        logging.info("Hiding Cursor")
        pygame.mouse.set_visible(False)

        logging.info("Setting screen size to %s", SCREEN_SIZE)
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.buttons = self.setup_menu(self.screen)
        running_challenge = None

        # While loop to manage touch screen inputs
        while True:
            clock.tick(30)
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    logging.debug("screen pressed: %s", event.pos)
                    pos = (event.pos[0], event.pos[1])
                    # for debugging purposes - adds a small dot
                    # where the screen is pressed
                    # pygame.draw.circle(screen, WHITE, pos, 2, 0)
                    requested_challenge = self.on_click(pos)
                    logging.info("requested challenge is %s", requested_challenge)
                    if requested_challenge:
                        logging.info("about to stop a thread if there's one running")
                        if running_challenge:
                            logging.info("about to stop thread")
                            self.stop_threads(running_challenge)

                    if requested_challenge is not None and requested_challenge is not "Exit" and requested_challenge is not "Other":
                        running_challenge = self.launch_challenge(requested_challenge)
                        logging.info("challenge %s launched", running_challenge.name)

                    if requested_challenge == "Exit":
                        sys.exit()
                # ensure there is always a safe way to end the program
                # if the touch screen fails
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        sys.exit()


if __name__ == "__main__":
    menu = Menu()
    menu.run()