import time


class RC:
    def __init__(self):
        #time.sleep(1)
        print("initialised")
        self.name = "RC"
        self.killed = False
 

    def run(self):
        print("set to run")
        now = time.clock()
        while not self.killed and time.clock()< (now +5):
            time.sleep(1)
            print("still alive")

    def stop(self):
        print("rc challenge stopping")
        self.killed = True
	return "stopping"
