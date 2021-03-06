from img_base_class import *
import random
import json
import math
import cv2.aruco as aruco
from approxeng.input.selectbinder import ControllerResource
from my_button import MyScale

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
        self.screen = pygame.display.get_surface()
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

    def file_selection(self, image):
        """Mode to select colour value to adjust. file and value labels are
        displayed on screen by calibrate object, so nothing needed from image"""
        self.display_label("Colour selection")
        time = self.clock.tick(30)
        sgc.update(time)

    def auto_calibrating(self, image):
        """mode to adjust current colour value based on Mean & stdDev of image
        in central region, also displays accordingly thresholded image"""
        obj_range = threshold_image(image, self.colour_value)
        frame = pygame.surfarray.make_surface(cv2.flip(obj_range, 1))
        self.screen.blit(frame, (0, 0))
        self.display_label("Auto-calibrating")
        self.colour_value = self.get_limits(image, 1.5)
        h, w = image.shape[:2]
        # pygame screen, (colour tuple), (top left x, top left y, width, height), line thickness
        pygame.draw.rect(self.screen, (255,0,0), (self.cal_y, self.cal_x, self.cal_height, self.cal_width), 2)

    def manual_calibrating(self, image):
        """manual calibration mode. sliders are displayed on screen by
        calibrate object, so nothing needed from image"""
        self.display_label("Manual calibration")
        time = self.clock.tick(30)
        sgc.update(time)

    def thresholding(self, image):
        """Image processing mode where image is converted to B&W based
        on current colour value, and displayed on screen"""
        self.display_label("Testing")
        obj_range = threshold_image(image, self.colour_value)
        frame = pygame.surfarray.make_surface(cv2.flip(obj_range, 1))
        self.screen.blit(frame, (0, 0))
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
        #cv2.rectangle takes cooridnates of lower left and top right
        cal_x1 = self.cal_x
        cal_y1 = self.cal_y
        cal_x2 = self.cal_x + self.cal_width
        cal_y2 = self.cal_y + self.cal_height
        cv2.rectangle(mask, (cal_x1, cal_y1), (cal_x2, cal_y2), 255, -1)
        mean, stddev = cv2.meanStdDev(image, mask=mask)
        lower = mean - sigmas * stddev
        upper = mean + sigmas * stddev
        return ((lower[0][0], lower[1][0], lower[2][0]), (upper[0][0], upper[1][0], upper[2][0]))
   
    def display_label(self, text):
        font = pygame.font.Font(None, 36)
        label = font.render(str(text), 1, (255,255,255))
        label_offset = self.image_centre_y - len(str(text)) * 4.5 #for centring
        self.screen.blit(label, (label_offset, 280))

    def process_image(self, image, screen):
        screen = pygame.display.get_surface()
        screen.fill([0, 0, 0])
        image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        self.mode[self.mode_number](image)
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
        self.file_dir = os.path.dirname(os.path.realpath(__file__))
        self.exponential = 2
        self.colour_radio_buttons = []
        self.colour_label = None
        self.file_index = None
        self.colour_index = None
        self.controls = self.setup_controls()
        super(Calibrate, self).__init__(name='Calibrate', timeout=timeout, logger=logger)

    def display_controls(self):
         """displays sliders for manual calibration"""
         colour_bounds = self.processor.colour_value
         for ctrl in self.controls:
             if not ctrl['ctrl'].active():
                 ctrl['ctrl'].add(ctrl['index'])
                 i = ctrl['index']
                 ctrl['ctrl'].value = colour_bounds[i % 2][int(i/2)]

    def remove_controls(self):
         """removes manual calibration sliders"""
         for ctrl in self.controls:
             if ctrl['ctrl'].active():
                 ctrl['ctrl'].remove(fade=False)

    def setup_controls(self):
        """returns a list of controls for HSV tuning"""
        # colours
        #why do these need repeating when theyre in menu.py? aren't they global?
        BLUE = 26, 0, 255
        SKY = 100, 50, 255
        CREAM = 254, 255, 250
        BLACK = 0, 0, 0
        WHITE = 255, 255, 255
        control_config = [
           ("min hue", 5, 50, BLACK, WHITE),
           ("max hue", 115, 50, BLACK, WHITE),
           ("min saturation", 5, 125, BLACK, WHITE),
           ("max saturation", 115, 125, BLACK, WHITE),
           ("min value", 5, 200, BLACK, WHITE),
           ("max value", 115, 200, WHITE, WHITE),
        ]
        return [
            self.make_controls(index, *item)
            for index, item
            in enumerate(control_config)
        ]

    def make_controls(self, index, text, xpo, ypo, colour, text_colour):
        """make a slider object for the specified position"""
        logger.debug("making button with text '%s' at (%d, %d)", text, xpo, ypo)
        return dict(
            index=index,
            label=text,
            ctrl = MyScale(label=text, pos=(xpo, ypo), col=colour, min=0, max=255, label_col=text_colour, label_side="top")
        )

    def joystick_handler(self, button):
        if button['home']:
            if self.processor.mode_number == 2: self.update_value()
            self.remove_controls()
            self.processor.mode_number = 0
            self.logger.info("File selection mode")
            pygame.mouse.set_visible(False)
            self.display_files(index=self.file_index)
            if self.colour_index is not None:
                self.display_values(index=self.colour_index)
        if button['start']:
            self.save_values()
            self.logger.info("colour value saved as %s" %  self.processor.colour_value)
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
            if self.processor.mode_number == 0: self.update_indexs()
            if self.processor.mode_number == 2: self.update_value()
            self.remove_controls()
            self.remove_radio_buttons()
            self.processor.mode_number = 3
            self.logger.info("Entering thresholding mode")
            pygame.mouse.set_visible(True)
        if button['l1']:
            if self.processor.mode_number == 0: self.update_indexs()
            self.remove_radio_buttons()
            self.processor.mode_number = 2
            self.logger.info("Manual calibration mode")
            self.display_controls()
            pygame.mouse.set_visible(False)
        if button['l2']:
            if self.processor.mode_number == 0: self.update_indexs()
            self.remove_controls()
            self.remove_radio_buttons()
            self.processor.mode_number = 1
            self.logger.info("Auto calibrating mode")
            pygame.mouse.set_visible(False)
        #if left or right buttons on right side of joystick pressed, treat them like arrow buttons
        #if left D pad pressed, treat like tab, double tab or shift tab (tab backwards)
        if button['circle']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 77, 'key': pygame.K_RIGHT, 'unicode': "u'\t'"}))
        if button['square']:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,{
                'mod': 0, 'scancode': 75, 'key': pygame.K_LEFT, 'unicode': "u'\t'"}))
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

    def update_value(self):
        # create list placeholder so individual elements can be added
        colour_val = [[None,None,None],[None,None,None]]  
        for ctrl in self.controls:
            i = ctrl['index']
            colour_val[i % 2][int(i/2)] = int(ctrl['ctrl'].value)
        #assign list to tuple in one go
        self.processor.colour_value = colour_val

    def save_values(self):
        if self.colour_index is not None:
            colour = self.colour_radio_buttons[self.colour_index]['label']
            self.colour_values[colour] = self.processor.colour_value
            data = self.colour_values
            filename = self.file_radio_buttons[self.file_index]['label'] + ".json"
            file_path = os.path.join(self.file_dir, filename)
            with open(file_path, 'w') as f:
                json.dump(data, f)
            save_label = sgc.Label(text="saved", pos=(15, 160), col=(255,255,255))
            save_label.add(101)
            self.clock = pygame.time.Clock()
            timer = self.clock.tick(30)
            sgc.update(timer)
            time.sleep(1)
            save_label.remove(fade=False) 

    def update_display(self):
        for radio in self.file_radio_buttons:
            if radio['btn'].has_focus():
                self.display_values()
                self.logger.info("%s file selected for colour editing" % radio['label'])
                if self.colour_label:
                    self.colour_label.remove(fade=False)
        for radio in self.colour_radio_buttons:
            if radio['btn'].has_focus():
                self.processor.colour_value = self.colour_values[radio['label']]
                label_text = str(self.colour_values[radio['label']])
                if self.colour_label and self.colour_label.active():
                    self.colour_label.text = label_text
                else:
                    self.colour_label = sgc.Label(text=label_text, pos=(15, 150), col=(255,255,255))
                    self.colour_label.add(100)
                self.logger.info("%s value selected for editing" % radio['label'])

    def display_files(self, index=None):
        all_files = os.listdir(self.file_dir)
        self.file_radio_buttons = []
        button_index = 0
        for filename in os.listdir(file_path):
            display_name, extension = os.path.splitext(filename)
            if extension == '.json' and filename <> 'calibration.json':
                button_x = (button_index % 2) * 120 + 10
                button_y = ((button_index - 1) % 2 + button_index) * 12
                radio_button = sgc.Radio(group="file", label=display_name, pos=(button_x, button_y), col = (255,255,255))
                data = dict(btn=radio_button, label=display_name, index=button_index)
                self.file_radio_buttons.append(data)
                radio_button.add(button_index)
                button_index += 1
        self.file_radio_buttons[index]['btn']._activate() if index is not None else self.file_radio_buttons[0]['btn']._activate()

    def display_values(self, index=None):
        for button in self.colour_radio_buttons:
            button['btn'].remove(button['index'])
        for button in self.file_radio_buttons:
            if button['btn'].selected:
                filename = button['label'] + ".json"
        file_path = os.path.join(self.file_dir, filename)
        with open(file_path) as json_file:
            self.colour_values = json.load(json_file)
        self.colour_radio_buttons = []
        num_of_file_radio_btns = len(self.file_radio_buttons)
        button_index = 0
        button_start_y = ((num_of_file_radio_btns - 2) % 2 + num_of_file_radio_btns - 1) * 12 + 15
        for colour in self.colour_values.keys():
            button_x = (button_index % 2) * 120 + 10
            button_y = ((button_index - 1) % 2 + button_index) * 12 + button_start_y
            radio_button = sgc.Radio(group="colour", label=colour, pos=(button_x, button_y), col = (255,255,255))
            button_details = dict(btn=radio_button, label=colour, index=button_index+num_of_file_radio_btns)
            self.colour_radio_buttons.append(button_details)
            radio_button.add(button_index+num_of_file_radio_btns)
            button_index += 1
        if index is not None: self.colour_radio_buttons[index]['btn']._activate()

    def remove_radio_buttons(self):
       for button in self.file_radio_buttons:
            button['btn'].remove(fade=False) #button['index'])
       for button in self.colour_radio_buttons:
            button['btn'].remove(fade=False) #button['index'])
       if self.colour_label:
           self.colour_label.remove(fade=False)

    def update_indexs(self):
        self.file_index = None
        for radio in self.file_radio_buttons:
            if radio['btn'].selected:
                self.file_index = radio['index']
        self.colour_index = None
        num_of_file_radio_btns = len(self.file_radio_buttons)
        for radio in self.colour_radio_buttons:
            if radio['btn'].selected:
                self.colour_index = radio['index']-num_of_file_radio_btns

    def run(self):
        # Startup sequence
        logger.info('Setting up camera')
#        screen = pygame.display.get_surface()
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
                    rx, ry = self.joystick['rx', 'ry']
                    logger.debug("joystick L/R: %s, %s" % (rx, ry))
                    rx = self.exp(rx, self.exponential)
                    ry = self.exp(ry, self.exponential)
                    self.drive.move(rx, ry)
                if self.processor.finished:
                    self.stop()

        except KeyboardInterrupt:
            # CTRL+C exit, disable all drives
            self.logger.info("killed from keyboard")
            self.drive.move(0,0)
        finally:
            self.remove_radio_buttons()
            self.remove_controls()
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

    def constrain(self, val, min_val, max_val):
        return min(max_val, max(min_val, val))

    def exp(self, demand, exp):
        # function takes a demand speed from -1 to 1 and converts it to a response value
        # with an exponential function. exponential is -inf to +inf, 0 is linear
        exp = 1/(1 + abs(exp)) if exp < 0 else exp + 1
        return math.copysign((abs(demand)**exp), demand)
