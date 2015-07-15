#######################################################
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 13, 2015
# Last Modified: July 15, 2015 by Nathaniel Rupprecht
#
# Dependencies: DBParser.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects
#######################################################

from DBParser import *
from ROOT import TF1
import cPickle as pickle
import sys
import time
# For colors
from termcolor import *
from colors import *
import getopt # For getting command line options  

def stringSegment(strng, tot):
    string = str(strng)
    for x in range(0, tot-len(str(strng))):
        string += " "
    return string

# Alias for sys.stdout.write
write = sys.stdout.write

# Class CommandLineParser
class CommandLineParser:
    def __init__(self):
        self.monitor = ShiftMonitor()

    def parseArgs(self):
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["Help", "fitFile=", "triggerList=", "AllowedPercDiff=","AllTriggers", "L1Triggers", "run="])
            
        except:
            print "Error getting options. Exiting."
            exit(1)
                                     
        if len(opt) == 0 and len(args) == 0:
            print "We need options to run this script."
            print "Use 'python ShiftMonitorTool.py --Help' to see options."
            
        for label, op in opt:
            if label == "--fitFile":
                self.monitor.fitFileHLT = str(op)
            if label == "--triggerList":
                self.monitor.TriggerListHLT = self.loadTriggersFromFile(str(op))
            if label == "--AllowedPercDiff":
                self.monitor.percAccept = float(op)
            if label == "--run":
                self.monitor.runNumber = int(op)
                self.monitor.assignedNum = True
            if label == "--AllTriggers":
                self.monitor.useAll = True
            if label == "--L1Triggers":
                self.monitor.useL1 = True
            if label == "--Help":
                self.printOptions()

    # Use: Prints out all the possible command line options
    def printOptions(self):
        print ""
        print "Usage: python ShiftMonitorTool.py [Options]"
        print ""
        print "OPTIONS:"
        print "--fitFile=<name>          : The name of the file containing the fit with which we calculate expected rates."
        print "--triggerList=<name>      : The name of a file containing a list of triggers that we want to observe."
        print "--AllowedPercDiff=<num>   : The allowed percent difference for the rate."
        print "--run=<num>               : Look at a certain run instead of monitoring current runs"
        print "--AllTriggers             : We will list the rates from unpredictable HLT Triggers."
        print "--L1Triggers              : We will monitor the unpredictable L1 Triggers as well."
        print "--Help                    : Calling this option prints out all the options that exist. You have already used this option."

    # Use: Runs the shift monitor
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

    def parserCFGFile(self):
        pass

## ----------- End of class CommandLineParser ------------ ##

# Class ShiftMonitor
class ShiftMonitor:

    def __init__(self):
        self.fitFileHLT = ""         # The fit file
        self.fitFileL1 = ""          # The fit file for L1 triggers
        self.InputFitHLT = None      # The fit information for the HLT triggers
        self.InputFitL1 = None       # The fit information for the L1 triggers
        self.parser = DBParser()

        self.lastRunNumber = -2      # The run number during the last segment
        self.runNumber = -1          # The number of the current run
        self.assignedNum = False     # If true, we look at the assigned run, not the latest run
        self.lastLS = 0              # The last LS that was processed last segment
        self.latestLS = 0            # The latest LS written to the DB
        self.triggerMode = None      # The trigger mode
        self.mode = None             # Mode: cosmics, circulate, physics
        self.cosmics = False         # Is the trigger in a cosmics mode

        self.header = ""             # The table header

        self.useTrigList = False     # Whether we were given a trigger list or not
        self.TriggerListHLT = []     # All the HLT triggers that we want to monitor
        self.TriggerListL1 = []      # All the L1 triggers that we want to monitor
        self.usableHLTTriggers = []  # Triggers in the triggerlist that are also active during this run
        self.otherHLTTriggers = []   # Triggers active during the run but that we don't have a fit for
        self.usableL1Triggers = []
        self.otherL1Triggers = []
        self.redoTList = True        # Whether we need to update the trigger lists
        self.useAll = False          # If true, we will plot out the rates for all the triggers
        self.useL1 = False           # If true, we monitor the L1 triggers too

        self.percAccept = 50.0       # The percent deviation that is acceptable

        self.normal = 0
        self.bad = 0
        self.total = 0

    def getHeader(self, haveHLT, haveL1):
        # Define spacing and header
        maxNameHLT = 0
        maxNameL1 = 0
        if haveHLT: maxNameHLT = max([len(trigger) for trigger in self.TriggerListHLT])
        if haveL1 : maxNameL1 = max([len(trigger) for trigger in self.TriggerListL1])
        maxName = max([maxNameHLT, maxNameL1])
        self.spacing = [maxName + 5, 14, 14, 14, 14, 20]
        self.header += stringSegment("* TRIGGER NAME", self.spacing[0])
        self.header += stringSegment("* ACTUAL", self.spacing[1])
        self.header += stringSegment("* EXPECTED", self.spacing[2])
        self.header += stringSegment("* % DIFF", self.spacing[3])
        self.header += stringSegment("* AVE PS", self.spacing[4])
        self.header += stringSegment("* COMMENTS", self.spacing[5])
        self.hlength = sum(self.spacing)
        
    def run(self):
        # Load the fit and trigger list
        haveHLT = (self.fitFileHLT != "")
        haveL1 = (self.fitFileL1 != "")
        if haveHLT: self.InputFitHLT = self.loadFit(self.fitFileHLT)
        if haveL1 : self.InputFitL1 = self.loadFit(self.fitFileL1)

        if self.useTrigList: pass # Only using triggers in the current trigger list
        else:
            if haveHLT: self.TriggerListHLT = self.InputFitHLT.keys()
            if haveL1 : self.TriggerListL1 = self.InputFitL1.keys()

        if haveHLT and len(self.InputFitHLT)==0: haveHLT = False
        if haveL1 and len(self.InputFitL1)==0: haveL1 = False

        # Get run info: The current run number, if the detector is collecting (?), if the data is good (?), and the trigger mode
        if not self.assignedNum:
            self.runNumber, isCol, isGood, mode = self.parser.getLatestRunInfo()
            self.triggerMode = mode[0]
            # Info message
            print "The current run number is %s." % (self.runNumber)

        self.getHeader(haveHLT, haveL1)
        
        # If we are observing a single run from the past
        if self.assignedNum:
            self.triggerMode = self.parser.getTriggerMode(self.runNumber)[0]
            self.runLoop()
            return

        # Run as long as we can
        self.redoTList = True
        while True:
            # Check if we are still in the same run, get trigger mode
            self.lastRunNumber = self.runNumber
            self.runNumber, isCol, isGood, mode = self.parser.getLatestRunInfo()
            # Run the main functionality
            self.runLoop()      
            # Sleep before re-querying
            self.sleepWait()
        # This loop is infinite, the user must forcefully exit

    def runLoop(self):
        # Reset counting variable
        self.total = 0
        self.normal = 0
        self.bad = 0
        
        if self.lastRunNumber != self.runNumber:
            print "Starting a new run: Run %s" % (self.runNumber)
            redoTList = True # Re-do trigger lists
            
        # Check what mode we are in
        self.cosmics = False
        if self.triggerMode.find("cosmics") > -1:
            self.cosmics = True
            self.mode = "cosmics"
        elif self.triggerMode.find("circulate") > -1:
            self.mode = "circulate"
        elif self.triggerMode.find("collisions") > -1:
            self.mode = "collisions"
        elif self.triggerMode == "MANUAL":
            self.mode = "MANUAL"
        else: self.mode = "other"
        
        # Get Rates: [triggerName][LS] { raw rate, prescale }
        self.HLTRates = self.parser.getRawRates(self.runNumber, self.latestLS)
        self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.latestLS)

        if len(self.HLTRates) == 0 or len(self.L1Rates) == 0:
            print "No new information can be retrieved. Waiting..."
            return
        
        # Construct (or reconstruct) trigger lists
        if self.redoTList:
            self.redoTList = False
            for trigger in self.HLTRates.keys():
                if not self.InputFitHLT is None and self.InputFitHLT.has_key(trigger):
                    self.usableHLTTriggers.append(trigger)
                else:
                    self.otherHLTTriggers.append(trigger)
            for trigger in self.L1Rates.keys():
                if not self.InputFitL1 is None and self.InputFitL1.has_key(trigger):
                    self.usableL1Triggers.append(trigger)
                else:
                    self.otherL1Triggers.append(trigger)
                    
        # Find the latest LS
        if len(self.HLTRates)>0: Rates = self.HLTRates
        elif len(self.L1Rates)>0: Rates = self.L1Rates

        trig = Rates.keys()[0]
        self.lastLS = self.latestLS
        self.latestLS = max(Rates[trig].keys())
        
        # TODO: Deal with starting a new run
        
        # If there are lumisection to show, print info for them
        if self.latestLS > self.lastLS:
            self.printHLTTable()
        else:
            print "Not enough lumisections. Last LS was %s, current LS is %s. Waiting." % (self.lastLS, self.latestLS)
                
    # Use: Retrieves information and prints it in table form
    # Returns: (void)
    def printHLTTable(self):
        # Print the header of the table
        print "\n\n", '*' * self.hlength
        print "INFORMATION:"
        print "Run Number: %s" % (self.runNumber)
        print "LS Range: %s - %s" % (self.lastLS+1, self.latestLS)
        print "Trigger Mode: %s (%s)" % (self.triggerMode, self.mode)

        self.total = 0
        self.normal = 0
        self.bad = 0
        
        # Print the header
        print '*' * self.hlength
        print self.header

        # Get the inst lumi
        aveLumi = 0
        if not self.cosmics:
            lumiData = self.parser.getLumiInfo(self.runNumber, self.lastLS)
            # Find the average lumi since we last checked
            count = 0
            # Get luminosity (only for non-cosmic runs)
            for LS, instLumi, _ in lumiData:
                if not instLumi is None:
                    aveLumi += instLumi
                    count += 1
            if count == 0:
                aveLumi = "NONE"
                expected = "NONE"
            else: aveLumi /= float(count)

        # Print the triggers that we can make predictions for

        if len(self.usableHLTTriggers)>0:
            print '*' * self.hlength
            print "Predictable HLT Triggers (ones we have a fit for)"
            print '*' * self.hlength
        for trigger in self.usableHLTTriggers:
            self.L1 = False
            self.printTriggerData(trigger, self.mode=="collisions", aveLumi)
        if len(self.usableL1Triggers)>0:
            print '*' * self.hlength
            print "Predictable L1 Triggers (ones we have a fit for)"
            print '*' * self.hlength
        for trigger in self.usableL1Triggers:
            self.L1 = True
            self.printTriggerData(trigger, self.mode=="collisions", aveLumi)
        if self.useAll:
            print '*' * self.hlength
            print "Unpredictable HLT Triggers (ones we have no fit for)"
            print '*' * self.hlength
            self.L1 = False
            for trigger in self.otherHLTTriggers:
                self.printTriggerData(trigger,False)
        if self.useL1:
            print '*' * self.hlength
            print "Unpredictable L1 Triggers (ones we have no fit for)"
            print '*' * self.hlength
            self.L1 = True
            for trigger in self.otherL1Triggers:
                self.printTriggerData(trigger,False)

        #if self.useL1:
        #    print '*' * self.hlength
        #    self.printL1TriggerData()

        # Closing information
        print '*' * self.hlength
        print "SUMMARY:"
        print "Total Triggers: %s   |   Triggers in Normal Range: %s   |   Triggers outside Normal Range: %s" % (self.total, self.normal, self.bad)
        print "Ave iLumi: %s" % (aveLumi)
        print '*' * self.hlength
        
    # Use: Prints a table, not making a prediction (Because we are in cosmics mode)
    # Returns: (void)
    def printCosmicsTable(self):
        # Print the header of the table
        print "\n\n", '*' * self.hlength
        print "INFORMATION:"
        print "Run Number: %s" % (self.runNumber)
        print "LS Range: %s - %s" % (self.lastLS+1, self.latestLS)
        print "Trigger Mode: %s (%s)" % (self.triggerMode, self.mode)
        
        # Print the header
        print '*' * self.hlength
        print self.header
        print '*' * self.hlength

        # Print all the trigger info
        for trigger in self.TriggerListHLT:
            self.L1 = False
            if trigger in self.HLTRates.keys(): 
                self.printTriggerData(trigger, False)
        if len(self.TriggerListL1)>0: print '*' * self.hlength
        self.L1 = True
        for trigger in self.TriggerListL1:
            if trigger in self.L1Rates.keys():
                self.printTriggerData(trigger, False)
        if self.useAll:
            print '*' * self.hlength
            self.L1 = False
            for trigger in self.otherHLTTriggers:
                self.printTriggerData(trigger,False)
            if len(self.otherL1Triggers)>0: print '*' * self.hlength
            self.L1 = True
            for trigger in self.otherL1Triggers:
                self.printTriggerData(trigger,False)

        if self.useL1:
            print '*' * self.hlength
            self.printL1TriggerData()
            

        # Closing information
        print '*' * self.hlength
        print "SUMMARY:"
        print "Total Triggers: %s" % (self.total)
        print '*' * self.hlength


    def printTriggerData(self, trigger, doPred=True, aveLumi=0):
        # If cosmics, don't do predictions
        if self.cosmics: doPred = False

        if not self.cosmics and doPred:
            if not aveLumi is None:
                expected = self.calculateRate(trigger, aveLumi)
            else: expected = None
             
        # Find the ave rate since the last time we checked
        aveRate = 0
        avePS = 0
        count = 0
        comment = "" # A comment

        Rates = {}
        Rates.update(self.HLTRates)
        Rates.update(self.L1Rates)

        for LS in Rates[trigger].keys():
            if Rates[trigger][LS][1] > 0: # If not prescaled to 0
                aveRate += Rates[trigger][LS][0]
                count += 1
                avePS += Rates[trigger][LS][1]
        if count > 0:
            aveRate /= count
            avePS /= count
        else: comment += "Trigger PS to 0"
        
        # Find the % diff
        if doPred:
            if expected == 0 or expected == "NONE": perc = "INF"
            else: perc = 100*(aveRate-expected)/expected
         
        # Print the info for this trigger
        self.total += 1
        if doPred:
            if perc != "INF" and abs(perc) > self.percAccept:
                write(bcolors.WARNING) # Write colored text
                self.bad += 1
            else: self.normal += 1

        info = stringSegment("* "+trigger, self.spacing[0])
        info += stringSegment("* "+"{0:.2f}".format(aveRate), self.spacing[1])
        
        if doPred and not self.cosmics:
            if expected != "NONE": info += stringSegment("* "+"{0:.2f}".format(expected), self.spacing[2])
            else: info += stringSegment("* NONE", self.spacing[2])
            if perc != "INF": info += stringSegment("* "+"{0:.2f}".format(perc), self.spacing[3])
            else: info += stringSegment("* INF", self.spacing[3])
            info += stringSegment("* "+"{0:.2f}".format(avePS), self.spacing[4])
        else:
            info += stringSegment("", sum(self.spacing[2:5]))
            #info += stringSegment("", self.spacing[3])
            #info += stringSegment("", self.spacing[4])

        info += stringSegment("* "+comment, self.spacing[5])
        print info
        if doPred:
            if perc != "INF" and abs(perc) > self.percAccept:
                write(bcolors.ENDC) # Stop writing colored text

    # Use: Gets the L1 raw rate data and prints it out in table form
    def printL1TriggerData(self):
        L1Rates = self.parser.getL1RawRates(self.runNumber, self.lastLS)

        for trigger in L1Rates:
            aveRate = 0.0  # Find the ave trigger rate
            avePS = 0.0    # Find the ave trigger PS
            count = 0
            comment = ""
            for LS in L1Rates[trigger]:
                #?# Will the rate ever be None?
                aveRate += L1Rates[trigger][LS][0]
                avePS += L1Rates[trigger][LS][1]
                count += 1
            if avePS == 0: comment = "Trigger PS to 0"
            aveRate /= count
            avePS /= count

            info = stringSegment("* "+trigger, self.spacing[0])
            info += stringSegment("* "+"{0:.2f}".format(aveRate), self.spacing[1])
            info += stringSegment("", sum(self.spacing[2:4]))
            info += stringSegment("* "+"{0:.2f}".format(avePS), self.spacing[4])
            info += stringSegment("* "+comment, self.spacing[5])

            print info
        print '*' * self.hlength
            
    # Use: Sleeps and prints out waiting dots
    def sleepWait(self):
        print "Sleeping for 60 sec before next query  "
        for iSleep in range(20):
            write(".")
            sys.stdout.flush()
            time.sleep(3)
        sys.stdout.flush()
        print ""
            
    # Use: Loads the fit data from the fit file
    # Parameters:
    # -- fitFile: The file that the fit data is stored in (a pickle file)
    # Returns: The input fit data
    def loadFit(self, fileName):
        if fileName == "":
            return None
        InputFit = {} # Initialize InputFit (as an empty dictionary)
        # Try to open the file containing the fit info
        try:
            pkl_file = open(fileName, 'rb')
            InputFit = pickle.load(pkl_file)
            pkl_file.close()
        except:
            # File failed to open
            print "Error: could not open fit file: %s" % (fileName)
        return InputFit

    # Use: Calculates the expected rate for a trigger at a given ilumi based on our input fit
    def calculateRate(self, triggerName, ilum):
        # Make sure we have a fit for the trigger
        if not self.L1 and (self.InputFitHLT is None or not self.InputFitHLT.has_key(triggerName)):
            return 0
        elif self.L1 and ((self.InputFitL1 is None) or self.InputFitL1.has_key(triggerName)):
            return 0
        # Get the param list
        if self.L1: paramlist = self.InputFitL1[triggerName]
        else: paramlist = self.InputFitHLT[triggerName]
        # Calculate the rate
        if paramlist[0]=="exp": funcStr = "%s + %s*expo(%s+%s*x)" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Exponential
        else: funcStr = "%s+x*(%s+ x*(%s+x*%s))" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Polynomial
        fitFunc = TF1("Fit_"+triggerName, funcStr)
        return fitFunc.Eval(ilum)

## ----------- End of class ShiftMonitor ------------ ##

if __name__ == "__main__":
    parser = CommandLineParser()
    parser.parseArgs()
    #try:
    parser.run()
    #except:
    #    print "\nExiting. Goodbye..."
