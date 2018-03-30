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
        self._colour = colour
        self.found = False
        self.retreated = False
        self.cycle = 0
        self.menu = False
        self.last_a_error = 0
        self.last_t_error = 0
        self.AREA_P = 0.00015
        self.AREA_D = 0.0003
        self.TURN_P = 0.7
        self.TURN_D = 0.3
        self.colour_bounds = json.load(open('rainbow.json'))
        self.hsv_lower = (0, 0, 0)
        self.hsv_upper = (0, 0, 0)
        self.BACK_OFF_AREA = 1000
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
        image = image[80:180, 0:320]
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
        found_x = -1
        found_y = -1
        biggest_contour = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + (w / 2)
            cy = y + (h / 2)
            area = w * h
            aspect_ratio = float(h)/w
            if found_area < area and aspect_ratio < 2 and aspect_ratio > 0.5:
                found_area = area
                found_x = cx
                found_y = cy
                biggest_contour = contour
        if found_area > self.MIN_CONTOUR_AREA:
            mask = numpy.zeros(image.shape[:2], dtype="uint8")
            cv2.drawContours(mask, [biggest_contour], -1, 255, -1)
            mask = cv2.erode(mask, None, iterations=2)
            mean = cv2.mean(image, mask=mask)[:3]
            #print mean
            ball = [found_x, found_y, found_area]
        else:
            ball = None
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
            self.drive_toward_ball(ball, self.colour)
        elif not self.retreated:
            self.drive_away_from_ball(ball, self.colour)


    # TODO: Move this motor control logic out of the stream processor
    # as it is challenge logic, not stream processor logic
    # (the clue is that the streamprocessor needs a drivetrain)

    # Set the motor speed from the ball position
    def drive_toward_ball(self, ball, targetcolour):
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area > self.MAX_AREA:
                self.drive.move(0, 0)
                self.found = True
                logger.info('Close enough to %s ball, stopping' % (targetcolour))
            else:
                # follow 0.2, /2 good
                a_error = self.MAX_AREA - area
                forward = self.AREA_P * a_error
                t_error  = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error
                if self.last_t_error is not None:
                    #if there was a real error last time then do some damping
                    turn -= self.TURN_D *(self.last_t_error - t_error)
                    forward -= self.AREA_D * (self.last_a_error - a_error)
                if self.DRIVING and self.tracking:
                    self.drive.move(turn, forward)
                self.last_t_error = t_error
                self.last_a_error = a_error
                print ('%s ball, %s' % (targetcolour, t_error))
        else:
            # no ball, turn right 0.25, 0.12 ok but a bit sluggish and can get stuck in corner 0.3, -0.12 too fast, 0.3, 0 very slow. 0.25, 0.15 good
            if self.cycle > 5:
                if self.DRIVING and self.tracking:
                    self.drive.move(self.FAST_SEARCH_TURN, 0)
                self.cycle = 0
            else:
                self.drive.move(0, 0)
                self.cycle += 1
            logger.info('No %s ball' % (targetcolour))
            # reset PID errors
            self.last_t_error = None

 # drive away from the ball, back to the middle
    def drive_away_from_ball(self, ball, targetcolour):
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area < self.BACK_OFF_AREA:
                self.drive.move(0, 0)
                self.retreated = True
                logger.info('far enough away from %s, stopping' % (targetcolour))
            else:
                forward = self.BACK_OFF_SPEED
                t_error = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error
                if self.last_t_error is not None:
                    turn -= self.TURN_D *(self.last_t_error - t_error)
                if self.DRIVING and self.tracking:
                    self.drive.move(turn, forward)
                self.last_t_error = t_error
        else:
            # ball lost, stop
            self.found = False
            self.drive.move(0, 0)
            logger.info('%s ball lost' % (targetcolour))



class Rainbow(BaseChallenge):
    """Rainbow challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 320  # Camera image width
        self.image_height = 240  # Camera image height
        self.frame_rate = Fraction(20)  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.menu = False
        self.joystick=joystick
        super(Rainbow, self).__init__(name='Rainbow', timeout=timeout, logger=logger)

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
                with open('rainbow.json', 'w') as f:
                    json.dump(data, f)
        elif button['dright']:
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
        elif button['r1']:
            self.timeout = 0
        elif button['r2']:
            self.processor.tracking = True
            print "Starting"
        elif button['l1']:
            self.processor.tracking = False
            self.drive.move(0,0)
            print "Stopping"
        if button['l2']:
            self.progress_colour()
            print ("manually moved on to %s" % self.processor.colour)

    def progress_colour(self):
        if self.processor.colour is not "green":
            if self.processor.colour is "yellow": self.processor.colour = "green"
            if self.processor.colour is "blue": self.processor.colour = "yellow"
            if self.processor.colour is "red": self.processor.colour = "blue"
            self.processor.found = False
            self.processor.retreated = False
        else:
            print "finished"
            self.timeout=0

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
            colour="red"
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

