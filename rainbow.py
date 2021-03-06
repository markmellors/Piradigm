
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
        self.saving_images = False
        self.camera = camera
        image_width, image_height = self.camera.resolution
        self.image_centre_x = image_width / 2.0
        self.image_centre_y = image_height / 2.0
        self.drive = drive
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.MAX_WIDTH = 90 # Largest target to move towards
        self.MAX_AREA = 1000 #area requirement for bahaviour transition
        self.MAX_HEIGHT = 100
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
        self.WIDTH_D = 0.03
        self.TURN_P = 0.7
        self.TURN_D = 0.3
        self.seek_direction = None
        self.AIM_OFFSET = 0.13
        # define colour keys (lower case)
        self.running_order = [
            'red',
            'blue',
            'yellow',
            'green'
        ]
        self.colour_positions = OrderedDict([(key, None) for key in self.running_order])
        # Initialise the index of the current ball we're looking for
        self.current_position = 0
        self.colour_seen = None
        self.learning_failed = False
        self.first_seek_direction = 'right'  #not used yet
        self.seek_attempts = 0
        self.mode = [self.learning, self.orientating, self.visiting]
        self.mode_number = 0
        self.restart = False
        file_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(file_dir, 'rainbow.json')
        with open(file_path) as json_file:
            self.colour_bounds = json.load(json_file)
        self.hsv_lower = (0, 0, 0)
        self.hsv_upper = (0, 0, 0)
        self.TURN_SPEED = 1
        self.BACK_OFF_BRAKING = 0.3 #power when stopping the backoff move
        self.AT_BALL_BRAKING = 0.6 #power when stopping the drive towards move
        self.BACK_OFF_AREA = 2000
        self.BACK_OFF_SPEED = -0.8
        self.FAST_SEARCH_TURN = 1
        self.time_out = None
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

    @property
    def learned_colour_count(self):
        return  sum(1 for k,v in self.colour_positions.items() if v is not None)

    @property
    def all_colours_learned(self):
        return self.learned_colour_count == len(self.running_order)

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

    def turn_to_next_ball(self, previous_ball_position, direction='right'):
        nominal_move_time = 0.22
        move_correction_factor = 0.09
        move_time = nominal_move_time - (previous_ball_position - self.image_centre_x)/ self.image_centre_x * move_correction_factor
        turn = self.TURN_SPEED if direction == 'right' else -self.TURN_SPEED
        if self.tracking: self.drive.move(turn, 0)
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
        return turn_dir, abs(step_size)

    def seek(self, direction=None):
        seek_time = 0.02 * self.seek_attempts + 0.02
        if self.tracking:
            if (self.tried_left and not direction=='left') or direction=='right':
                logger.info( "seeking right, requested %s" % direction)
                seek_turn = self.FAST_SEARCH_TURN
                self.tried_left = False
            else:
                logger.info( "seeking left, request: %s" % direction)
                seek_turn = -self.FAST_SEARCH_TURN
                self.tried_left = True
            self.drive.move(seek_turn, 0)
            time.sleep(seek_time)
            self.drive.move(0, 0)
            time.sleep(seek_time)
            self.seek_attempts += 1
        self.just_moved = True

    def learning(self, image):
        image = image[30:69, 0:320]
        if self.tracking and self.saving_images:
            img = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
            img_name = "%dlearningimg.jpg" % (self.i)
            # filesave for debugging: 
            cv2.imwrite(img_name, img)
            self.i += 1
        if self.current_position == 0:
            if self.tracking:
                logger.info("moving to first position")
                turn_time = 0.13
                self.drive.move(self.FAST_SEARCH_TURN, 0)
                time.sleep(turn_time)
                self.drive.move(0, 0)
                time.sleep(turn_time)
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
                        logger.info("found ball order is %s" % self.colour_positions)
                        self.colour_seen = colour
                        #leave learn mode, start seeking
                        learnt = 0
                        if not self.all_colours_learned:
                            logger.info("lost a ball, learning failed")
                            self.learning_failed = True
                        self.mode_number = 1 
                else:
                    #we're still on the same ball, try moving again
                    logger.info("%s ball found again, this time at position %i, coordinate %d" % (colour, self.current_position, x))
                    self.turn_to_next_ball(x)
            else:
                logger.info("No balls found, seeking")
                self.seek(direction='right')

    def orientating(self, image):
        if self.learning_failed:
            colour, x, y, a = self.get_ball_colour_and_position(image)
            if colour is not None and colour == self.colour:
                logger.info("%s ball found, moving to visiting mode" % colour)
                self.mode_number = 2
            else:
                logger.info("%s ball found, seeking %s" % (colour, self.colour))
                self.seek_attempts = 1
                self.seek(direction='right')
        else:
            self.orientating_with_learning(image)


    def orientating_with_learning(self, image):
       if self.current_position == 0:
            if self.tracking:
                logger.info("moving to first position")
                turn_time = 0.13
                turn_factor = 1 if self.colour_positions[self.colour] <= 2 else -1
                self.drive.move(turn_factor * self.FAST_SEARCH_TURN, 0)
                time.sleep(turn_time)
                self.drive.move(0, 0)
                time.sleep(turn_time)
                self.current_position += 1
                self.just_moved = True
       else:
            colour, x, y, a = self.get_ball_colour_and_position(image)
            if colour is not None:
                self.seek_attempts = 0
                if colour == self.colour:
                    logger.info("orientated to %s ball, moving to visiting mode" % colour)
                    self.mode_number = 2
                else:
                    direction, steps = self.get_turn_direction_by_colour(colour, self.colour)
                    logger.info("%s ball found, turning %s towards %s. steps = %s" % (colour, direction, self.colour, steps))
                    self.turn_to_next_ball(x, direction=direction)
                    self.seek_direction = direction if steps == 2 else None
            else:
                logger.info("No balls found, seeking")
                self.seek(direction=self.seek_direction)

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
        if self.saving_images:
            img = cv2.cvtColor(imrange, cv2.COLOR_GRAY2BGR)
            img_name = "%dvisitingmask.jpg" % (self.i)
            cv2.imwrite(img_name, img)
            img = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
            img_name = "%dvisitingimg.jpg" % (self.i)
            cv2.imwrite(img_name, img)
            self.i += 1
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
            image = image[80:205, 0:320]
            img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frame = pygame.surfarray.make_surface(cv2.flip(img, 1))
            screen.fill([0, 0, 0])
            font = pygame.font.Font(None, 24)
            screen.blit(frame, (0, 0))
            image = cv2.medianBlur(image, 5)
            # Convert the image from 'BGR' to HSV colour space
            image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            if self.tracking:
                self.mode[self.mode_number](image)
            else:
                pygame.display.update()


    # TODO: Move this motor control logic out of the stream processor
    # as it is challenge logic, not stream processor logic
    # (the clue is that the streamprocessor needs a drivetrain)

    # Set the motor speed from the ball position
    def drive_toward_ball(self, ball, targetcolour):
        turn = 0.0
        if ball:
            x, y, area, width  = ball
            if (width > self.MAX_WIDTH or y > self.MAX_HEIGHT) and area > self.MAX_AREA:
                self.drive.move(0, -self.AT_BALL_BRAKING)
                self.found = True
                logger.info('Close enough to %s ball, stopping. width: %s, height: %s, area: %s' % (targetcolour, width, y, area))
                time.sleep(0.3)
                BACK_OFF_TIME = 0.2
                self.time_out = time.clock() + BACK_OFF_TIME
            else:
                # follow 0.2, /2 good
                w_error = self.MAX_WIDTH - width
                forward = self.WIDTH_P * w_error + 0.18
                t_error  = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error + self.AIM_OFFSET
                if self.last_t_error is not None:
                    #if there was a real error last time then do some damping
                    turn -= self.TURN_D *(self.last_t_error - t_error)
                    if area > self.MAX_AREA: forward -= self.WIDTH_D * (self.last_w_error - w_error)
                if self.DRIVING and self.tracking:
                    self.drive.move(turn, forward)
                self.last_t_error = t_error
                self.last_w_error = w_error
                logger.info ('%s ball found, error:, %s, width: %s, height: %s' % (targetcolour, t_error, width, y))
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
        turn = 0.0
        if ball:
            x = ball[0]
            area = ball[2]
            if area < self.BACK_OFF_AREA and time.clock() > self.time_out:
                if self.tracking: self.drive.move(0, self.BACK_OFF_BRAKING)
                time.sleep(0.1)
                self.drive.move(0, 0)
                self.retreated = True
                logger.info('far enough away from %s, stopping. area: %s' % (targetcolour, area))
                self.mode_number = 1
            else:
                forward = self.BACK_OFF_SPEED
                t_error = (self.image_centre_x - x) / self.image_centre_x
                turn = self.TURN_P * t_error + self.AIM_OFFSET
                if self.last_t_error is not None:
                    turn -= self.TURN_D *(self.last_t_error - t_error)
                if self.DRIVING and self.tracking:
                    self.drive.move(turn, forward)
                self.last_t_error = t_error
        else:
            # ball lost
            if time.clock() > self.time_out:
                if self.tracking: self.drive.move(0, self.BACK_OFF_BRAKING)
                time.sleep(0.1)
                self.drive.move(0, 0)
                self.retreated = True
                logger.info('far enough away from %s (timed_out), stopping' % (targetcolour))
                self.mode_number = 1
            else:
                self.lost_time = time.clock()
                if self.tracking: self.drive.move(0, self.BACK_OFF_SPEED)
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
            logger.info("finished, resetting parameters to run again")
            self.processor.found = False
            self.processor.retreated = False
            self.drive.move(0,0)
            self.processor.tracking = False
            self.processor.colour = "red"
            self.processor.current_position = 0
            self.processor.colour_seen = None

            if self.processor.learning_failed:
                self.processor.learning_failed = False
                self.restart = False
                self.processor.mode_number = 0
                self.processor.colour_positions = OrderedDict([(key, None) for key in self.processor.running_order])
            else:
                self.processor.mode_number = 1
                self.processor.restart = True
            

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

