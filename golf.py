from img_base_class import *
import cv2.aruco as aruco
import math
from approxeng.input.selectbinder import ControllerResource

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen=None, camera=None, drive=None, dict=None):
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
        self.small_dict = dict
        self.DRIVING = True
        self.TURN_TIME = 0.025
        self.TURN_SPEED = 0.8
        self.SETTLE_TIME = 0.05
        self.MIN_BALL_SIZE = 100
        self.TURN_AREA = 5000  #6000 turns right at edge, 9000 too high
        self.TURN_HEIGHT = 16
        self.BACK_AWAY_START = 2000
        self.BACK_AWAY_STOP = 1500
        self.BACK_AWAY_HEIGHT = 5
        self.back_away = False
        self.edge = False
        self.BLUR = 3
        self.colour_limits = ((0, 0, 50), (180, 150, 255))
        self.FLOOR_LIMITS  = ((82, 200, 50), (90, 255, 130))
        self.calibrating = False
        self.tracking = False
        self.last_t_error = 0
        self.ACQUIRE_SPEED = 0.25
        self.STRAIGHT_SPEED = 0.5
        self.STEADY_SPEED =0.4
        self.BALL_S_P = 0.1 * self.STRAIGHT_SPEED
        self.BALL_T_P = 0.02 * self.STRAIGHT_SPEED
        self.BALL_D = 0.002 * self.STRAIGHT_SPEED
        self.BALL_POS_TOL = 8
        self.TARGET_BALL_POS_X = 100
        self.TARGET_BALL_POS_Y = 9
        self.recent_ball_error = None
        self.MAX_CAPTURED_BALL_ERROR = 8
        self.TURN_P = 2 * self.STRAIGHT_SPEED
        self.TURN_D = 1 * self.STRAIGHT_SPEED
        self.SLIGHT_TURN = 0.1
        self.MAX_TURN_SPEED = 0.6
        self.SEEK_TURN_SPEED = 1
        self.CORNER_ONE_ID = 1
        self.CORNER_ONE_STOP_WIDTH = 35
        self.CORNER_TWO_ID = 2
        self.CORNER_TWO_STOP_WIDTH = 47
        self.WINDMILL_CENTRE_ID = 3
        self.CENTRE_STOP_WIDTH = 30
        self.WINDMILL_BLADE_ID = 4
        self.WINDMILL_GAP_ID = 5
        self.BLADE_AND_GAP_WIDTH = 0.042
        self.GAP_STOP_WIDTH = 34
        self.GO_FOR_IT_POSITION = 70
        self.DONT_GO_POSITION = 180
        self.MARKER_RATIO = 3.2 #ratio of radius of periemter markers on disk to marker size
        self.STEERING_OFFSET = 0.0  #more positive make it turn left
        self.BALL_CROP_START = 0
        self.BALL_CROP_WIDTH = 200
        self.BALL_CROP_HEIGHT = 50
        self.FLOOR_CROP_WIDTH = 320
        self.FLOOR_CROP_START = 0
        self.FLOOR_CROP_HEIGHT = 140
        self.acquiring_ball = True
        self.first_acquired = None
        self.moving_to_corner_one= False
        self.moving_to_corner_two= False
        self.moving_to_windmill = False
        self.moving_to_entrance = False
        self.putting = False
        self.TIMEOUT = 30.0
        self.PARAM = 60
        self.START_TIME = time.clock()
        self.END_TIME = self.START_TIME + self.TIMEOUT
        self.found = False
        self.just_turned = False
        self.finished = False
        self.i = 0
        logger.info("setup complete, looking")
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

    def acquire_ball(self, ball_range):
        ACQUIRING_TIMEOUT = 1
        ball_x, ball_y, ball_a = self.find_largest_contour(ball_range)
        if ball_a is not None:
            pygame.mouse.set_pos(ball_y, 0.5 * self.BALL_CROP_WIDTH + 0.5 * self.FLOOR_CROP_WIDTH - ball_x)
        if ball_a > self.MIN_BALL_SIZE:
            #opponent is disrupting countour shape, making it concave
            self.found = True
            t_error = self.TARGET_BALL_POS_X - ball_x
            turn = self.BALL_T_P * t_error
            s_error = ball_y - self.TARGET_BALL_POS_Y
            speed = self.BALL_S_P * s_error
            #constrain speeds
            speed = max(-self.ACQUIRE_SPEED, min(self.ACQUIRE_SPEED, speed))
            turn = max(-self.ACQUIRE_SPEED, min(self.ACQUIRE_SPEED, turn))
            if max(abs(s_error),abs(t_error)) < self.BALL_POS_TOL:
                print "stopping, ball found and within tolerance, making ring drop"
                if self.first_acquired is None: self.first_acquired = time.clock()
                self.drive.move(0,-self.ACQUIRE_SPEED/2)
            else:
                print ("found ball: position %d, %d, area %d" % (ball_x, ball_y, ball_a))
                if self.DRIVING and self.tracking:
                    self.drive.move(turn, speed)
            #update log of how close we've been to the ball recently
            if self.recent_ball_error==None:
                self.recent_ball_error=s_error
            else:
                self.recent_ball_error = 0.95 * self.recent_ball_error + 0.05 * abs(s_error)
            if (self.recent_ball_error < self.MAX_CAPTURED_BALL_ERROR) and self.first_acquired and ((self.first_acquired + ACQUIRING_TIMEOUT) < time.clock()):
                #we've probably capture the ball, stop and move to next segment
                print "ball captured"
                self.drive.move(0,0)
                self.acquiring_ball = False
                self.moving_to_corner_one = True
        else:
            if self.tracking: self.drive.move(0,-self.ACQUIRE_SPEED/2)
            print "nothing large enough to be a ball found"     

    def drive_to_corner_one(self, image):
        if self.drive_to_marker(image, self.CORNER_ONE_ID, self.CORNER_ONE_STOP_WIDTH):
            logger.info("at marker one")
            self.moving_to_corner_one = False
            self.moving_to_corner_two = True

    def drive_to_corner_two(self, image):
        if self.drive_to_marker(image, self.CORNER_TWO_ID, self.CORNER_TWO_STOP_WIDTH):
            logger.info("at marker two")
            self.moving_to_corner_two = False
            self.moving_to_windmill = True

    def drive_to_windmill(self, image):
        if self.drive_to_marker(image, self.WINDMILL_CENTRE_ID, self.CENTRE_STOP_WIDTH):
            logger.info("at windmill")
            self.moving_to_windmill = False
            self.moving_to_entrance = True

    def drive_to_marker(self, image, marker_number, stop_width):
        appraoched = False
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        parameters =  aruco.DetectorParameters_create()
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, self.small_dict, parameters=parameters)
        if ids != None:
            if len(ids) == 1:
                marker_index = 0
            else:
                marker_index = 0
                for marker_number in range(0, len(ids)):
                    # test the found aruco object is equivalent to the id of the one we're looking for
                    if ids[marker_number] == marker_number:
                        marker_index = marker_number
            #if found, comptue the centre and move the cursor there
            if ids[marker_index] == marker_number:
                m = marker_index
                found_y = sum([arr[0] for arr in corners[m][0]])  / 4
                found_x = sum([arr[1] for arr in corners[m][0]])  / 4
                width = math.sqrt(math.pow(corners[m][0][0][0]-corners[m][0][1][0],2)+math.pow(corners[m][0][0][1]-corners[m][0][1][1],2))
                pygame.mouse.set_pos(int(found_x), int(found_y))
                t_error = (self.image_width/2 - found_x) / (self.image_width / 2)
                turn =  - self.TURN_P * t_error
                print ("approaching marker %d" % width)
                pygame.mouse.set_pos(int(found_x), int(self.image_width-found_y))
                if width > stop_width:
                    print ("at marker %s", marker_number)
                    self.drive.move(0,0)
                    approached= True
                else:
                    self.t_error = (self.image_width/2 - found_y) / (self.image_width / 2)
                    turn_amount = self.STEERING_OFFSET + self.TURN_P * self.t_error
                    turn_amount = min(max(turn_amount,-self.MAX_TURN_SPEED), self.MAX_TURN_SPEED)
                    if self.tracking: self.drive.move(turn_amount, self.STRAIGHT_SPEED)
                    approached = False
                self.just_turned = False
            else:
                print ("markers found but not the right one (%s)", marker_number)
                self.drive.move(self.SEEK_TURN_SPEED,0)
                time.sleep(0.05)
                self.just_turned = True
                last_t_error = 0
                approached = False
        else:
            print ("no markers found, looking for %s", marker_number)
            self.drive.move(self.SEEK_TURN_SPEED,0)
            time.sleep(0.05)
            self.just_turned = True
            last_t_error = 0 
            approached = False
        return approached

    def move_to_entrance(self,image):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        parameters =  aruco.DetectorParameters_create()
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, self.small_dict, parameters=parameters)
        if ids != None:
            found_x_sum = 0
            for marker_number in range(0, len(ids)):
                if ids[marker_number] == self.WINDMILL_CENTRE_ID:
                    found_x_sum += sum([arr[0] for arr in corners[marker_number][0]])  / 4
                    #print ("%i, %i, %i" % (ids[marker_number], sum([arr[1] for arr in corners[marker_number][0]])  / 4,sum([arr[0] for arr in corners[marker_number][0]])  / 4))
                else:
                    dy, dx = marker_vector(corners[marker_number][0])
                    x = sum([arr[0] for arr in corners[marker_number][0]])/4 - dy * self.MARKER_RATIO
                    found_x_sum += x
                    #print ("%i, %i, %i, %i, %i, %i" % (ids[marker_number], dx, dy, sum([arr[1] for arr in corners[marker_number][0]])  / 4,sum([arr[0] for arr in corners[marker_number][0]])  / 4,x))
            found_x = found_x_sum / len(ids)
            #if found, compute the centre and move the cursor there
            width = math.sqrt(math.pow(corners[0][0][0][0]-corners[0][0][1][0],2)+math.pow(corners[0][0][0][1]-corners[0][0][1][1],2))
            t_error = (self.image_width/2 - found_x) / (self.image_width / 2)
            turn =  - self.TURN_P * t_error
            print ("approaching entrance %d" % width)
            if width > self.GAP_STOP_WIDTH:
                if t_error < 0.15:
                    print 'at entrance!'
                    self.drive.move(0,0)
                    self.moving_to_entrance = False
                    self.putting = True
                else:
                    self.t_error = (self.image_width/2 - found_x) / (self.image_width / 2)
                    turn_amount = self.STEERING_OFFSET + self.TURN_P * self.t_error
                    turn_amount = min(max(turn_amount,-self.MAX_TURN_SPEED), self.MAX_TURN_SPEED)
                    if self.tracking: self.drive.move (0, -self.STEADY_SPEED)
            else:
                self.t_error = (self.image_width/2 - found_x) / (self.image_width / 2)
                turn_amount = self.STEERING_OFFSET + self.TURN_P * self.t_error
                turn_amount = min(max(turn_amount,-self.MAX_TURN_SPEED), self.MAX_TURN_SPEED)
                if self.tracking: self.drive.move (turn_amount, self.STEADY_SPEED)
        else:
            self.drive.move(0,-self.STRAIGHT_SPEED)

    def putt(self,image):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        parameters =  aruco.DetectorParameters_create()
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, self.small_dict, parameters=parameters)
        if ids != None:
            gap_x = 0
            for marker_number in range(0, len(ids)):
                if ids[marker_number] == self.WINDMILL_GAP_ID:
                    gap_x = sum([arr[0] for arr in corners[marker_number][0]])  / 4
            print("waiting to lunge, position currently: %s" % gap_x)
            if gap_x > self.GO_FOR_IT_POSITION and gap_x < self.DONT_GO_POSITION and self.tracking:
                #if we're in the right postion, lunge forward, then back, then go back to lining up with the gap
                self.drive.move(0, self.STRAIGHT_SPEED)
                time.sleep(2) #was 1.2
              #  self.drive.move(0,-self.STRAIGHT_SPEED)
              #  time.sleep(1.3)
                self.drive.move(0,0)
              #  self.moving_to_entrance = True
              #  self.putting = False
        else:
            self.drive.move(0,-self.STEADY_SPEED)
  
            

    def process_image(self, image, screen):
        if self.just_turned:
            self.just_turned = False
            self.drive.move(0,0)
        else:
            screen = pygame.display.get_surface()
            HSVimage = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            ball_image = HSVimage[self.BALL_CROP_START:self.BALL_CROP_HEIGHT, (self.image_centre_x - self.BALL_CROP_WIDTH/2):(self.image_centre_x + self.BALL_CROP_WIDTH/2)]
            floor_image = HSVimage[self.FLOOR_CROP_START:self.FLOOR_CROP_HEIGHT, (self.image_centre_x - self.FLOOR_CROP_WIDTH/2):(self.image_centre_x + self.FLOOR_CROP_WIDTH/2)]
            HSVimage=HSVimage[self.FLOOR_CROP_START:self.image_height, 0:self.image_width]
            #for floor calibration:        print cv2.meanStdDev(floor_image)
            # Our operations on the frame come here
            screenimage = cv2.cvtColor(HSVimage, cv2.COLOR_HSV2BGR)
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
            if self.acquiring_ball: self.acquire_ball(ball_range)
            if self.moving_to_corner_one: self.drive_to_corner_one(image)
            if self.moving_to_corner_two: self.drive_to_corner_two(image)
            if self.moving_to_windmill: self.drive_to_windmill(image)
            if self.moving_to_entrance: self.move_to_entrance(image)
            if self.putting: self.putt(image)
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

    def __init__(self, timeout=120, screen=None, joystick=None, markers=None):
        self.image_width = 320  # Camera image width
        self.image_height = 256  # Camera image height
        self.frame_rate = 40  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.exponential = 2
        self.joystick=joystick
        self.markers=markers
        super(Golf, self).__init__(name='Golf', timeout=timeout, logger=logger)

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def exp(self, demand, exp):
        # function takes a demand speed from -1 to 1 and converts it to a response value
        # with an exponential function. exponential is -inf to +inf, 0 is linear
        exp = 1/(1 + abs(exp)) if exp < 0 else exp + 1
        return math.copysign((abs(demand)**exp), demand)

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
        self.camera.shutter_speed = 2000
        logger.info('Setup the stream processing thread')
        # TODO: Remove dependency on drivetrain from StreamProcessor
        self.processor = StreamProcessor(
            screen=self.screen,
            camera=self.camera,
            drive=self.drive,
            dict=self.markers
        )
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
                    self.stop()
                if not self.processor.tracking:
                    rx, ry = self.joystick['rx', 'ry']
                    logger.debug("joystick L/R: %s, %s" % (rx, ry))
                    rx = self.exp(rx, self.exponential)
                    ry = self.exp(ry, self.exponential)
                    self.drive.move(rx, ry)

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
