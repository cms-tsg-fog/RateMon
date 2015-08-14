#######################################################
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 13, 2015
# Last Modified: August 14, 2015 by Nathaniel Rupprecht
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
            opt, args = getopt.getopt(sys.argv[1:],"",["Help", "fitFile=", "configFile=", "triggerList=", "triggerListHLT=", "triggerListL1=",
                                                       "LSRange=", "singleLS=", "displayBad=", "allowedPercDiff=", "allowedDev=",
                                                       "window=","AllTriggers", "L1Triggers", "run=", "simulate=", "keepZeros",
                                                       "requireLumi", "quiet", "noColors", "mailAlerts", "usePerDiff", "hideStreams", "cutOnBoth",
                                                       "maxStream="])
        except:
            print "Error getting options. Exiting."
            exit(1)

        # Remember if we were told to use all triggers
        usingAll = False
        
        for label, op in opt:
            if label == "--fitFile":
                self.monitor.fitFile = str(op)
            elif label == "--triggerList":
                if not usingAll: self.monitor.useAll = False
                self.monitor.triggerList = self.loadTriggersFromFile(str(op))
                print "Using Trigger list %s" % (str(op))
            elif label == "--LSRange":
                self.monitor.sendMailAlerts = False
                start, end = str(op).split("-")
                self.monitor.LSRange = [int(start), int(end)]
                self.monitor.useLSRange = True
                print "Using only LS in the range %s - %s" % (start, end)
            elif label == "--singleLS":
                self.monitor.sendMailAlerts = False
                self.monitor.LSRange = [int(op), int(op)]
                self.monitor.useLSRange = True
                print "Only looking at lumisection %s" % (op)
            elif label == "--allowedPercDiff":
                self.monitor.percAccept = float(op)
            elif label == "--allowedDev":
                self.monitor.devAccept = float(op)
            elif label == "--run":
                self.monitor.sendMailAlerts = False
                self.monitor.runNumber = int(op)
                self.monitor.assignedNum = True
            elif label == "--simulate":
                self.monitor.sendMailAlerts = False
                self.monitor.runNumber = int(op)
                self.monitor.simulate = True
                self.monitor.assignedNum = True
            elif label == "--displayBad":
                self.monitor.displayBadRates = int(op)
            elif label == "--AllTriggers":
                self.monitor.useAll = True
                usingAll = True
            elif label == "--L1Triggers":
                self.monitor.useL1 = True
            elif label == "--keepZeros":
                self.monitor.removeZeros = False
            elif label == "--window":
                self.monitor.slidingLS = int(op)
            elif label == "--configFile":
                self.cfgFile = str(op)
                self.parseCFGFile()
            elif label == "--requireLumi":
                self.monitor.requireLumi = True
            elif label == "--quiet":
                self.monitor.quiet = True
            elif label == "--noColors":
                self.monitor.noColors = True
            elif label == "--mailAlerts":
                self.monitor.sendMailAlerts = True
            elif label == "--usePerDiff":
                self.monitor.usePerDiff = True
            elif label == "--hideStreams":
                self.monitor.showStreams = False
            elif label == "--cutOnBoth":
                self.monitor.either = True
            elif label == "--maxStream":
                self.monitor.maxStreamRate = float(op)
            elif label == "--Help":
                self.printOptions()

    # Use: Prints out all the possible command line options
    def printOptions(self):
        print ""
        print "Usage: python ShiftMonitorTool.py [Options]"
        print ""
        print "OPTIONS:"
        print "Help:"
        print "--Help                    : Calling this option prints out all the options that exist. You have already used this option."
        print ""
        print "File Options:"
        print "--fitFile=<name>          : The name of the file containing the fit for HLT and L1 Triggers."
        print "--configFile=<name>       : The name of a configuration file."
        print "--triggerList=<name>      : The name of a file containing a list of the HLT and L1 triggers that we want to observe."
        print ""
        print "Error Monitoring Options:"
        print "--allowedPercDiff=<num>   : The allowed percent difference for the rate."
        print "--allowedDev=<num>        : The allowed deviation for the rate."
        print "--cutOnBoth               : Flag rates only when they exceed both the standard deviation and the percent difference"
        print "--usePerDiff              : Cuts on percent difference instead of deviation."
        print "--displayBad=<num>        : Prints the first <num> triggers that are bad each time we check."
        print "--noColors                : Doesn't print out colors. Useful if you are dumping info to a file where colors don't work."
        print "--hideStreams             : Doesn't print out information about the streams."
        print "--maxStream               : The maximum stream rate for a 'good' stream, streams with a rate greater then this are colored (if colors are on)"
        print "--window=<num>            : The window (number of LS) to average over. Default is averaging over every new LS since last db query"
        print "--mailAlerts              : Send mail alerts when triggers have been in error for a while."
        print ""
        print "Secondary Capabilities:"
        print "--run=<num>               : Look at a certain run instead of monitoring current runs"
        print "--LSRange=<start>-<end>   : A range of LS to look at if we are using the --run=<num> option (you can actually use it any time, it just might not be useful)."
        print "--singleLS=<num>          : Look at a single LS (short for --LSRange=<num>-<num>)."
        print "--simulate=<num>          : Simulates online monitoring of run <num>, printing out tables covering periods of 60 seconds of run time."
        print ""
        print "Trigger Options:"
        print "--AllTriggers             : We will list the rates from unpredictable HLT Triggers."
        print "--L1Triggers              : We will monitor the unpredictable L1 Triggers as well."
        print ""
        print "Formatt Options:"
        print "--requireLumi             : Only prints out a table when the ave Lumi is not None"
        print "--keepZeros               : By default, triggers with zero rate that we don't have fits for are not shown. This makes them visible."
        print "--quiet                   : Prints fewer messages."
        print ""
        print "Program by Nathaniel Rupprecht, created July 13th, 2015. For questions, email nrupprec@nd.edu"
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
                    TriggerList.append(stripVersion(str(triggerName)))
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
                
                if label == "AllTriggers" and int(op)!=0:
                    self.monitor.doAll = True
                elif label == "L1Triggers" and int(op)!=0:
                    self.monitor.useL1 = True
                elif label == "DoL1" and int(op)!=0:
                    self.monitor.useL1 = True
                elif label == "TriggerListHLT" or label == "TriggerToMonitorList": # Backwards compatibility
                    self.monitor.TriggerListHLT = self.loadTriggersFromFile(str(op))
                    self.monitor.useTrigListHLT = True
                elif label == "TriggerListL1":
                    self.monitor.TriggerListL1 = self.loadTriggersFromFile(str(op))
                    self.monitor.useTrigListL1 = True
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
                elif label=="AllowedStandardDev":
                    self.monitor.devAccept = float(op)
                elif label=="AllowedPercentDev":
                    self.monitor.percAccept = float(op)
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
                elif label == "NoVersion": print "We always run with no version" # We always strip the version
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
