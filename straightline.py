from img_base_class import *
import cv2.aruco as aruco

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, screen=None, camera=None, drive=None, dict=None):
        super(StreamProcessor, self).__init__()
        self.camera = camera
        image_width, image_height = self.camera.resolution
        self.image_centre_x = image_width / 2.0
        self.image_centre_y = image_height / 2.0
        self.drive = drive
        self.drive.__init__()
        self.drive.should_normalise_motor_speed = False
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.small_dict = dict 
        self.last_t_error = 0
        self.TURN_P = 4
        self.TURN_D = 2
        self.AIM_P = 1
        self.AIM_D = 0.5
        self.LINE_TURN_P = 4
        self.LINE_TURN_D = 2
        self.STRAIGHT_SPEED = 1
        self.MAX_TURN_SPEED = 0.6
        self.STEERING_OFFSET = -0.2  #more positive make it turn left
        self.CROP_WIDTH = 200
        self.CROP_BOTTOM = 170
        self.CROP_TOP = 300
        self.LINE_CROP_LEFT = 0
        self.LINE_CROP_RIGHT = 320
        self.LINE_CROP_BOTTOM = 30
        self.LINE_CROP_TOP = 55
        self.ribbon_pos = 0
        self.i = 0
        self.TIMEOUT = 8
        self.START_TIME = time.clock()
        self.END_TIME = self.START_TIME + self.TIMEOUT
        self.m_found = False
        self.l_found = False
        self.TURN_TARGET = 5
        self.MARKER_STOP_WIDTH = 70
        self.loop_start_time=0
        self.target_aruco_marker_id = 3
        self.marker_to_track=0
        self.ribbon_colour = ((0, 0, 100), (180, 55, 255))
        self.MIN_CONTOUR_AREA = 30
        self.driving = False
        self.aiming = False
        self.finished = False
        logger.info("setup complete, looking")
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

    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        screen.fill([0,0,0])
        if self.target_aruco_marker_id >= self.TURN_TARGET:
           logger.info("finished!")
           self.finished = True
        frame = image[self.CROP_BOTTOM:self.CROP_TOP, (self.image_centre_x - self.CROP_WIDTH/2):(self.image_centre_x + self.CROP_WIDTH/2)]
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        parameters =  aruco.DetectorParameters_create()
        #lists of ids and the corners beloning to each id
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, self.small_dict, parameters=parameters)
        if ids != None:
            if len(ids) > 1:
                logger.info( "found %d markers" % len(ids))
                self.marker_to_track = 0
                for marker_number in range(0, len(ids)):
                    # test the found aruco object is equivalent to the id of the one we're looking for
                    if ids[marker_number] == self.target_aruco_marker_id:
                        self.marker_to_track = marker_number
                logger.info ("marker I'm looking for, is number %d" % self.marker_to_track)
            else:
                self.marker_to_track = 0
            if ids[self.marker_to_track][0] == self.target_aruco_marker_id:
                m = self.marker_to_track
                self.m_found = True
                #if found, compute the centre and move the cursor there
                found_y = sum([arr[0] for arr in corners[m][0]])  / 4
                found_x = sum([arr[1] for arr in corners[m][0]])  / 4
                width = abs(corners[m][0][0][0]-corners[m][0][1][0]+corners[m][0][3][0]-corners[m][0][2][0])/2
                logger.info('marker width %s' % width)
                if width > self.MARKER_STOP_WIDTH:
                    logger.info('finished!')
                    self.drive.move(0,0)
                    self.finished = True
                pygame.mouse.set_pos(int(found_x)+self.LINE_CROP_TOP, int(self.CROP_WIDTH-found_y))
                self.t_error = (self.CROP_WIDTH/2 - found_y) / (self.CROP_WIDTH / 2)
                turn = self.STEERING_OFFSET + self.TURN_P * self.t_error
                if self.last_t_error is not 0:
                    #if there was a real error last time then do some damping
                    turn -= self.TURN_D *(self.last_t_error - self.t_error)
                turn = min(max(turn,-self.MAX_TURN_SPEED), self.MAX_TURN_SPEED)
                #if we're rate limiting the turn_amount, go slow
                # TODO Rate limit the speed change
                if self.driving:
                    self.drive.move(turn, self.STRAIGHT_SPEED)
                elif self.aiming:
                    self.drive.move(turn, 0)
                self.last_t_error = self.t_error
            else:
                if self.driving:
                    self.stop_and_wait()
        else:
            logger.info("no marker, looking for ribbon")
            self.m_found = False
            cropped_image = cv2.pyrDown(image, dstsize=(int(self.image_centre_x), int(self.image_centre_y)))
            cropped_image = cropped_image[self.LINE_CROP_BOTTOM:self.LINE_CROP_TOP, self.LINE_CROP_LEFT:self.LINE_CROP_RIGHT]
            img = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)
            ribbon_frame = pygame.surfarray.make_surface(cv2.flip(img, 1))
            screen.blit(ribbon_frame, (0, 0))
            blur_image = cv2.medianBlur(cropped_image, 3)
            blur_image = cv2.cvtColor(blur_image, cv2.COLOR_RGB2HSV)
            ribbon_mask = threshold_image(blur_image, self.ribbon_colour)
            self.ribbon_following(ribbon_mask)
            
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(cv2.flip(frame,1))
        screen.blit(frame, (self.LINE_CROP_TOP,0))
        pygame.display.update()
        m_found_identifier = "mF" if self.m_found else "NmF"
        l_found_identifier = "lF" if self.l_found else "NlF"
        img_name = "%d%s%s%dimg.jpg" % (self.i, m_found_identifier, l_found_identifier, self.ribbon_pos)
        # filesave for debugging: 
#        if self.driving:
#            cv2.imwrite(img_name, image)
        self.i += 1

    def ribbon_following(self, ribbon_image):
        ribbon_x, ribbon_y, ribbon_area, ribbon_contour = find_largest_contour(ribbon_image)
        if ribbon_area > self.MIN_CONTOUR_AREA:
            ribbon = [ribbon_x, ribbon_y, ribbon_area, ribbon_contour]
            self.l_found = True
            self.ribbon_pos = ribbon_x
        else:
            ribbon = None
            self.l_found = False
            self.ribbon_pos = 0
        crop_width = self.LINE_CROP_RIGHT - self.LINE_CROP_LEFT
        pygame.mouse.set_pos(int(ribbon_y), int(crop_width - ribbon_x))
        self.follow_ribbon(ribbon, self.STRAIGHT_SPEED)

    def follow_ribbon(self, ribbon, speed):
        turn = 0.0
        if ribbon is not None:
            x = ribbon[0]
            logger.info ("ribbon spotted at %i" % (x))
            image_centre_x = (self.LINE_CROP_RIGHT - self.LINE_CROP_LEFT)/2
            t_error  = float(image_centre_x - x) / image_centre_x
            if self.aiming:
                turn = self.AIM_P * t_error
            else:
                turn = self.LINE_TURN_P * t_error
            turn = min(max(turn,-self.MAX_TURN_SPEED), self.MAX_TURN_SPEED)
            if self.last_t_error is not None:
                #if there was a real error last time then do some damping
                if self.aiming:
                    turn -= self.LINE_TURN_D *(self.last_t_error - t_error)
                else:
                    turn -= self.AIM_D *(self.last_t_error - t_error)
            if self.driving:
                self.drive.move(turn, self.STRAIGHT_SPEED)
            elif self.aiming:
                self.drive.move(turn, 0)
            self.last_t_error = t_error
        else:
            self.last_t_error = None
            logger.info('No ribbon either')
            if self.driving:
                self.stop_and_wait()


    def stop_and_wait(self):
        self.drive.move(0, self.STRAIGHT_SPEED)
        self.found = False
        self.last_t_error = None


class StraightLineSpeed(BaseChallenge):
    """Minimal StraightLineSpeed challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None, markers=None):
        self.image_width = 640  # Camera image width
        self.image_height = 480  # Camera image height
        self.frame_rate = 30  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.joystick = joystick
        self.dict = markers
        super(StraightLineSpeed, self).__init__(name='StraightLineSpeed', timeout=timeout, logger=logger)

    def joystick_handler(self, button):
        if button['r1']:
            print "Exiting"
            self.timeout = 0
        if button['r2']:
            self.processor.driving = True
            print "Starting"
        if button['l1']:
            self.processor.driving = False
            self.processor.aiming = False
            self.drive.move(0,0)
            print "Stopping"
        if button['l2']:
            self.processor.driving = False
            self.processor.aiming = True
            print ("Aiming")

    def run(self):
        # Startup sequence
        logger.info('Setting up camera')
        screen = pygame.display.get_surface()
        self.camera = picamera.PiCamera()
        self.camera.resolution = (self.image_width, self.image_height)
        self.camera.framerate = self.frame_rate
        self.camera.iso = 800
        self.camera.shutter_speed = 8000
        time.sleep(0.2)
        logger.info('Setup the stream processing thread')
        # TODO: Remove dependency on drivetrain from StreamProcessor
        self.processor = StreamProcessor(
            screen=self.screen,
            camera=self.camera,
            drive=self.drive,
            dict=self.dict
        )
        logger.info('Setting up image capture thread')
        self.image_capture_thread = ImageCapture(
            camera=self.camera,
            processor=self.processor
        )
        pygame.mouse.set_visible(True)
        try:
            while not self.should_die:
                time.sleep(0.1)
                if self.joystick.connected:
                    self.joystick_handler(self.joystick.check_presses())
                if self.processor.finished:
                    self.stop()

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
