#######################################################
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 13, 2015
# Last Modified: July 15, 2015 by Nathaniel Rupprecht
#
# Dependencies: ShiftMonitorNCR.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
import cPickle as pickle
import sys
import time
# For getting command line options
import getopt
# For the ShiftMonitor tool
from ShiftMonitorNCR import *

# Class CommandLineParser
class CommandLineParser:
    def __init__(self):
        self.monitor = ShiftMonitor()
        self.cfgFile = ""  # The name of the configuration file to use

    def parseArgs(self):
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["Help", "fitFile=", "configFile=", "triggerList=", "LSRange=", "displayBad=", "AllowedPercDiff=", "Window=","AllTriggers", "L1Triggers", "run=", "keepZeros"])
            
        except:
            print "Error getting options. Exiting."
            exit(1)
                                     
        if len(opt) == 0 and len(args) == 0:
            print "We need options to run this script."
            print "Use 'python ShiftMonitorTool.py --Help' to see options."
            
        for label, op in opt:
            if label == "--fitFile":
                self.monitor.fitFileHLT = str(op)
            elif label == "--triggerList":
                self.monitor.TriggerListHLT = self.loadTriggersFromFile(str(op))
            elif label == "--LSRange":
                start, end = str(op).split("-")
                self.monitor.LSRange = [start, end]
                self.useLSRange = True
                print "Using only LS in the range %s - %s" % (start, end)
            elif label == "--AllowedPercDiff":
                self.monitor.percAccept = float(op)
            elif label == "--run":
                self.monitor.runNumber = int(op)
                self.monitor.assignedNum = True
            elif label == "--displayBad":
                self.monitor.displayBadRates = int(op)
            elif label == "--AllTriggers":
                self.monitor.useAll = True
            elif label == "--L1Triggers":
                self.monitor.useL1 = True
            elif label == "--keepZeros":
                self.monitor.removeZeros = False
            elif label == "--Window":
                self.monitor.slidingLS = int(op)
            elif label == "--configFile":
                self.cfgFile = str(op)
                self.parseCFGFile()
            elif label == "--Help":
                self.printOptions()

    # Use: Prints out all the possible command line options
    def printOptions(self):
        print ""
        print "Usage: python ShiftMonitorTool.py [Options]"
        print ""
        print "OPTIONS:"
        print "--fitFile=<name>          : The name of the file containing the fit with which we calculate expected rates."
        print "--configFile=<name>       : The name of a configuration file."
        print "--triggerList=<name>      : The name of a file containing a list of triggers that we want to observe."
        print "--AllowedPercDiff=<num>   : The allowed percent difference for the rate."
        print "--Window=<num>            : The window (number of LS) to average over."
        print "--run=<num>               : Look at a certain run instead of monitoring current runs"
        print "--LSRange=<num>-<num>     : A range of LS to look at if we are using the --run=<num> option (you can actually use it any time, it just might not be useful)."
        print "--displayBad=<num>        : Prints the first <num> triggers that are bad each time we check."
        print "--AllTriggers             : We will list the rates from unpredictable HLT Triggers."
        print "--L1Triggers              : We will monitor the unpredictable L1 Triggers as well."
        print "--Help                    : Calling this option prints out all the options that exist. You have already used this option."
        exit()

    # Use: Runs the shift monitor
    # Returns: (void) (Never returns, monitor.run() has an infinite loop)
    def run(self):
        self.monitor.run()
                    
    # Use: Opens a file containing a list of trigger names and adds them to the RateMonitor class's trigger list
    # Note: We do not clear the trigger list, this way we could add triggers from multiple files to the trigger list
    # -- fileName: The name of the file that trigger names are contained in
    # Returns: (void)
    def loadTriggersFromFile(self, fileName):
        try:
            file = open(fileName, 'r')
        except:
            print "File", fileName, "(a trigger list file) failed to open."
            return
        
        allTriggerNames = file.read().split() # Get all the words, no argument -> split on any whitespace
        TriggerList = []
        for triggerName in allTriggerNames:
            try:
                if not str(triggerName) in TriggerList:
                    TriggerList.append(str(triggerName))
            except:
                print "Error parsing trigger name in file", fileName
        return TriggerList

    # Use: Parser options from a cfg file
    def parseCFGFile(self):
        try:
            file = open(self.cfgFile, "r")
        except:
            print "Config file failed to open. Exiting program."
            exit()
            
        for line in file:
            # Get rid of new line
            lineprime = line.split('\n')[0]
            tuple = lineprime.split('#',1) # Find where comments start
            if tuple[0] != "" and tuple[0] != "\n": # If the entire line is not a comment
                # Get the label and the option argument
                try: label, op = tuple[0].split('=')
                except: continue
                
                if label == "AllTriggers" and int(op)==1:
                    self.monitor.doAll = True
                elif label == "DoL1" and int(op)==1:
                    self.monitor.useL1 = True
                elif label == "TriggerListHLT" or label == "TriggerToMonitorList": # Backwards compatibility
                    self.monitor.TriggerListHLT = self.loadTriggersFromFile(str(op))
                    self.monitor.useTrigList = True
                elif label == "TriggerListL1":
                    self.monitor.TriggerListL1 = self.loadTriggersFromFile(str(op))
                    self.monitor.useTrigList = True
                elif label == "FitFileHLT" or label == "FitFileName":
                    self.monitor.fitFileHLT = str(op)
                elif label == "FitFileL1":
                    self.monitor.fitFileL1 = str(op)
                elif label == "LSSlidingWindow":
                    self.monitor.slidingLS = int(op)
                elif label == "DefaultMaxBadRatesToShow":
                    if int(op) >= 0:
                        self.monitor.displayBadRates = int(op)
                    else: print "We need a positive number for the max number of bad rates to show."
                elif label == "ShowAllBadRates":
                    self.monitor.displayBadRates = -1

                elif label == "ShowSigmaAndPercDiff": print "ShowSigmaAndPercDiff unimplemented"
                elif label == "WarnOnSigmaDiff": print "WarnOnSigmaDiff unimplemented"
                elif label == "ReferenceRun": print "ReferenceRun unimplemented"
                elif label == "CompareReference": print "CompareReference unimplemented"
                elif label == "DefaultAllowedRatePercDiff": print "DefaultAllowedRatePercDiff unimplemented"
                elif label == "DefaultAllowedRateSigmaDiff": print "DefaultAllowedRateSigmaDiff unimplemented"
                elif label == "DefaultIgnoreThreshold": print "DefaultIgnoreThreshold unimplemented"
                elif label == "ExcludeTriggerList": print "ExcludeTriggerList unimplemented"
                elif label == "L1CrossSection": print "L1CrossSection unimplemented"
                elif label == "MonitorTargetLumi": print "MonitorTargetLumi unimplemented"
                elif label == "FindL1Zeros": print "FindL1Zeros unimplemented"
                elif label == "MaxExpressRate": print "MaxExpressRate unimplemented"
                elif label == "ShifterMode": print "ShifterMode unimplemented"
                elif label == "MaxStreamARate": print "MaxStreamARate unimplemented"
                elif label == "NoVersion": print "NoVersion unimplemented" # We always strip the version
                elif label == "ForbiddenColumns": print "ForbiddenColumns unimplemented"
                elif label == "CirculatingBeamsColumn": print "CirculatingBeamsColumn unimplemented"
                elif label == "MaxLogMonRate": print "MaxLogMonRate unimplemented"
                elif label == "L1SeedChangeFit": print "L1SeedChangeFit unimplemented"
                
                else: print "Option %s, %s not recognized" % (label, op)
             
## ----------- End of class CommandLineParser ------------ ##

if __name__ == "__main__":
    parser = CommandLineParser()
    parser.parseArgs()
    #try:
    parser.run()
    #except:
    #print "\nExiting. Goodbye..."
