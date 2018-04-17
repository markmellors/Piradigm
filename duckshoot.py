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
        self.drive = drive
        self.drive.should_normalise_motor_speed = False
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.MAX_AREA = 2000  # Largest target to shoot at
        self.MIN_CONTOUR_AREA = 400
        self.MAX_TARGET_SIZE = 2000
        self.MAX_TARGET_WIDTH = 80
        self.AIM_OFFSET = 45
        self._colour = colour
        self.found = False
        self.cycle = 0
        self.target_number = 0
        self.menu = False
        self.last_t_error = 0
        self.TURN_I = 0.05
        self.TURN_P = 2
        self.TURN_D = 0.8
        self.integrated_error = 0
        self.CROP_WIDTH = 320
        self.CROP_HEIGHT = 60
        self.image_centre_x = self.CROP_WIDTH / 2.0
        self.image_centre_y = self.CROP_HEIGHT / 2.0
        self.CROP_H_OFFSET = 160
        self.CROP_V_OFFSET = 180
        file_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(file_dir, 'duckshoot.json')
        with open(file_path) as json_file:
            self.colour_bounds = json.load(json_file)
        self.hsv_lower = (0, 0, 0)
        self.hsv_upper = (0, 0, 0)
        self.DRIVING = True
        self.tracking = False
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
        crop_v_min = self.CROP_V_OFFSET
        crop_v_max = self.CROP_V_OFFSET + self.CROP_HEIGHT
        crop_h_min = self.CROP_H_OFFSET
        crop_h_max = self.CROP_H_OFFSET + self.CROP_WIDTH
        image = image[crop_v_min:crop_v_max, crop_h_min:crop_h_max]
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if not self.menu:
            frame = pygame.surfarray.make_surface(cv2.flip(img, 1))
            screen.fill([0, 0, 0])
            font = pygame.font.Font(None, 24)
            screen.blit(frame, (0, 0))
        image = cv2.medianBlur(image, 11)
        # Convert the image from 'BGR' to HSV colour space
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        # method will extract the colour we are interested in (between 0 and 180)
        default_colour_bounds = ((40, 0, 0), (180, 255, 255))
        hsv_lower, hsv_upper = self.colour_bounds.get(
            self.colour, default_colour_bounds
        )
        imrange = cv2.inRange(
            image,
            numpy.array(hsv_lower),
            numpy.array(hsv_upper)
        )
        if not self.menu:
            frame = pygame.surfarray.make_surface(cv2.flip(imrange, 1))
            screen.blit(frame, (100, 0))
            pygame.display.update()
        # Find the contours
        contourimage, contours, hierarchy = cv2.findContours(
            imrange, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )

        # Go through each contour
        found_area = -1
        found_x = self.CROP_WIDTH+1
        found_y = -1
        biggest_contour = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + (w / 2)
            cy = y + (h / 2)
            area = w * h
            aspect_ratio = float(h)/w
            if found_x > cx and area > self.MIN_CONTOUR_AREA and area < self.MAX_TARGET_SIZE and w < self.MAX_TARGET_WIDTH:
                found_area = area
                found_x = cx
                found_y = cy
                biggest_contour = contour
        if biggest_contour is not None:
            target = [found_x, found_y, found_area]
        else:
            target = None
        pygame.mouse.set_pos(found_y, 320 - found_x)
        if biggest_contour is not None:
            contour_area = cv2.contourArea(biggest_contour)
            if self.screen and contour_area > self.MIN_CONTOUR_AREA:
                font = pygame.font.Font(None, 24)
                label = font.render(str(contour_area), 1, (250, 250, 250))
                self.screen.blit(label, (10, 30))
                # skate wheel at 100mm has area = 7000,
                # from centre of course is 180, far corner is 5
                pygame.display.update()
        # Set drives or report ball status
        if not self.found:
            self.turn_toward_target(target)
        else:
            self.fire()


    # TODO: Move this motor control logic out of the stream processor
    # as it is challenge logic, not stream processor logic
    # (the clue is that the streamprocessor needs a drivetrain)

    def fire(self):
        logger.info('firing')
        self.drive.trigger('fire')
        time.sleep(0.4)
        self.drive.trigger('cock')
        time.sleep(0.5)
        self.found = False
        self.target_number += 1
        logger.info('target %s fired at', self.target_number)
        if self.target_number > 5:
            self.running = False
            logger.info('last target found')

    def turn_toward_target(self, target):
        turn = 0.0
        AIM_TOL = 0.025
        if target:
            x = target[0]
            t_error = (self.image_centre_x - self.AIM_OFFSET - x) / self.image_centre_x
            self.integrated_error += t_error
            if abs(self.last_t_error) < AIM_TOL and abs(t_error) < AIM_TOL:
                self.drive.move(0, 0)
                self.found = True
                logger.info('target found %s, %s', self.last_t_error, t_error)
                self.last_t_error = AIM_TOL + 0.02
                
            else:
                forward = -0.02
                turn = (self.TURN_P * t_error
                    - self.TURN_D *(self.last_t_error - t_error)
                    + self.TURN_I * self.integrated_error)
                turn = min(max(-0.4, turn), 0.4)
                self.drive.move(turn, forward)
                self.last_t_error = t_error
                logger.info('hunting %s', t_error)
        else:
            #no targets found, stop
            self.found = False
            self.drive.move(0, 0)
            logger.info('no targets')



class Duckshoot(BaseChallenge):
    """Duck Shoot challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 640  # Camera image width
        self.image_height = 480  # Camera image height
        self.frame_rate = Fraction(20)  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.menu = False
        self.joystick=joystick
        super(Duckshoot, self).__init__(name='Duckshoot', timeout=timeout, logger=logger)

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
                with open('duckshoot.json', 'w') as f:
                    json.dump(data, f)
        if button['r1']:
            self.stop()
        if button['r2']:
            self.processor.tracking = True
            logger.info("Starting")
        if button['l1']:
            self.processor.tracking = False
            self.drive.move(0,0)
            logger.info("Stopping")
   

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
            colour="white"
        )
        # To switch target colour" on the fly, use:
        # self.processor.colour = "blue"
        self.controls = self.setup_controls()
        logger.info('Wait ...')
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
            self.should_normalise_motor_speed = True
            self.drive.stop()
            pygame.mouse.set_visible(False)
            self.logger.info("bye")
            pygame.event.post(pygame.event.Event(USEREVENT+1,message="challenge finished"))

