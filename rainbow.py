#q7#!/usr/bin/env python
# coding: Latin

import json
from collections import OrderedDict
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
        self.MAX_WIDTH = 60 #70  # Largest target to move towards
        self.MIN_CONTOUR_AREA = 3
        self.LEARNING_MIN_AREA = 30
        self._colour = colour
        self.found = False
        self.tried_left = False
        self.retreated = False
        self.cycle = 0
        self.just_moved = False
        self.last_a_error = 0
        self.last_w_error = 0
        self.last_t_error = 0
        self.WIDTH_P = 0.005
        self.WIDTH_D = 0.008
        self.TURN_P = 0.7
        self.TURN_D = 0.3
        # define colour keys (lower case)
        self.running_order = [
            'yellow',
            'red',
            'green',
            'blue'
        ]
        self.colour_positions = OrderedDict([(key, None) for key in self.running_order])
        # Initialise the index of the current ball we're looking for
        self.current_position = 0
        self.colour_seen = None
        self.first_seek_direction = 'right'  #not used yet
        self.seek_attempts = 0
        self.colour_bounds = json.load(open('rainbow.json'))
        self.mode = [self.learning, self.orientating, self.visiting]
        self.mode_number = 0
        self.hsv_lower = (0, 0, 0)
        self.hsv_upper = (0, 0, 0)
        self.TURN_SPEED = 1
        self.BRAKING = 0.2
        self.BACK_OFF_AREA = 1200
        self.BACK_OFF_SPEED = -0.6
        self.FAST_SEARCH_TURN = 1
        self.DRIVING = True
        self.tracking = False
        # Why the one second sleep?
        self.i=0
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

    def get_ball_colour_and_position(self, image):
        default_colour_bounds = ((40, 0, 0), (180, 255, 255))
        largest_colour_name = None
        largest_colour_x = None
        largest_colour_y = None
        largest_colour_area = None
        for colour in self.colour_positions.keys():
            colour_limits = self.colour_bounds.get(colour, default_colour_bounds)
            mask = threshold_image(image, colour_limits)
            x, y, a, ctr = find_largest_contour(mask)
            if a > self.LEARNING_MIN_AREA and a > largest_colour_area:
                largest_colour_name = colour
                largest_colour_x = x
                largest_colour_y = y
                largest_colour_area = a
        return largest_colour_name, largest_colour_x, largest_colour_y, largest_colour_area

    def turn_to_next_ball(self, previous_ball_position, direction ='right'):
        nominal_move_time = 0.24
        move_correction_factor = 0.03 #0.07
        move_time = nominal_move_time - (previous_ball_position - self.image_centre_x)/ self.image_centre_x * move_correction_factor
        turn = self.TURN_SPEED if direction == 'right' else -self.TURN_SPEED
        self.drive.move(turn, 0)
        time.sleep(move_time)
        self.drive.move(0, 0)
        time.sleep(move_time)
        self.just_moved = True

    def get_running_order_position_by_colour(self, colour):
        '''Return the position in the running order of a given colour key'''
        return self.running_order.index(colour.lower())
    
    def get_turn_direction_by_colour(self, current_colour, target_colour):
        turn_dir = 'right'
        step_size = (
            self.colour_positions[target_colour]
            - self.colour_positions[current_colour]
        )
        if step_size > len(self.running_order) / 2 or (step_size < 0 and step_size > -len(self.running_order) / 2):
            turn_dir = 'left'
        
        return turn_dir

    def seek(self):
        seek_time = 0.04 * self.seek_attempts + 0.03
        if self.tracking:
            if self.tried_left:
                seek_turn = self.FAST_SEARCH_TURN
                self.tried_left = True
            else:
                seek_turn = -self.FAST_SEARCH_TURN
                self.tried_left = False
            self.drive.move(seek_turn, 0)
            time.sleep(seek_time)
            self.drive.move(0, 0)
            self.seek_attempts += 1
        self.just_moved = True

    def learning(self, image):
        image = image[35:65, 0:320]
        if self.tracking:
            img = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
            img_name = "%dimg.jpg" % (self.i)
            # filesave for debugging: 
            #cv2.imwrite(img_name, img)
            self.i += 1
        if self.current_position == 0:
            if self.tracking:
                logger.info("moving to first position")
                turn_time = 0.13
                self.drive.move(self.FAST_SEARCH_TURN, 0)
                time.sleep(turn_time)
                self.drive.move(0, 0)
                self.current_position += 1
                self.just_moved = True
        else:
            colour, x, y, a = self.get_ball_colour_and_position(image)
            if colour is not None:
                self.seek_attempts = 0
                if self.colour_positions[colour] <> (self.current_position - 1):
                    self.colour_positions[colour] = self.current_position
                    logger.info("%s ball found at position %i, coordinate %d" % (colour, self.current_position, x))
                    if self.current_position < 4:
                        self.turn_to_next_ball(x)
                        self.current_position += 1
                    else:
                        logger.info("ball order is %s" % self.colour_positions)
                        self.colour_seen = colour
                        #leave learn mode, start seeking
                        learnt = 0
                        for colour in self.colour_positions:
                            if self.colour_positions[colour] is not None:
                                learnt += 1
                        if learnt < 4:
                            logger.info("lost a ball, learning failed")
                            self.mode_number = 3
                        else:
                            self.mode_number = 1 
                else:
                    #we're still on the same ball, try moving again
                    logger.info("%s ball found again, this time at position %i, coordinate %d" % (colour, self.current_position, x))
                    self.turn_to_next_ball(x)
            else:
                logger.info("No balls found, seeking")
                self.seek()

    def orientating(self, image):
        colour, x, y, a = self.get_ball_colour_and_position(image)
        if colour is not None:
            self.seek_attempts = 0
            if colour == self.colour:
                logger.info("orientated to %s ball, moving to visiting mode" % colour)
                self.mode_number = 2
            else:
                direction = self.get_turn_direction_by_colour(colour, self.colour)
                logger.info("%s ball found, turning %s towards %s" % (colour, direction, self.colour))
                self.turn_to_next_ball(x, direction=direction)
        else:
            logger.info("No balls found, seeking")
            self.seek()

    def visiting(self, image):
        screen = pygame.display.get_surface()
        default_colour_bounds = ((40, 0, 0), (180, 255, 255))
        hsv_lower, hsv_upper = self.colour_bounds.get(
            self.colour, default_colour_bounds
        )
        imrange = cv2.inRange(
            image,
            numpy.array(hsv_lower),
            numpy.array(hsv_upper)
        )
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
        found_w = -1
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
                found_w = w
                biggest_contour = contour
        if biggest_contour is not None:
            ball = [found_x, found_y, found_area, found_w]
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

    # Image processing function
    def process_image(self, image, screen):
        if self.just_moved:
            #if we've jsut done a fixed time move, ignore the next frame
            logger.debug("frame flush")
            self.just_moved = False
        else:
            screen = pygame.display.get_surface()
            # crop image to speed up processing and avoid false positives
            image = image[80:180, 0:320]
            img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frame = pygame.surfarray.make_surface(cv2.flip(img, 1))
            screen.fill([0, 0, 0])
            font = pygame.font.Font(None, 24)
            screen.blit(frame, (0, 0))
            image = cv2.medianBlur(image, 5)
            # Convert the image from 'BGR' to HSV colour space
            image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            self.mode[self.mode_number](image)


    # TODO: Move this motor control logic out of the stream processor
    # as it is challenge logic, not stream processor logic
    # (the clue is that the streamprocessor needs a drivetrain)

    # Set the motor speed from the ball position
    def drive_toward_ball(self, ball, targetcolour):
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            width = ball[3]
            if width > self.MAX_WIDTH:
                self.drive.move(0, -self.BRAKING)
                self.found = True
                logger.info('Close enough to %s ball, stopping' % (targetcolour))
                time.sleep(0.3)
            else:
                # follow 0.2, /2 good
                w_error = self.MAX_WIDTH - width
                forward = self.WIDTH_P * w_error + 0.2
                t_error  = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error
                if self.last_t_error is not None:
                    #if there was a real error last time then do some damping
                    turn -= self.TURN_D *(self.last_t_error - t_error)
                    forward -= self.WIDTH_D * (self.last_w_error - w_error)
                if self.DRIVING and self.tracking:
                    self.drive.move(turn, forward)
                self.last_t_error = t_error
                self.last_w_error = w_error
                logger.info ('%s ball found, error:, %s, area: %s' % (targetcolour, t_error, area))
        else:
            # no ball, turn right 0.25, 0.12 ok but a bit sluggish and can get stuck in corner 0.3, -0.12 too fast, 0.3, 0 very slow. 0.25, 0.15 good
            if self.cycle > 1:
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
        BACK_OFF_TIMEOUT = 0.2
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area < self.BACK_OFF_AREA:
                self.drive.move(0, self.BRAKING)
                self.retreated = True
                logger.info('far enough away from %s, stopping' % (targetcolour))
                self.mode_number = 1
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
            self.lost_time = time.clock()
            self.drive.move(0, self.BACK_OFF_SPEED)
            logger.info('%s ball lost' % (targetcolour))



class Rainbow(BaseChallenge):
    """Rainbow challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 320  # Camera image width
        self.image_height = 240  # Camera image height
        self.frame_rate = Fraction(20)  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.joystick=joystick
        super(Rainbow, self).__init__(name='Rainbow', timeout=timeout, logger=logger)


    def joystick_handler(self, button):
        #if left or right buttons on right side of joystick pressed, treat them like arrow buttons
        if button['circle']:
            #next colour
            self.progress_colour()
        if button['square']:
            #previosu colour
            pass
        if button['r1']:
            self.stop()
        if button['r2']:
            self.processor.tracking = True
            logger.info("Starting moving")
        if button['l1']:
            self.processor.tracking = False
            self.drive.move(0,0)
            logger.info("Stopping moving")
        if button['l2']:
            #calibration mode
            pass

    def progress_colour(self):
        if self.processor.colour is not "green":
            if self.processor.colour is "yellow": self.processor.colour = "green"
            if self.processor.colour is "blue": self.processor.colour = "yellow"
            if self.processor.colour is "red": self.processor.colour = "blue"
            self.processor.found = False
            self.processor.retreated = False
        else:
            print "finished"
            self.stop()

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
        logger.info('Setting up image capture thread')
        self.image_capture_thread = ImageCapture(
            camera=self.camera,
            processor=self.processor
        )
        pygame.mouse.set_visible(True)
        logger.info("Initialised, starting")
        try:
            while not self.should_die:
                time.sleep(0.01)
                # TODO: Tidy this
                if self.joystick.connected:
                    self.joystick_handler(self.joystick.check_presses())
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
            #release camera
            self.camera.close()
            self.camera = None
            self.logger.info("stopping drive")
            self.drive.stop()
            pygame.mouse.set_visible(False)
            self.logger.info("bye")
            pygame.event.post(pygame.event.Event(USEREVENT+1,message="challenge finished"))

