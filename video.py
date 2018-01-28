 

"""display picam video on the touchscreen"""
import os
import sys
sys.path.append('/usr/local/lib/python2.7/site-packages')
import pygame
from pygame.locals import *
import cv2
import numpy as np
import time
import picamera
import picamera.array

env_vars = [
    ("SDL_FBDEV", "/dev/fb1"),
    ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
    ("SDL_MOUSEDRV", "TSLIB"),
]
for var_name, val in env_vars:
    os.environ[var_name] = val

screen_width = 240
screen_height = 320

camera = picamera.PiCamera()
camera.resolution = (screen_width, screen_height)

pygame.init()
clock = pygame.time.Clock()
pygame.display.set_caption("OpenCV camera stream on Pygame")
pygame.mouse.set_visible(False)
screen = pygame.display.set_mode([screen_width, screen_height])
video = picamera.array.PiRGBArray(camera)
try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        frame = np.rot90(frameBuf.array)        
        video.truncate(0)
        frame = pygame.surfarray.make_surface(frame)
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
                                         
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    pygame.quit()
    cv2.destroyAllWindows()
