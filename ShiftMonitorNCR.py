#######################################################
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 13, 2015
# Last Modified: July 16, 2015 by Nathaniel Rupprecht
#
# Dependencies: DBParser.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
from DBParser import *
from ROOT import TF1
import cPickle as pickle
import sys
import time
# For colors
from termcolor import *
from colors import *
# For getting command line options
import getopt
# For mail alerts
from mailAlert import *

def stringSegment(strng, tot):
    string = str(strng)
    for x in range(0, tot-len(str(strng))):
        string += " "
    return string

# Alias for sys.stdout.write
write = sys.stdout.write

# Class ShiftMonitor
class ShiftMonitor:

    def __init__(self):
        # Fits and fit files
        self.fitFileHLT = ""         # The fit file
        self.fitFileL1 = ""          # The fit file for L1 triggers
        self.InputFitHLT = None      # The fit information for the HLT triggers
        self.InputFitL1 = None       # The fit information for the L1 triggers
        # DBParser
        self.parser = DBParser()     # A database parser
        # Rates
        self.HLTRates = None         # HLT rates
        self.L1Rates = None          # L1 rates
        self.Rates = None            # Combined L1 and HLT rates
        # Run control
        self.lastRunNumber = -2      # The run number during the last segment
        self.runNumber = -1          # The number of the current run
        # Running over a previouly done run
        self.assignedNum = False     # If true, we look at the assigned run, not the latest run
        self.LSRange = []            # If we want to only look at a range of LS from the run
        # Lumisection control
        self.lastLS = 0              # The last LS that was processed last segment
        self.latestLS = 0            # The latest LS written to the DB
        self.slidingLS = -1          # The number of LS to average over, use -1 for no sliding LS
        self.useLSRange = False      # Only look at LS in a certain range
        # Mode
        self.triggerMode = None      # The trigger mode
        self.mode = None             # Mode: cosmics, circulate, physics
        self.cosmics = False         # Is the trigger in a cosmics mode
        # Columns header
        self.header = ""             # The table header
        # Triggers
        self.useTrigListHLT = False  # Whether we were given an HLT trigger list or not
        self.useTrigListL1 = False   # Whether we were given an L1 trigger list or not
        self.TriggerListHLT = None   # All the HLT triggers that we want to monitor
        self.TriggerListL1 = None    # All the L1 triggers that we want to monitor
        self.usableHLTTriggers = []  # HLT Triggers active during the run that we have fits for (and are in the HLT trigger list if it exists)
        self.otherHLTTriggers = []   # HLT Triggers active during the run that are not usable triggers
        self.usableL1Triggers = []   # L1 Triggers active during the run that have fits for (and are in the L1 trigger list if it exists)
        self.otherL1Triggers = []    # L1 Triggers active during that run that are not usable triggers
        self.redoTList = True        # Whether we need to update the trigger lists
        self.useAll = False          # If true, we will plot out the rates for all the triggers
        self.useL1 = False           # If true, we monitor the L1 triggers too
        self.removeZeros = True      # If true, we don't show triggers that have zero rate
        # Trigger behavior
        self.percAccept = 50.0       # The percent deviation that is acceptable
        self.normal = 0
        self.bad = 0
        self.total = 0
        self.badRates = {}              # A dictionary: [ trigger name ] { num consecutive bad , whether the trigger was bad last time we checked }
        self.recordAllBadTriggers = {}  # A dictionary: [ trigger name ] < total times the trigger was bad >
        self.maxCBR = 4                 # The maximum consecutive bad runs that we can have in a row
        self.displayBadRates = 0        # The number of bad rates we should show in the summary. We use -1 for all

    # Use: Formats the header string
    # Returns: (void)
    def getHeader(self):
        # Define spacing and header
        maxNameHLT = 0
        maxNameL1 = 0
        if len(self.usableHLTTriggers)>0 or len(self.otherHLTTriggers)>0:
            maxNameHLT = max([len(trigger) for trigger in self.usableHLTTriggers+self.otherHLTTriggers])
        if len(self.usableL1Triggers)>0 or len(self.otherL1Triggers)>0:
            maxNameL1 = max([len(trigger) for trigger in self.usableL1Triggers+self.otherL1Triggers])
        
        maxName = max([maxNameHLT, maxNameL1])
        if maxName == 0: maxName = 90
        
        self.spacing = [maxName + 5, 14, 14, 14, 14, 0]
        self.spacing[5] = max( [ 181 - sum(self.spacing), 0 ] )
        
        self.header += stringSegment("* TRIGGER NAME", self.spacing[0])
        self.header += stringSegment("* ACTUAL", self.spacing[1])
        self.header += stringSegment("* EXPECTED", self.spacing[2])
        self.header += stringSegment("* % DIFF", self.spacing[3])
        self.header += stringSegment("* AVE PS", self.spacing[4])
        self.header += stringSegment("* COMMENTS", self.spacing[5])
        self.hlength = sum(self.spacing)

    # Use: Runs the program
    # Returns: (void)
    def run(self):
        # Load the fit and trigger list
        haveHLT = (self.fitFileHLT != "")
        haveL1 = (self.fitFileL1 != "")
        if haveHLT: self.InputFitHLT = self.loadFit(self.fitFileHLT)
        if haveL1 : self.InputFitL1 = self.loadFit(self.fitFileL1)
        # If there aren't preset trigger lists, use all the triggers that we can fit
        if self.useTrigListHLT: pass # Only using triggers in the current trigger list
        elif haveHLT: self.TriggerListHLT = self.InputFitHLT.keys()
        if self.useTrigListL1: pass
        elif haveL1: self.TriggerListL1 = self.InputFitL1.keys()

        if haveHLT and len(self.InputFitHLT)==0: haveHLT = False
        if haveL1 and len(self.InputFitL1)==0: haveL1 = False

        # Get run info: The current run number, if the detector is collecting (?), if the data is good (?), and the trigger mode
        if not self.assignedNum:
            self.runNumber, isCol, isGood, mode = self.parser.getLatestRunInfo()
            self.triggerMode = mode[0]
            # Info message
            print "The current run number is %s." % (self.runNumber)
        # If we are observing a single run from the past
        if self.assignedNum:
            self.triggerMode = self.parser.getTriggerMode(self.runNumber)[0]
            self.runLoop()
            self.checkTriggers()
            return

        # Run as long as we can
        self.redoTList = True
        while True:
            # Check if we are still in the same run, get trigger mode
            self.lastRunNumber = self.runNumber
            self.runNumber, isCol, isGood, mode = self.parser.getLatestRunInfo()
            # Run the main functionality
            self.runLoop()      
            # Check for bad triggers
            self.checkTriggers()
            # Sleep before re-querying
            self.sleepWait()
        # This loop is infinite, the user must forcefully exit

    # Use: The main body of the main loop, checks the mode, creates trigger lists, prints table
    # Returns: (void)
    def runLoop(self):
        # Reset counting variable
        self.total = 0
        self.normal = 0
        self.bad = 0
        # If we have started a new run
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
        if not self.useLSRange:
            self.HLTRates = self.parser.getRawRates(self.runNumber, self.latestLS)
            self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.latestLS)
        else:
            self.HLTRates = self.parser.getRawRates(self.runNumber, self.LSRange[0]-1)
            self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.LSRange[0]-1)
        self.Rates = {}
        self.Rates.update(self.HLTRates)
        self.Rates.update(self.L1Rates)
        
        # Make sure there is info to use
        if len(self.HLTRates) == 0 or len(self.L1Rates) == 0:
            print "No new information can be retrieved. Waiting..."
            return
        
        # Construct (or reconstruct) trigger lists
        if self.redoTList:
            self.redoTList = False
            # Reset bad rate records
            self.badRates = {}           # A dictionary: [ trigger name ] < num consecutive bad >
            self.recordAllBadRates = {}  # A dictionary: [ trigger name ] < total times the trigger was bad >
            # Re-make trigger lists
            for trigger in self.HLTRates.keys():
                if (not self.InputFitHLT is None and self.InputFitHLT.has_key(trigger)) and \
                (not self.TriggerListHLT is None and trigger in self.TriggerListHLT):
                    self.usableHLTTriggers.append(trigger)
                else: self.otherHLTTriggers.append(trigger)
            for trigger in self.L1Rates.keys():
                if (not self.InputFitL1 is None and self.InputFitL1.has_key(trigger)) and \
                (not self.TriggerListL1 is None and trigger in self.TriggerListL1):
                    self.usableL1Triggers.append(trigger)
                else: self.otherL1Triggers.append(trigger)
            self.getHeader()
                    
        # Find the latest LS
        if len(self.HLTRates)>0: Rates = self.HLTRates
        elif len(self.L1Rates)>0: Rates = self.L1Rates

        trig = Rates.keys()[0]
        self.lastLS = self.latestLS
        self.latestLS = max(Rates[trig].keys())

        if self.useLSRange: # Adjust runs so we only look at those in our range
            self.slidingLS = -1 # No sliding LS window
            self.lastLS = max( [self.lastLS, self.LSRange[0]-1] )
            self.latestLS = min( [self.latestLS, self.LSRange[1] ] )
        
        # TODO: Deal with starting a new run
        
        # If there are lumisection to show, print info for them
        if self.latestLS > self.lastLS:
            self.printTable()
        else:
            print "Not enough lumisections. Last LS was %s, current LS is %s. Waiting." % (self.lastLS, self.latestLS)
                
    # Use: Retrieves information and prints it in table form
    # Returns: (void)
    def printTable(self):
        if self.slidingLS == -1:
            startLS = self.lastLS
        else: startLS = max( [0, self.latestLS-self.slidingLS ] )
        # Print the header of the table
        print "\n\n", '*' * self.hlength
        print "INFORMATION:"
        print "Run Number: %s" % (self.runNumber)
        print "LS Range: %s - %s" % (startLS+1, self.latestLS)
        print "Trigger Mode: %s (%s)" % (self.triggerMode, self.mode)
        # Reset variable
        self.total = 0
        self.normal = 0
        self.bad = 0
        # Print the header
        print '*' * self.hlength
        print self.header
        # Get the inst lumi
        aveLumi = 0
        physicsActive = False # True if we have at least 1 LS with lumi and physics bit true
        if not self.cosmics:
            lumiData = self.parser.getLumiInfo(self.runNumber, startLS)
            # Find the average lumi since we last checked
            count = 0
            # Get luminosity (only for non-cosmic runs)
            for LS, instLumi, physics in lumiData:
                # If we are watching a certain range, throw out other LS
                if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
                # Average our instLumi
                if not instLumi is None and physics:
                    physicsActive = True
                    aveLumi += instLumi
                    count += 1
            if count == 0:
                aveLumi = "NONE"
                expected = "NONE"
            else: aveLumi /= float(count)
        # We only do predictions when there were physics active LS in a collisions run
        doPred = physicsActive and self.mode=="collisions"
        # Print the triggers that we can make predictions for
        if len(self.usableHLTTriggers)>0:
            print '*' * self.hlength
            print "Predictable HLT Triggers (ones we have a fit for)"
            print '*' * self.hlength
        for trigger in self.usableHLTTriggers:
            self.L1 = False
            self.printTriggerData(trigger, doPred, aveLumi)
        if len(self.usableL1Triggers)>0:
            print '*' * self.hlength
            print "Predictable L1 Triggers (ones we have a fit for)"
            print '*' * self.hlength
        for trigger in self.usableL1Triggers:
            self.L1 = True
            self.printTriggerData(trigger, doPred, aveLumi)
        # Print the triggers that we can't make predictions for
        if self.useAll:
            print '*' * self.hlength
            print "Unpredictable HLT Triggers (ones we have no fit for or do not try to fit)"
            print '*' * self.hlength
            self.L1 = False
            for trigger in self.otherHLTTriggers:
                self.printTriggerData(trigger,False)
        if self.useL1:
            print '*' * self.hlength
            print "Unpredictable L1 Triggers (ones we have no fit for or do not try to fit)"
            print '*' * self.hlength
            self.L1 = True
            for trigger in self.otherL1Triggers:
                self.printTriggerData(trigger,False)

        # Closing information
        print '*' * self.hlength
        print "SUMMARY:"
        print "Total Triggers: %s" % (self.total)
        if self.mode=="collisions": print "Triggers in Normal Range: %s   |   Triggers outside Normal Range: %s" % (self.normal, self.bad)
        print "Ave iLumi: %s" % (aveLumi)
        print '*' * self.hlength

    # Use: Prints out a row in the monitor table
    # Arguments:
    # -- trigger : The name of the trigger
    # -- doPred  : Whether we should try to make a prediction
    # -- aveLumi : The ave lumi for the LS's
    # Returns: (void)
    def printTriggerData(self, trigger, doPred=True, aveLumi=0):
        # If cosmics, don't do predictions
        if self.cosmics: doPred = False
        # Calculate rate
        if not self.cosmics and doPred:
            if not aveLumi is None:
                expected = self.calculateRate(trigger, aveLumi)
            else: expected = None
        # Find the ave rate since the last time we checked
        aveRate = 0
        avePS = 0
        count = 0
        comment = "" # A comment

        for LS in self.Rates[trigger].keys():
            # If using a LSRange
            if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
            # Average the rate
            if self.Rates[trigger][LS][1] > 0: # If not prescaled to 0
                aveRate += self.Rates[trigger][LS][0]
                count += 1
                avePS += self.Rates[trigger][LS][1]
        if count > 0:
            aveRate /= count
            avePS /= count
        else: comment += "Trigger PS to 0"
        # Returns if we are not making predictions for this trigger and we are throwing zeros
        if not doPred and self.removeZeros and aveRate==0:
            return
        
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
                # Record if a trigger was bad
                if not self.recordAllBadRates.has_key(trigger):
                    self.recordAllBadRates[trigger] = 0
                self.recordAllBadRates[trigger] += 1
                # Record consecutive bad rates
                if not self.badRates.has_key(trigger):
                    self.badRates[trigger] = [0, True]
                last = self.badRates[trigger]
                self.badRates[trigger] = [ last[0]+1, True ]
            else:
                self.normal += 1
                # Remove warning from badRates
                if self.badRates.has_key(trigger):
                    self.badRates[trigger] = [ 0, False ]

        info = stringSegment("* "+trigger, self.spacing[0])
        info += stringSegment("* "+"{0:.2f}".format(aveRate), self.spacing[1])
        
        if doPred and not self.cosmics:
            if expected != "NONE": info += stringSegment("* "+"{0:.2f}".format(expected), self.spacing[2])
            else: info += stringSegment("* NONE", self.spacing[2])
            if perc != "INF": info += stringSegment("* "+"{0:.2f}".format(perc), self.spacing[3])
            else: info += stringSegment("* INF", self.spacing[3])
        else: info += stringSegment("", sum(self.spacing[2:4]))
        info += stringSegment("* "+"{0:.2f}".format(avePS), self.spacing[4])
        info += stringSegment("* "+comment, self.spacing[5])
        print info
        if doPred:
            if perc != "INF" and abs(perc) > self.percAccept:
                write(bcolors.ENDC) # Stop writing colored text

    # Use: Checks triggers to make sure none have been bad for to long
    def checkTriggers(self):
        if self.displayBadRates != 0:
            count = 0
            if self.displayBadRates != -1: write("First %s triggers that are bad: " % (self.displayBadRates)) 
            else: write("All bad triggers: ")
            for trigger in self.badRates:
                if self.badRates[trigger][1]:
                    count += 1
                    write(trigger)
                    if count != self.displayBadRates-1:
                        write(", ")
                if count == self.displayBadRates:
                    write(".....")
                    break
            print ""

        # Print warnings for triggers that have been repeatedly misbehaving
        for trigger in self.badRates:
            if self.badRates[trigger][1]:
                if self.badRates[trigger][1] and self.badRates[trigger][0] >= self.maxCBR:
                    print "Trigger %s has been out of line for more then %s minutes" % (trigger, self.maxCBR)
                elif self.badRates[trigger][0] >= self.maxCBR-1:
                    print "Warning: Trigger %s has been out of line for more then %s minutes" % (trigger, self.maxCBR-1)
        ##** TODO: incorporate mailed warnings
        
            
    # Use: Sleeps and prints out waiting dots
    # Returns: (void)
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
    # Returns: The expected trigger rate (a float)
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

    def sendMail(self):
        pass
        #mail = "Run: %d, Lumisections: %s - %s \n \n" %(HeadParser.RunNumber,str(HeadLumiRange[0]),str(HeadLumiRange[-1]))
        #mail += "The following path rate(s) are deviating from expected values: \n"
        #for index,entry in enumerate(core_data):
        #    if Warn[index]:
        #        mail += " - %-30s \tmeasured rate: %-6.2f Hz, expected rate: %-6.2f Hz, difference: %-4.0f%%\n" % (core_data[index][0], core_data[index][1], core_data[index][2], core_data[index][3])
        #mailAlert(mail)

## ----------- End of class ShiftMonitor ------------ ##
