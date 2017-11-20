import datetime
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
        timeout_threshold = datetime.datetime.now() + datetime.timedelta(seconds=10)
        while (datetime.datetime.now() < timeout_threshold) and not self.killed:
            #print(datetime.datetime.now())
            time.sleep(0.5)
            logging.info("RC still alive")
            time.sleep(0.5)
        if (datetime.datetime.now() > timeout_threshold):
            logging.info("RC challenge timed out")

    def stop(self):
        logging.info("rc challenge stopping")
        self.killed = True
