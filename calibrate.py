from img_base_class import *
import random
import json
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
        self.drive.should_normalise_motor_speed = False
        self.screen = screen
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.DRIVING = True
        self.edge = False
        self.BLUR = 3
        self.mode = [self.file_selection, self.auto_calibrating, self.manual_calibrating, self.thresholding]
        self.mode_number = 0
        self.colour_value = ((0, 0, 0), (180, 255, 255))
        self.cal_x = self.image_width/3
        self.cal_y = self.image_height/3
        self.cal_width = self.image_width/3
        self.cal_height = self.image_width/3
        self.TIMEOUT = 30.0
        self.PARAM = 60
        self.clock = pygame.time.Clock()
        self.START_TIME = time.clock()
        self.END_TIME = self.START_TIME + self.TIMEOUT
        self.finished = False
        self.i = 0
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

    def file_selection(self, image, screen):
        time = self.clock.tick(30)
        sgc.update(time)

    def auto_calibrating(self, image, screen):
        screenimage = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        frame = pygame.surfarray.make_surface(cv2.flip(screenimage, 1))
        screen.blit(frame, (0, 0))
        self.show_cal_label(screen)
        self.colour_value = self.get_limits(image, 1.5)
        h, w = image.shape[:2]
        # pygame screen, (colour tuple), (top left x, top left y, width, height), line thickness
        pygame.draw.rect(screen, (255,0,0), (self.cal_y, self.cal_x, self.cal_height, self.cal_width), 2)

    def manual_calibrating(self, image, screen):
        pass

    def thresholding(self, image, screen):
        self.show_thresholding_label(screen)
        obj_range = threshold_image(image, self.colour_value)
        frame = pygame.surfarray.make_surface(cv2.flip(obj_range, 1))
        screen.blit(frame, (0, 0))
        obj_x, obj_y, obj_a, obj_contour = find_largest_contour(obj_range)
        if obj_contour is not None:
            pygame.mouse.set_pos(obj_y, self.image_width - obj_x)
            img_name = str(self.i) + "Fimg.jpg"
        else:
            img_name = str(self.i) + "NFimg.jpg"
        image = cv2.cvtColor(image, cv2.COLOR_HSV2RGB)
        #filesave for debugging: 
        #cv2.imwrite(img_name, image)
        self.i += 1

    def get_limits(self, image, sigmas):
        """function to use the mean and standard deviation of an images
        channels in the centre of the image to create suggested threshold
        limits based on number of 'sigmas' (usually less than three).
        returns a tuple of tuples ((low1, low2, low3),(upp1, upp2, upp3))"""
        h, w = image.shape[:2]
        mask = numpy.zeros(image.shape[:2], numpy.uint8)
        cal_x1 = self.cal_x
        cal_y1 = self.cal_y
        cal_x2 = self.cal_x + self.cal_width
        cal_y2 = self.cal_y + self.cal_height
        cv2.rectangle(mask, (cal_x1, cal_y1), (cal_x2, cal_y2), 255, -1)
        mean, stddev = cv2.meanStdDev(image, mask=mask)
        lower = mean - sigmas * stddev
        upper = mean + sigmas * stddev
        return ((lower[0][0], lower[1][0], lower[2][0]), (upper[0][0], upper[1][0], upper[2][0]))
   
    def show_cal_label(self, screen):
        font = pygame.font.Font(None, 60)
        label = font.render(str("Calibrating"), 1, (255,255,255))
        screen.blit(label, (10, 240))

    def show_thresholding_label(self, screen):
        font = pygame.font.Font(None, 60)
        label = font.render(str("Testing"), 1, (255,255,255))
        screen.blit(label, (10, 240))


    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        screen.fill([0, 0, 0])
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        self.mode[self.mode_number](image, screen)
        pygame.display.update()



class Calibrate(BaseChallenge):
    """Colour calibration function, allows any json file storing colours to be tuned"""

    def __init__(self, timeout=120, screen=None, joystick=None):
        self.image_width = 240  # Camera image width
        self.image_height = 192  # Camera image height
        self.frame_rate = 40  # Camera image capture frame rate
        self.screen = screen
        time.sleep(0.01)
        self.joystick=joystick
        self.colour_radio_buttons = []
        self.colour_label = None
        super(Calibrate, self).__init__(name='Calibrate', timeout=timeout, logger=logger)

    def joystick_handler(self, button):
        if button['home']:
            self.processor.mode_number = 0
            self.logger.info("File selection mode")
            pygame.mouse.set_visible(False)
            self.display_files()
        if button['start']:
            if self.processor.mode_number <> 0:
                self.logger.info("colour value set to %s" %  self.colour_value)
                #TODO: add value save routine here 
                self.logger.info("value saved")
        if button['select']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 32, 'key': pygame.K_SPACE, 'unicode': u' '}))
            pygame.event.post(pygame.event.Event(pygame.KEYUP,{
                'mod': 0, 'scancode': 32, 'key': pygame.K_SPACE, 'unicode': u' '}))
            time.sleep(0.1)
            self.update_display()
        if button['r1']:
            self.processor.finished = True
        if button['r2']:
            self.remove_radio_buttons()
            self.processor.mode_number = 3
            self.logger.info("Entering thresholding mode")
            pygame.mouse.set_visible(True)
        if button['l1']:
            self.remove_radio_buttons()
            self.processor.mode_number = 2
            self.logger.info("Manual calibration mode")
            pygame.mouse.set_visible(False)
        if button['l2']:
            self.remove_radio_buttons()
            self.processor.mode_number = 1
            self.logger.info("Auto calibrating mode")
            pygame.mouse.set_visible(False)
        if button['dright']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
        if button['dleft']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 1, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
        if button['ddown']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
        if button['dup']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 1, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 1, 'scancode': 15, 'key': pygame.K_TAB, 'unicode': "u'\t'"}))

    def update_display(self):
        for radio in self.file_radio_buttons:
            if radio['btn'].has_focus():
                self.display_values()
                self.logger.info("%s file selected for colour editing" % radio['label'])
        for radio in self.colour_radio_buttons:
            if radio['btn'].has_focus():
                self.processor.colour_value = self.colour_values[radio['label']]
                label_text = str(self.colour_values[radio['label']])
                if self.colour_label:
                    self.colour_label.text = label_text
                else:
                    self.colour_label = sgc.Label(text=label_text, pos=(15, 120), col=(255,255,255))
                    self.colour_label.add(100)
                self.logger.info("%s value selected for editing" % radio['label'])

    def display_files(self):
        file_path = os.path.dirname(os.path.realpath(__file__))
        all_files = os.listdir(file_path)
        self.file_radio_buttons = []
        button_index = 0
        screen = pygame.display.get_surface()
        for filename in os.listdir(file_path):
            if filename.endswith('.json') and filename <> 'calibration.json': 
                display_name = filename[:len(filename)-5] #trim filetype off
                button_x = (button_index % 2) * 120 + 10
                button_y = ((button_index - 1) % 2 + button_index) * 12
                radio_button = sgc.Radio(group="file", label=display_name, pos=(button_x, button_y), col = (255,255,255))
                data = dict(btn=radio_button, label=display_name, index=button_index)
                self.file_radio_buttons.append(data)
                radio_button.add(button_index)
                button_index += 1
        self.file_radio_buttons[0]['btn']._activate()

    def display_values(self):
        for button in self.colour_radio_buttons:
            button['btn'].remove(button['index'])
        for button in self.file_radio_buttons:
            if button['btn'].selected:
                filename = button['label'] + ".json"
        with open(filename) as json_file:
            self.colour_values = json.load(json_file)
        self.colour_radio_buttons = []
        num_of_file_radio_btns = len(self.file_radio_buttons)
        button_index = 0
        button_start_y = ((num_of_file_radio_btns - 2) % 2 + num_of_file_radio_btns - 1) * 12 + 15
        for colour in self.colour_values.keys():
            button_x = (button_index % 2) * 120 + 10
            button_y = ((button_index - 1) % 2 + button_index) * 12 + button_start_y
            radio_button = sgc.Radio(group="colour", label=colour, pos=(button_x, button_y), col = (255,255,255))
            data = dict(btn=radio_button, label=colour, index=button_index+num_of_file_radio_btns)
            self.colour_radio_buttons.append(data)
            radio_button.add(button_index+num_of_file_radio_btns)
            button_index += 1

    def remove_radio_buttons(self):
       for button in self.file_radio_buttons:
            button['btn'].remove(button['index'])
       for button in self.colour_radio_buttons:
            button['btn'].remove(button['index'])
       self.colour_label.remove      


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
        logger.info('Setting up image capture thread')
        self.image_capture_thread = ImageCapture(
            camera=self.camera,
            processor=self.processor
        )
        pygame.mouse.set_visible(False)

        self.display_files()
        try:
            while not self.should_die:
                time.sleep(0.01)
                if self.joystick.connected:
                    self.joystick_handler(self.joystick.check_presses())
                if self.processor.finished:
                    self.stop()

        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            self.logger.info("killed from keyboard")
            self.drive.move(0,0)
        finally:
            self.remove_radio_buttons()
            # Tell each thread to stop, and wait for them to end
            self.logger.info("stopping threads")
            self.drive.should_normalise_motor_speed = True
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
