import time

class RC:

    def _init_(self):
        print("initialised")
        self.name = "RC"
        self.killed = False


    def run(self):
        print("set to run")
        while True:
            time.sleep(1)
            print("still alive")


    def stop(self):
        print("rc challenge stopping")
        self.killed = True
