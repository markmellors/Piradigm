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
        # Why the one second sleep?
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

    def process_image(self, image, screen)
    


class Maze(BaseChallenge):
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
        pygame.mouse.set_visible(False)
        try:
            while not self.should_die:
                time.sleep(0.1)

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

camera = picamera.PiCamera()
camera.resolution = (screen_width, screen_height)
camera.framerate = 30
camera.iso = 800
camera.shutter_speed = 12000
pygame.init()
screen = pygame.display.set_mode([240, 320])
video = picamera.array.PiRGBArray(camera)
drive = Drivetrain(timeout=120)

#create small cust dictionary
small_dict = aruco.Dictionary_create(6, 3)
print("setup complete, looking")
last_t_error = 0
speed = 0
MIN_SPEED = 0
STRAIGHT_SPEED = 0.5
STEERING_OFFSET = 0.0  #more positive make it turn left
CROP_WIDTH = 320
i = 0
TIMEOUT = 30.0
START_TIME = time.clock()
END_TIME = START_TIME + TIMEOUT
found = False
turn_number = 0
TURN_TARGET = 5
TURN_WIDTH = [30, 35, 35, 30, 35, 35]

NINTY_TURN = 0.8  #0.8 works if going slowly
MAX_SPEED = 0
SETTLE_TIME = 0.05
TURN_TIME = 0.04
MAX_TURN_SPEED = 0.25
loop_start_time=0
marker_to_track=0
BRAKING_FORCE = 0.1
BRAKE_TIME = 0.05

def turn_right():
    drive.move(NINTY_TURN, 0)
    time.sleep(TURN_TIME)
    drive.move(0,0)
    time.sleep(SETTLE_TIME)
                
def turn_left():
    drive.move(-NINTY_TURN, 0)
    time.sleep(TURN_TIME)
    drive.move(0,0)
    time.sleep(SETTLE_TIME)

def brake():
    drive.move(0,-BRAKING_FORCE)
    time.sleep(BRAKE_TIME)
    drive.move(0,0)
    
try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        if time.clock() > END_TIME or turn_number > TURN_TARGET:
           raise KeyboardInterrupt
        frame = (frameBuf.array)
        video.truncate(0)
        frame = frame[30:190, (screen_centre - CROP_WIDTH/2):(screen_centre + CROP_WIDTH/2)]
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        parameters =  aruco.DetectorParameters_create()
        #print(parameters)
        '''    detectMarkers(...)
            detectMarkers(image, dictionary[, corners[, ids[, parameters[, rejectedI
            mgPoints]]]]) -> corners, ids, rejectedImgPoints
        '''
        #lists of ids and the corners beloning to each id
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, small_dict, parameters=parameters)
        if ids != None:
            #print ("found marker %s" % ids)
            if len(ids)>1:
                print "found %d markers" % len(ids),
                marker_to_track = 0
                for marker_number in range(0, len(ids)):
                    if ids[marker_number] == turn_number:
                        marker_to_track = marker_number
                print (", marker I'm looking for, is number %d" % marker_to_track)
            else:
                marker_to_track = 0
            if ids[marker_to_track][0] == turn_number:
                m = marker_to_track
                found = True
                #if found, comptue the centre and move the cursor there
                found_y = sum([arr[0] for arr in corners[m][0]])  / 4
                found_x = sum([arr[1] for arr in corners[m][0]])  / 4
                width = abs(corners[m][0][0][0]-corners[m][0][1][0]+corners[m][0][3][0]-corners[m][0][2][0])/2
                print ('marker width %s' % width)
                if width > TURN_WIDTH[turn_number]:
                    turn_number += 1
                    print ('Close to marker making turn %s' % turn_number)
                    if turn_number is 5:
                        print('finished!')
                        drive.move(0,0)
                        END_TIME = time.clock()
                pygame.mouse.set_pos(int(found_x), int(CROP_WIDTH-found_y))
                t_error = (CROP_WIDTH/2 - found_y) / (CROP_WIDTH / 2)
                turn = STEERING_OFFSET + TURN_P * t_error
                if last_t_error is not 0:
                    #if there was a real error last time then do some damping
                    turn -= TURN_D *(last_t_error - t_error)
                turn = min(max(turn,-MAX_TURN_SPEED), MAX_TURN_SPEED)
                print turn
                #if we're rate limiting the turn, go slow
                if abs(turn) == MAX_TURN_SPEED:
                    drive.move (turn, STRAIGHT_SPEED/3)
                else:
                    drive.move (turn, STRAIGHT_SPEED)
                last_t_error = t_error
                #print(camera.exposure_speed)
            else:
                print ("looking for marker %d" % turn_number)
                if found:
                    drive.move(0,0)
                else:
                    if turn_number <= 2:
                        if turn_number == 1:
                            brake()
                        turn_right()
                    else:
                        if turn_number == 4:
                            brake()
                        turn_left()
                found = False
                last_t_error = 0 
        else:
            print ("looking for marker %d" % turn_number)
            #if marker was found, then probably best to stop and look
            if found:
                drive.move(0,0)
            else:
                #otherwise, go looking
                if turn_number <= 2:
                    if turn_number == 1:
                        brake()
                    turn_right()
                else:
                    if turn_number == 4:
                        brake()
                    turn_left()
            found = False
            last_t_error = 0
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(cv2.flip(frame,1))
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
        if found:
         img_name = str(i) + "Fimg.jpg"
        else:
         img_name = str(i) + "NFimg.jpg"
        #filesave for debugging: 
        #cv2.imwrite(img_name, gray)
        i += 1
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    drive.move(0,0)
    pygame.quit()
    cv2.destroyAllWindows()
