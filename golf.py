from img_base_class import *
import cv2.aruco as aruco
from approxeng.input.selectbinder import ControllerResource

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen=None, camera=None, drive=None):
        super(StreamProcessor, self).__init__()
        self.camera = camera
        self.image_width, self.image_height = self.camera.resolution
        self.image_centre_x = self.image_width / 2.0
        self.image_centre_y = self.image_height / 2.0
        self.drive = drive
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.DRIVING = True
        self.TURN_TIME = 0.025
        self.TURN_SPEED = 0.8
        self.SETTLE_TIME = 0.05
        self.MIN_BALLOON_SIZE = 50
        self.TURN_AREA = 5000  #6000 turns right at edge, 9000 too high
        self.TURN_HEIGHT = 16
        self.BACK_AWAY_START = 2000
        self.BACK_AWAY_STOP = 1500
        self.BACK_AWAY_HEIGHT = 5
        self.back_away = False
        self.edge = False
        self.BLUR = 3
        self.colour_limits = ((90, 20, 50), (95, 200, 255))
        self.FLOOR_LIMITS  = ((82, 200, 50), (90, 255, 130))
        self.calibrating = False
        self.tracking = False
        self.last_t_error = 0
        self.STRAIGHT_SPEED = 0.2
        self.BALL_S_P = 0.1 * self.STRAIGHT_SPEED
        self.BALL_T_P = 0.02 * self.STRAIGHT_SPEED
        self.BALL_D = 0.002 * self.STRAIGHT_SPEED
        self.BALL_POS_TOL = 2
        self.TARGET_BALL_POS_X = 50
        self.TARGET_BALL_POS_Y = 10
        self.TURN_P = 2 * self.STRAIGHT_SPEED
        self.TURN_D = 1 * self.STRAIGHT_SPEED
        self.SLIGHT_TURN = 0.1
        self.STEERING_OFFSET = 0.0  #more positive make it turn left
        self.BALL_CROP_START = 0
        self.BALL_CROP_WIDTH = 100
        self.BALL_CROP_HEIGHT = 55
        self.FLOOR_CROP_WIDTH = 160
        self.FLOOR_CROP_START = 0
        self.FLOOR_CROP_HEIGHT = 70
        self.acquiring_ball = True
        self.moving_to_corner_one= False
        self.moving_to_corner_two= False
        self.moving_to_windmill = False
        self.putting = False
        self.TIMEOUT = 30.0
        self.PARAM = 60
        self.START_TIME = time.clock()
        self.END_TIME = self.START_TIME + self.TIMEOUT
        self.found = False
        self.finished = False
        self.i = 0
        logger.info("setup complete, looking")
        time.sleep(1)
        self.endtime=time.time()
        self.start()

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

    def threshold_image(self, image, limits):
        '''function to find what parts of an image liue within limits.
        returns the parts of the original image within the limits, and the mask'''
        hsv_lower, hsv_upper = limits
       
        mask = cv2.inRange(
            image,
            numpy.array(hsv_lower),
            numpy.array(hsv_upper)
        )
        return mask

    def get_limits(self, image, sigmas):
        """function to use the mean and standard deviation of an images
        channels to create suggested threshold limits based on number of
        'sigmas' (usually less than three). returns a tuple of tuples
        ((low1, low2, low3),(upp1, upp2, upp3))"""
        mean, stddev = cv2.meanStdDev(image)
        lower = mean - sigmas * stddev
        upper = mean + sigmas * stddev
        return ((lower[0][0], lower[1][0], lower[2][0]), (upper[0][0], upper[1][0], upper[2][0]))

    def seek(self):
        self.drive.move(self.TURN_SPEED, 0)
        time.sleep(self.TURN_TIME)
        self.drive.move(0,0)
        time.sleep(self.SETTLE_TIME)
    
    def show_cal_label(self, screen):
        font = pygame.font.Font(None, 60)
        label = font.render(str("Calibrating"), 1, (255,255,255))
        screen.blit(label, (10, 200))
        self.drive.move(0,0)

    def show_tracking_label(self, screen):
        font = pygame.font.Font(None, 60)
        label = font.render(str("Golfing!"), 1, (255,255,255))
        screen.blit(label, (10, 200))

    def find_largest_contour(self,image):
        '''takes a binary image and returns coordinates and size of largest contour'''
        contourimage, contours, hierarchy = cv2.findContours(
            image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        # Go through each contour
        found_area = 1
        found_x = -1
        found_y = -1
        biggest_contour = None
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            aspect_ratio = float(h)/w
            if found_area < area:
                found_area = area
                M = cv2.moments(contour)
                found_x = int(M['m10']/M['m00'])
                found_y = int(M['m01']/M['m00'])
                biggest_contour = contour
        return found_x, found_y, found_area

    def aquire_ball(self, ball_range):
            balloon_x, balloon_y, balloon_a = self.find_largest_contour(ball_range)
            if balloon_a is not None:
                pygame.mouse.set_pos(balloon_y, 0.5 * self.BALL_CROP_WIDTH + 0.5 * self.FLOOR_CROP_WIDTH - balloon_x)
            if balloon_a > self.MIN_BALLOON_SIZE:
                #opponent is disrupting countour shape, making it concave
                self.found = True
                t_error = self.TARGET_BALL_POS_X - balloon_x
                turn = self.BALL_T_P * t_error
                s_error = balloon_y - self.TARGET_BALL_POS_Y
                print s_error
                speed = self.BALL_S_P * s_error
                #constrain speeds
                speed = max(-self.STRAIGHT_SPEED, min(self.STRAIGHT_SPEED, speed))
                turn = max(-self.STRAIGHT_SPEED, min(self.STRAIGHT_SPEED, turn))
                if max(abs(s_error),abs(t_error)) < self.BALL_POS_TOL:
                    print "stopping, ball found and within tolerance"
                    self.drive.move(0,0)
                else:
                    print ("found ball: position %d, %d, area %d" % (balloon_x, balloon_y, balloon_a))
                    if self.DRIVING and self.tracking:
                        self.drive.move(turn, speed)
            else:
                self.drive.move(0,0)
                print "nothing large enough to be a ball found"
        else:
            self.drive.move(0,0)
            print "No Ball found"

    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        ball_image = image[self.BALL_CROP_START:self.BALL_CROP_HEIGHT, (self.image_centre_x - self.BALL_CROP_WIDTH/2):(self.image_centre_x + self.BALL_CROP_WIDTH/2)]
        floor_image = image[self.FLOOR_CROP_START:self.FLOOR_CROP_HEIGHT, (self.image_centre_x - self.FLOOR_CROP_WIDTH/2):(self.image_centre_x + self.FLOOR_CROP_WIDTH/2)]
        image=image[self.FLOOR_CROP_START:self.image_height, 0:self.image_width]
        #for floor calibration:        print cv2.meanStdDev(floor_image)
        # Our operations on the frame come here
        screenimage = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        frame = pygame.surfarray.make_surface(cv2.flip(screenimage, 1))
        screen.fill([0, 0, 0])
        screen.blit(frame, (0, 0))
        if self.calibrating:
            print "calibrating"
            self.show_cal_label(screen)
            self.colour_limits = self.get_limits(ball_image, 1.5)
            print self.colour_limits
        if self.tracking:
            self.show_tracking_label(screen)
        ball_range = self.threshold_image(ball_image, self.colour_limits)
        floor_range =  self.threshold_image(floor_image, self.FLOOR_LIMITS)
        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        frame = pygame.surfarray.make_surface(cv2.flip(floor_range, 1))
        screen.blit(frame, (self.image_height-self.FLOOR_CROP_START, 0))
        frame = pygame.surfarray.make_surface(cv2.flip(ball_range, 1))
        screen.blit(frame, (self.image_height-self.FLOOR_CROP_START + self.FLOOR_CROP_HEIGHT, 0))
        pygame.display.update()
        #todo: move all ball only related stuff into acquire ball
        self.acquire_ball(ball_range) if self.acquiring_ball else pass
        #rodo: add other move functions
        if self.tracking:
            image = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
            if self.found:
                img_name = str(self.i) + "Fimg.jpg"
            else:
                img_name = str(self.i) + "NFimg.jpg"
            #filesave for debugging: 
            #cv2.imwrite(img_name, image)
            self.i += 1
        #print 1/(time.time()-self.endtime)
        #self.endtime=time.time()



class Golf(BaseChallenge):
    """Golf challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 160  # Camera image width
        self.image_height = 128  # Camera image height
        self.frame_rate = 40  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.joystick=joystick
        super(Golf, self).__init__(name='Golf', timeout=timeout, logger=logger)

    def joystick_handler(self, button):
        if button['r1']:
            self.processor.finished = True
        if button['r2']:
            self.processor.tracking = True
            self.processor.calibrating = False
            print "Tracking"
        if button['l1']:
            self.processor.tracking = False
            self.processor.calibrating = False
            self.drive.move(0,0)
            print "finished calibrating or stopping tracking"
        if button['l2']:
            self.processor.tracking = False
            self.processor.calibrating = True
            print "calibrating"

    def run(self):
        # Startup sequence
        logger.info('Setting up camera')
        screen = pygame.display.get_surface()
        self.camera = picamera.PiCamera()
        self.camera.resolution = (self.image_width, self.image_height)
        self.camera.framerate = self.frame_rate
        self.camera.iso = 800
        self.camera.awb_mode = 'off'
        self.camera.awb_gains = (1.149, 2.193)
        self.camera.shutter_speed = 12000
        logger.info('Setup the stream processing thread')
        # TODO: Remove dependency on drivetrain from StreamProcessor
        self.processor = StreamProcessor(
            screen=self.screen,
            camera=self.camera,
            drive=self.drive,
        )
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
                if self.joystick.connected:
                    self.joystick_handler(self.joystick.check_presses())
                if self.processor.finished:
                    self.timeout = 0

        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            self.logger.info("killed from keyboard")
            self.drive.move(0,0)
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
