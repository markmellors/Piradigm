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
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        # Why the one second sleep?
        #create small cust dictionary
        self.small_dict = dict #aruco.Dictionary_create(6, 3)
        self.last_t_error = 0
        self.TURN_P = 2  #0.9
        self.TURN_D = 0.6 #0.5
        self.drive.__init__()
        self.STRAIGHT_SPEED = 0.8 #was 0.5
        self.STEERING_OFFSET = 0.0  #more positive make it turn left
        self.CROP_WIDTH = 480
        self.i = 0
        self.TIMEOUT = 30.0
        self.START_TIME = time.clock()
        self.END_TIME = self.START_TIME + self.TIMEOUT
        self.found = False
        self.turn_number = 0
        self.TURN_TARGET = 5
        self.TURN_WIDTH = [36, 30, 38, 42, 34, 24] # [32, 27, 34, 33, 27, 24]
        self.NINTY_TURN = 0.8  #0.8 works if going slowly
        self.SETTLE_TIME = 0.05
        self.TURN_TIME = 0.04
        self.MAX_TURN_SPEED = 0.7 #was 0.25
        self.loop_start_time=0
        self.marker_to_track=0
        self.BRAKING_FORCE = 0.1
        self.BRAKE_TIME = 0.05
        self.driving = False
        self.aiming = False
        self.finished = False
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

    def turn_right(self):
        if self.driving:
            self.drive.move(self.NINTY_TURN, 0)
            time.sleep(self.TURN_TIME)
            self.drive.move(0,0)
            time.sleep(self.SETTLE_TIME)
                
    def turn_left(self):
        if self.driving:
            self.drive.move(-self.NINTY_TURN, 0)
            time.sleep(self.TURN_TIME)
            self.drive.move(0,0)
            time.sleep(self.SETTLE_TIME)

    def brake(self):
        self.drive.move(0,-self.BRAKING_FORCE)
        time.sleep(self.BRAKE_TIME)
        self.drive.move(0,0)
    
    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        if self.turn_number >= self.TURN_TARGET:
           logger.info("finished!")
           self.finished = True
        frame = image[75:255, (self.image_centre_x - self.CROP_WIDTH/2):(self.image_centre_x + self.CROP_WIDTH/2)]
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        parameters =  aruco.DetectorParameters_create()
        #lists of ids and the corners beloning to each id
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, self.small_dict, parameters=parameters)
        if ids != None:
            if len(ids)>1:
                logger.info( "found %d markers" % len(ids))
                self.marker_to_track = 0
                for marker_number in range(0, len(ids)):
                    if ids[marker_number] == self.turn_number:
                        self.marker_to_track = marker_number
                logger.info ("marker I'm looking for, is number %d" % self.marker_to_track)
            else:
                self.marker_to_track = 0
            if ids[self.marker_to_track][0] == self.turn_number:
                m = self.marker_to_track
                self.found = True
                #if found, comptue the centre and move the cursor there
                found_y = sum([arr[0] for arr in corners[m][0]])  / 4
                found_x = sum([arr[1] for arr in corners[m][0]])  / 4
                width = abs(corners[m][0][0][0]-corners[m][0][1][0]+corners[m][0][3][0]-corners[m][0][2][0])/2
                logger.info('marker width %s' % width)
                if width > self.TURN_WIDTH[self.turn_number]:
                    self.turn_number += 1
                    self.found = False
                    logger.info('Close to marker making turn %s' % self.turn_number)
                    if self.turn_number <= 2:
                        if self.turn_number == 1:
                            self.brake()
                        self.turn_right()
                    elif self.turn_number == 5:
                        logger.info('finished!')
                        self.drive.move(0,0)
                        self.finished = True
                    else:
                        if self.turn_number == 4:
                            self.brake()
                        self.turn_left()
                pygame.mouse.set_pos(int(found_x), int(self.CROP_WIDTH-found_y))
                self.t_error = (self.CROP_WIDTH/2 - found_y) / (self.CROP_WIDTH / 2)
                turn = self.STEERING_OFFSET + self.TURN_P * self.t_error
                if self.last_t_error is not 0:
                    #if there was a real error last time then do some damping
                    turn -= self.TURN_D *(self.last_t_error - self.t_error)
                turn = min(max(turn,-self.MAX_TURN_SPEED), self.MAX_TURN_SPEED)
                if self.driving:
                    self.drive.move(turn, self.STRAIGHT_SPEED)
                elif self.aiming:
                    self.drive.move(turn, 0)
                self.last_t_error = self.t_error
            else:
                logger.info("looking for marker %d" % self.turn_number)
                if self.found:
                    self.drive.move(0,0)
                else:
                    if self.turn_number <= 2:
                        self.turn_right()
                    else:
                        self.turn_left()
                self.found = False
                self.last_t_error = 0 
        else:
            logger.info("looking for marker %d" % self.turn_number)
            #if marker was found, then probably best to stop and look
            if self.found:
                if self.driving:
                    self.drive.move(0, 0) #self.STRAIGHT_SPEED/2)
            else:
                #otherwise, go looking
                if self.turn_number <= 2:
                    self.turn_right()
                else:
                    self.turn_left()
            self.found = False
            self.last_t_error = 0
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(cv2.flip(frame,1))
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
        found_identifier = "F" if self.found else "NF"
        img_name = "%d%simg.jpg" % (self.i, found_identifier)
        # filesave for debugging: 
        #cv2.imwrite(img_name, gray)
        self.i += 1



class Maze(BaseChallenge):
    """Minimal Maze challenge class"""

    def __init__(self, timeout=120, screen=None, joystick=None, markers=None):
        self.image_width = 480  # Camera image width
        self.image_height = 368  # Camera image height
        self.frame_rate = 30  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.joystick = joystick
        self.dict = markers
        super(Maze, self).__init__(name='Maze', timeout=timeout, logger=logger)

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
        self.camera.shutter_speed = 2000
        logger.info('Setup the stream processing thread')
        # TODO: Remove dependency on drivetrain from StreamProcessor
        self.processor = StreamProcessor(
            screen=self.screen,
            camera=self.camera,
            drive=self.drive,
            dict=self.dict
        )
        logger.info('Wait ...')
        time.sleep(2)
        logger.info('Setting up image capture thread')
        self.image_capture_thread = ImageCapture(
            camera=self.camera,
            processor=self.processor
        )
        pygame.mouse.set_visible(False)
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
