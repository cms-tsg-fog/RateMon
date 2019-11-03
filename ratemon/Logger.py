import sys, os, datetime

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        
        self.cdate = str(datetime.datetime.now()).split()[0]
        self.ctime = str(datetime.datetime.now()).split()[1].split(':')[0] +"_"+ str(datetime.datetime.now()).split()[1].split(':')[1]
        self.fname = "log_rateMon_"+self.cdate+"_"+self.ctime+".dat"

        self.log = open(self.fname, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()
