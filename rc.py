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
        while not self.killed and time.clock() < (now + 10):
            time.sleep(1)
            logging.info("RC still alive")
        logging.info("RC timing out")

    def stop(self):
        logging.info("rc challenge stopping")
        self.killed = True
        return "stopping"
