
#!/usr/bin/env python2.7  
# script by Alex Eames http://RasPi.tv/  
# http://raspi.tv/2013/how-to-use-interrupts-with-python-on-the-raspberry-pi-and-rpi-gpio  
import RPi.GPIO as GPIO  
import subprocess
GPIO.setmode(GPIO.BCM)  

# GPIO 17 set up as input. It is pulled up to stop false signals  
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)  



print "Press button 17 to launch menu.py"  
# now the program will do nothing until the signal on port 17   
# starts to fall towards zero. This is why we used the pullup  
# to keep the signal high and prevent a false interrupt  


def my_callback(channel):  
    print "falling edge detected on 17"

# when a falling edge is detected on port 17, regardless of whatever   
# else is happening in the program, the function my_callback will be run  
#GPIO.add_event_detect(17, GPIO.FALLING, callback=my_callback, bouncetime=300)   

 
try:  
    GPIO.wait_for_edge(17, GPIO.FALLING)  
    print "\nFalling edge detected. Now your program can continue with"  
    print "whatever was waiting for a button press."  
    subprocess.call(["sudo", "python", "/home/pi/Piradigm/menu.py"])
    
except KeyboardInterrupt:  
    GPIO.cleanup()       # clean up GPIO on CTRL+C exit  

GPIO.cleanup()           # clean up GPIO on normal exit 
