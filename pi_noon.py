from img_base_class import *
import cv2.aruco as aruco

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen=None, camera=None, drive=None):
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
        self.MIN_CONTOUR_AREA = 1000
        self.last_t_error = 0
        self.TURN_P = 0.6
        self.TURN_D = 0.3
        self.STRAIGHT_SPEED = 0.5
        self.STEERING_OFFSET = 0.0  #more positive make it turn left
        self.CROP_WIDTH = 160
        self.TIMEOUT = 30.0
        self.START_TIME = time.clock()
        self.END_TIME = self.START_TIME + self.TIMEOUT
        self.found = False
        self.finished = False
        self.i = 0
        logger.info("setup complete, looking")
        time.sleep(1)
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

    def find_opponent(self, image, contour, hull):
        '''function to find the centre of the convex portion of a contour'''
        mask = numpy.zeros(image.shape,numpy.uint8)
        cv2.drawContours(mask,[hull],0,255,-1)
        cv2.drawContours(mask,[contour],0,0,-1)
        contourimage, subcontours, hierarchy = cv2.findContours(
            mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        # Go through each contour
        found_area = -1
        found_x = -1
        found_y = -1
        biggest_contour = None
        for subcontour in subcontours:
            x,y, w, h = cv2.boundingRect(subcontour)
            cx = x + (w / 2)
            cy = y + (h / 2)
            area = cv2.contourArea(subcontour)
            if found_area < area:
                found_area = area
                found_x = cx
                found_y = cy
                biggest_contour = subcontour
        return [found_x, found_y]

        
    def turn_right(self):
        self.drive.move(self.NINTY_TURN, 0)
        time.sleep(self.TURN_TIME)
        self.drive.move(0,0)
        time.sleep(self.SETTLE_TIME)
    
    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        frame = image[0:90, (self.image_centre_x - self.CROP_WIDTH/2):(self.image_centre_x + self.CROP_WIDTH/2)]
        # Our operations on the frame come here
        screenimage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = pygame.surfarray.make_surface(cv2.flip(screenimage, 1))
        screen.fill([0, 0, 0])
        screen.blit(frame, (0, 0))
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # We want to extract the 'Hue', or colour, from the image. The 'inRange'
        # method will extract the colour we are interested in (between 0 and 180)
        hsv_lower, hsv_upper = ((100, 90, 40), (140, 255, 200))
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
        biggest_contour = None
        for contour in contours:
            area = cv2.contourArea(contour)
            if found_area < area:
                found_area = area
                biggest_contour = contour
        if found_area > self.MIN_CONTOUR_AREA:
            #arc length of a typical contour is ~400
            smoothed_contour = cv2.approxPolyDP(biggest_contour, 8, True)
            hull = cv2.convexHull(smoothed_contour)
            found_area = cv2.contourArea(smoothed_contour)
            opponent_size = cv2.contourArea(hull) - found_area
            if not cv2.isContourConvex(smoothed_contour):
                print "opponent found, area: %d" % opponent_size
                found_x, found_y = self.find_opponent(imrange, smoothed_contour, hull)
                print ("found coordinates %d, %d" % (found_x, found_y))
                self.found = True
                pygame.mouse.set_pos(found_y, self.CROP_WIDTH - found_x)
            else:
                print "no opponent found, convex red area: %d, opponent area: %d" % (found_area, opponent_size)
        else:
            print "no opponent, no red spotted"
            self.found = False
        if self.found:
         img_name = str(self.i) + "Fimg.jpg"
        else:
         img_name = str(self.i) + "NFimg.jpg"
        #filesave for debugging: 
        #cv2.imwrite(img_name, image)
        self.i += 1



class PiNoon(BaseChallenge):
    """Pi Noon challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 160  # Camera image width
        self.image_height = 120  # Camera image height
        self.frame_rate = 30  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.joystick=joystick
        super(PiNoon, self).__init__(name='PiNoon', timeout=timeout, logger=logger)


    def run(self):
        # Startup sequence
        logger.info('Setting up camera')
        screen = pygame.display.get_surface()
        self.camera = picamera.PiCamera()
        self.camera.resolution = (self.image_width, self.image_height)
        self.camera.framerate = self.frame_rate
        self.camera.iso = 800
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
                time.sleep(0.1)
                if self.processor.finished:
                    self.timeout = 0

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
