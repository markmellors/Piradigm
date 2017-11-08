import time
import logging

logging.basicConfig(
            filename='piradigm.log',
            level=logging.DEBUG,
            format='%(asctime)s %(message)s'
        )

class RC:
    def __init__(self):       
        #time.sleep(1)
        logging.info("initialised")
        self.name = "RC"
        self.killed = False

    def run(self):
        logging.info("RC set to run")
        now = time.clock()
        while (time.clock() < (now + 10)) and not self.killed:
            time.sleep(0.5)
            logging.info("RC still alive")
            time.sleep(0.5)
        if time.clock() > (now+10):
            logging.info("RC challenge timed out")

    def stop(self):
        logging.info("rc challenge stopping")
        self.killed = True
