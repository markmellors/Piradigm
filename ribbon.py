#!/usr/bin/env python
# coding: Latin

import json
from my_button import MyScale
# Load all standard tools for image processing challenges
from img_base_class import *


# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen=None, camera=None, drive=None, colour="any"):
        super(StreamProcessor, self).__init__()
        self.camera = camera
        image_width, image_height = self.camera.resolution
        self.image_centre_x = image_width / 2.0
        self.image_centre_y = image_height / 2.0
        self.drive = drive
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.MAX_AREA = 4000  # Largest target to move towards
        self.MIN_CONTOUR_AREA = 3
        self.RIBBON_COLOUR = 'yellow'
        self.MARKER_COLOUR = 'red'
        self.found = False
        self.retreated = False
        self.cycle = 0
        self.menu = False
        self.last_a_error = 0
        self.last_t_error = 0
        self.AREA_P = 0.00015
        self.AREA_D = 0.0003
        self.MAX_SPEED = 0.35
        self.TURN_P = 6 * self.MAX_SPEED
        self.TURN_D = 3 * self.MAX_SPEED
        self.colour_bounds = json.load(open('ribbon.json'))
        self.hsv_lower = (0, 0, 0)
        self.hsv_upper = (0, 0, 0)
        self.BACK_OFF_SPEED = -0.25
        self.FAST_SEARCH_TURN = 0.7
        self.DRIVING = True
        self.tracking = False
        # Why the one second sleep?
        time.sleep(1)
        self.start()

    @property
    def colour(self):
        """Set the target colour property"""
        return self._colour

    @colour.setter
    def colour(self, colour):
        self._colour = colour

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and do some processing on it
                    self.stream.seek(0)
                    self.process_image(self.stream.array, self.screen)
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

    # Image processing function
    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        # crop image to speed up processing and avoid false positives
        image = image[30:60, 0:320]
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if not self.menu:
            frame = pygame.surfarray.make_surface(cv2.flip(img, 1))
            screen.fill([0, 0, 0])
            font = pygame.font.Font(None, 24)
            screen.blit(frame, (0, 0))
        image = cv2.medianBlur(image, 5)
        # Convert the image from 'BGR' to HSV colour space
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        # method will extract the colour we are interested in (between 0 and 180)
        default_colour_bounds = ((40, 0, 0), (180, 255, 255))
        limits = self.colour_bounds.get(
            self.RIBBON_COLOUR, default_colour_bounds
        )
        imrange = threshold_image(image, limits)
        if not self.menu:
            frame = pygame.surfarray.make_surface(cv2.flip(imrange, 1))
            screen.blit(frame, (100, 0))
            pygame.display.update()
        found_x, found_y, found_area = find_largest_contour(imrange)
        if found_area > self.MIN_CONTOUR_AREA:
            ribbon = [found_x, found_y, found_area]
        else:
            ribbon = None
        pygame.mouse.set_pos(found_y, 320 - found_x)
        # Set drives or report ball status
        self.follow_ribbon(ribbon)



    # TODO: Move this motor control logic out of the stream processor
    # as it is challenge logic, not stream processor logic
    # (the clue is that the streamprocessor needs a drivetrain)

    # Set the motor speed from the ball position
    def follow_ribbon(self, ribbon):
        turn = 0.0
        if ribbon:
            x = ribbon[0]
            t_error  = (self.image_centre_x - x) / self.image_centre_x
            turn = self.TURN_P * t_error
            if self.last_t_error is not None:
                #if there was a real error last time then do some damping
                turn -= self.TURN_D *(self.last_t_error - t_error)
            forward = self.MAX_SPEED
            if self.DRIVING and self.tracking:
               self.drive.move(turn, forward)
            self.last_t_error = t_error
        else:
            if self.DRIVING and self.tracking:
               self.drive.move(0, -self.MAX_SPEED/2)

            logger.info('No ribbon')
            # reset PID errors
            self.last_t_error = None



class Ribbon(BaseChallenge):
    """Ribbon following challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 320  # Camera image width
        self.image_height = 240  # Camera image height
        self.frame_rate = Fraction(20)  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.menu = False
        self.joystick=joystick
        super(Ribbon, self).__init__(name='Ribbon', timeout=timeout, logger=logger)

    def setup_controls(self):
        # colours
        #why do these need repeating when theyre in menu.py? aren't they global?
        BLUE = 26, 0, 255
        SKY = 100, 50, 255
        CREAM = 254, 255, 250
        BLACK = 0, 0, 0
        WHITE = 255, 255, 255
        control_config = [
           ("min hue", 5, 90, BLACK, WHITE),
           ("max hue", 115, 90, BLACK, WHITE),
           ("min saturation", 5, 165, BLACK, WHITE),
           ("max saturation", 115, 165, BLACK, WHITE),
           ("min value", 5, 240, BLACK, WHITE),
           ("max value", 115, 240, WHITE, WHITE),
        ]
        return [
            self.make_controls(index, *item)
            for index, item
            in enumerate(control_config)
        ]


    def make_controls(self, index, text, xpo, ypo, colour, text_colour):
        """make a slider control at the specified position"""
        logger.debug("making button with text '%s' at (%d, %d)", text, xpo, ypo)
        return dict(
            index=index,
            label=text,
            ctrl = MyScale(label=text, pos=(xpo, ypo), col=colour, min=0, max=255, label_col=text_colour, label_side="top")
        )

    def joystick_handler(self, button):
        #if left or right buttons on right side of joystick pressed, treat them like arrow buttons
        if button['circle']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 77, 'key': pygame.K_RIGHT, 'unicode': "u'\t'"}))
        elif button['square']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 75, 'key': pygame.K_LEFT, 'unicode': "u'\t'"}))
        elif button['start']:
            #start button brings up or hides menu
            self.menu = not self.menu
            colour = self.processor.colour
            if not self.menu:
                #menu closing, store values in file
                #first, get new values
                for ctrl in self.controls:
                    i = ctrl['index']
                    self.processor.colour_bounds[colour][i % 2][int(i/2)] = ctrl['ctrl'].value
                data = self.processor.colour_bounds
                with open('ribbon.json', 'w') as f:
                    json.dump(data, f)
        if button['r1']:
            self.timeout = 0
        if button['r2']:
            self.processor.tracking = True
            print "Starting"
        if button['l1']:
            self.processor.tracking = False
            self.drive.move(0,0)
            print "Stopping"

    def run(self):
        # Startup sequence
        logger.info('Setup camera')
        screen = pygame.display.get_surface()
        self.camera = picamera.PiCamera()
        self.camera.resolution = (self.image_width, self.image_height)
        self.camera.framerate = self.frame_rate

        logger.info('Setup the stream processing thread')
        # TODO: Remove dependency on drivetrain from StreamProcessor
        self.processor = StreamProcessor(
            screen=self.screen,
            camera=self.camera,
            drive=self.drive,
            colour="yellow"
        )
        # To switch target colour" on the fly, use:
        # self.processor.colour = "blue"
        self.controls = self.setup_controls()
        logger.info('Wait ...')
        time.sleep(2)
        logger.info('Setting up image capture thread')
        self.image_capture_thread = ImageCapture(
            camera=self.camera,
            processor=self.processor
        )
        pygame.mouse.set_visible(True)
        try:
            while not self.should_die:
                time.sleep(0.01)
                # TODO: Tidy this
                if self.joystick.connected:
                    self.joystick_handler(self.joystick.check_presses())
                self.processor.menu = self.menu
                if self.menu:
                    screen.fill([0, 0, 0])
                    colour = self.processor.colour
                    colour_bounds = self.processor.colour_bounds[colour]
                    #add the controls and give them their initial values
                    for ctrl in self.controls:
                        if not ctrl['ctrl'].active():
                            ctrl['ctrl'].add(ctrl['index'], fade=False)
                            i = ctrl['index']
                            ctrl['ctrl'].value = colour_bounds[i % 2][int(i/2)]
                else:
                    for ctrl in self.controls:
                        if ctrl['ctrl'].active():
                            ctrl['ctrl'].remove(fade=False)
                if self.processor.retreated:
                    self.progress_colour()
                sgc.update(time)

        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            self.logger.info("killed from keyboard")
        finally:
            # Tell each thread to stop, and wait for them to end
            self.logger.info("stopping threads")
            self.image_capture_thread.terminated = True
            self.image_capture_thread.join()
            self.processor.terminated = True
            self.processor.join()
            for ctrl in self.controls:
                if ctrl['ctrl'].active():
                    ctrl['ctrl'].remove(fade=False)
            #release camera
            self.camera.close()
            self.camera = None
            self.logger.info("stopping drive")
            self.drive.stop()
            pygame.mouse.set_visible(False)
            self.logger.info("bye")
            pygame.event.post(pygame.event.Event(USEREVENT+1,message="challenge finished"))

