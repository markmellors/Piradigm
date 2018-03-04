import sys
import os
sys.path.append('/usr/local/lib/python2.7/site-packages')
import cv2
import cv2.aruco as aruco
import pygame
import numpy as np
from pygame.locals import*
import picamera
import picamera.array
import math
import json
#create board of markers
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
board = cv2.aruco.CharucoBoard_create(3,3,.025,.0125,dictionary)
img = board.draw((200*3,200*3))

#Dump the calibration board to a file
cv2.imwrite('charuco.png',img)


env_vars = [
    ("SDL_FBDEV", "/dev/fb1"),
    ("SDL_MOUSEDEV", "/dev/input/touchscreen"),
    ("SDL_MOUSEDRV", "TSLIB"),
]
for var_name, val in env_vars:
    os.environ[var_name] = val
screen_width = 320
screen_height = 240

camera = picamera.PiCamera()
camera.resolution = (screen_width, screen_height)
camera.framerate = 39
pygame.init()
screen = pygame.display.set_mode([screen_height, screen_width])
video = picamera.array.PiRGBArray(camera)

allCorners = []
allIds = []
decimator = 0
print("setup complete, looking")

try:
    for frameBuf in camera.capture_continuous(video, format ="rgb", use_video_port=True):
        frame = frameBuf.array #np.rot90(frameBuf.array)        
        video.truncate(0)
        
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        parameters =  aruco.DetectorParameters_create()
                                
        #print(parameters)
        '''    detectMarkers(...)
            detectMarkers(image, dictionary[, corners[, ids[, parameters[, rejectedI
            mgPoints]]]]) -> corners, ids, rejectedImgPoints
        '''
        #lists of ids and the corners beloning to each id
        res  = aruco.detectMarkers(gray, dictionary, parameters=parameters)
        if len(res[0])>0:
            res2 = cv2.aruco.interpolateCornersCharuco(res[0],res[1],gray,board)
            if res2[1] is not None and res2[2] is not None and len(res2[1])>3 and decimator%3==0:
                allCorners.append(res2[1])
                allIds.append(res2[2])

            cv2.aruco.drawDetectedMarkers(gray,res[0],res[1])
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        decimator+=1
        print decimator
        # Display the resulting frame
        frame = pygame.surfarray.make_surface(frame)
        screen.fill([0,0,0])
        screen.blit(frame, (0,0))
        pygame.display.update()
                                                                         
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                raise KeyboardInterrupt
except KeyboardInterrupt,SystemExit:
    imsize = gray.shape
    print "starting calibration calculations"
    err, cameraMatrix, distCoeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(allCorners,allIds,board,imsize,None,None)
    data = ({
      'cameraMatrix': cameraMatrix.tolist(),
      'distCoeffs': distCoeffs.tolist(),
      'err': err
    })
    with open('calibration.json', 'w') as f:
        json.dump(data, f)
    print('...done!')
    print(err)
    pygame.quit()
    cv2.destroyAllWindows()
