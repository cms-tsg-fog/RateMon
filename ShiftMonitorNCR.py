#######################################################
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 13, 2015
# Last Modified: August 6, 2015 by Nathaniel Rupprecht
#
# Dependencies: DBParser.py, mailAlert.py
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

# Use: Writes a string in a fixed length margin string (pads with spaces)
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
        self.fitFileHLT = ""            # The fit file
        self.fitFileL1 = ""             # The fit file for L1 triggers
        self.InputFitHLT = None         # The fit information for the HLT triggers
        self.InputFitL1 = None          # The fit information for the L1 triggers
        # DBParser
        self.parser = DBParser()        # A database parser
        # Rates
        self.HLTRates = None            # HLT rates
        self.L1Rates = None             # L1 rates
        self.Rates = None               # Combined L1 and HLT rates
        # Run control
        self.lastRunNumber = -2         # The run number during the last segment
        self.runNumber = -1             # The number of the current run
        # Running over a previouly done run
        self.assignedNum = False        # If true, we look at the assigned run, not the latest run
        self.LSRange = []               # If we want to only look at a range of LS from the run
        self.simulate = False           # Simulate running through and monitoring a previous run
        # Lumisection control
        self.lastLS = 1                 # The last LS that was processed last segment
        self.currentLS = 1              # The latest LS written to the DB
        self.slidingLS = -1             # The number of LS to average over, use -1 for no sliding LS
        self.useLSRange = False         # Only look at LS in a certain range
        # Mode
        self.triggerMode = None         # The trigger mode
        self.mode = None                # Mode: cosmics, circulate, physics
        self.cosmics = False            # Is the trigger in a cosmics mode
        # Columns header
        self.header = ""                # The table header
        # Triggers
        self.useTrigListHLT = False     # Whether we were given an HLT trigger list or not
        self.useTrigListL1 = False      # Whether we were given an L1 trigger list or not
        self.TriggerListHLT = None      # All the HLT triggers that we want to monitor
        self.TriggerListL1 = None       # All the L1 triggers that we want to monitor
        self.usableHLTTriggers = []     # HLT Triggers active during the run that we have fits for (and are in the HLT trigger list if it exists)
        self.otherHLTTriggers = []      # HLT Triggers active during the run that are not usable triggers
        self.usableL1Triggers = []      # L1 Triggers active during the run that have fits for (and are in the L1 trigger list if it exists)
        self.otherL1Triggers = []       # L1 Triggers active during that run that are not usable triggers
        self.redoTList = True           # Whether we need to update the trigger lists
        self.useAll = False             # If true, we will print out the rates for all the HLT triggers
        self.useL1 = False              # If true, we will print out the rates for all the L1 triggers
        # Restrictions
        self.removeZeros = True         # If true, we don't show triggers that have zero rate
        self.requireLumi = False        # If true, we only display tables when aveLumi is not None
        # Trigger behavior
        self.percAccept = 50.0          # The acceptence for % diff
        self.devAccept = 1.5            # The acceptence for deviation
        self.normal = 0
        self.bad = 0
        self.total = 0
        self.badRates = {}              # A dictionary: [ trigger name ] { num consecutive bad , whether the trigger was bad last time we checked }
        self.recordAllBadTriggers = {}  # A dictionary: [ trigger name ] < total times the trigger was bad >
        self.maxCBR = 4                 # The maximum consecutive bad runs that we can have in a row
        self.displayBadRates = 0        # The number of bad rates we should show in the summary. We use -1 for all
        self.usePerDiff = False         # Whether we should identify bad triggers by perc diff or deviatoin

        self.quiet = False              # Prints fewer messages in this mode
        self.noColors = False           # Special formatting for if we want to dump the table to a file

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

        # Make the name spacing at least 90
        maxName = max([maxNameHLT, maxNameL1, 90])
        
        self.spacing = [maxName + 5, 14, 14, 14, 14, 14, 0]
        self.spacing[5] = max( [ 181 - sum(self.spacing), 0 ] )
        
        self.header += stringSegment("* TRIGGER NAME", self.spacing[0])
        self.header += stringSegment("* ACTUAL", self.spacing[1])
        self.header += stringSegment("* EXPECTED", self.spacing[2])
        self.header += stringSegment("* % DIFF", self.spacing[3])
        self.header += stringSegment("* DEVIATION", self.spacing[4])
        self.header += stringSegment("* AVE PS", self.spacing[5])
        self.header += stringSegment("* COMMENTS", self.spacing[6])
        self.hlength = 181 #sum(self.spacing)

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
            self.runNumber, _, _, mode = self.parser.getLatestRunInfo()
            self.triggerMode = mode[0]
            # Info message
            print "The current run number is %s." % (self.runNumber)
        # If we are observing a single run from the past
        elif not self.simulate:
            self.triggerMode = self.parser.getTriggerMode(self.runNumber)[0]
            self.runLoop()
            self.checkTriggers()
            return

        # If we are simulating a previous run
        if self.simulate:
            self.simulateRun()
            return

        # Run as long as we can
        self.setMode()
        self.redoTList = True
        while True:
            # Check if we are still in the same run, get trigger mode
            self.lastRunNumber = self.runNumber
            self.runNumber, _, _, mode = self.parser.getLatestRunInfo()
            # Run the main functionality
            self.runLoop()      
            # Check for bad triggers
            self.checkTriggers()
            # Sleep before re-querying
            self.sleepWait()
        # This loop is infinite, the user must forcefully exit

    def simulateRun(self):
        modTime = 0
        # Get the rates
        self.triggerMode = self.parser.getTriggerMode(self.runNumber)[0]
        # Set the trigger mode
        self.setMode()
        # Get the rates for the entire run
        self.getRates()
        # Find the max LS for that run
        trig = self.Rates.keys()[0]
        self.lastLS = self.currentLS
        maxLS = max(self.Rates[trig].keys())
        # Simulate the run
        self.lastRunNumber = self.runNumber
        self.lastLS = 1
        while self.currentLS < maxLS:
            modTime += 23.3
            self.currentLS += 1
            if modTime > 60 or self.currentLS == maxLS:
                modTime -= 60
                # Print table
                self.runLoop()
                # Check for bad triggers
                self.checkTriggers()
                # We would sleep here if this was an online run
                if not self.quiet: print "Simulating 60 s of sleep..."
                self.lastLS = self.currentLS
        print "End of simulation"


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
            self.lastRunNumber = self.runNumber
            self.lastLS = 1
            self.currentLS = 1
            redoTList = True # Re-do trigger lists            
            # Check what mode we are in
            self.setMode()
        
        # Get Rates: [triggerName][LS] { raw rate, prescale }
        if not self.simulate: self.getRates()
        
        # Make sure there is info to use
        if len(self.HLTRates) == 0 or len(self.L1Rates) == 0:
            print "No new information can be retrieved. Waiting... (There may be no new LS, or run active may be false)"
            return
        
        # Construct (or reconstruct) trigger lists
        if self.redoTList:
            self.redoTriggerLists()

        # If we are not simulating a previous run. Otherwise, we already se lastLS and currentLS
        if not self.simulate:
            lslist = []
            for trig in self.Rates.keys():
                if len(self.Rates[trig])>0: lslist.append(max(self.Rates[trig]))
            # Update lastLS
            self.lastLS = self.currentLS
            
            if len(lslist)>0: self.currentLS = max(lslist)
            
            #if len(self.Rates[trig].keys())>0:
            #    self.lastLS = max( [ self.lastLS, min(self.Rates[trig].keys()) ] )
            #    self.currentLS = max(self.Rates[trig].keys())
            
            try: self.currentLS = max(self.Rates[trig].keys())
            except:
                self.lastLS = self.currentLS
                print "rates table empty"

            if self.useLSRange: # Adjust runs so we only look at those in our range
                self.slidingLS = -1 # No sliding LS window
                self.lastLS = max( [self.lastLS, self.LSRange[0]] )
                self.currentLS = min( [self.currentLS, self.LSRange[1] ] )
        # If there are lumisection to show, print info for them
        if self.currentLS > self.lastLS: self.printTable()
        else: print "Not enough lumisections. Last LS was %s, current LS is %s. Waiting." % (self.lastLS, self.currentLS)

    def setMode(self):
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

    # Use: Remakes the trigger lists
    def redoTriggerLists(self):
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

    # Use: Gets the rates for the lumisections we want
    def getRates(self):
        if not self.useLSRange:
            self.HLTRates = self.parser.getRawRates(self.runNumber, self.lastLS)
            self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.lastLS)
        else:
            self.HLTRates = self.parser.getRawRates(self.runNumber, self.LSRange[0], self.LSRange[1])
            self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.LSRange[0], self.LSRange[1])
        self.Rates = {}
        self.Rates.update(self.HLTRates)
        self.Rates.update(self.L1Rates)
                
    # Use: Retrieves information and prints it in table form
    def printTable(self):
        if self.slidingLS == -1:
            self.startLS = self.lastLS
        else: self.startLS = max( [0, self.currentLS-self.slidingLS ] )+1
        # Reset variable
        self.total = 0
        self.normal = 0
        self.bad = 0
        # Get the inst lumi
        aveLumi = 0
        physicsActive = False # True if we have at least 1 LS with lumi and physics bit true
        if not self.cosmics:
            lumiData = self.parser.getLumiInfo(self.runNumber, self.startLS, self.currentLS)
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
        # If we demand a non NONE ave lumi, check that here
        if self.requireLumi and aveLumi == "NONE":
            if not self.quiet: print "Ave Lumi is None for LS %s - %s, skipping." % (self.startLS, self.currentLS)
            return
        
        # We only do predictions when there were physics active LS in a collisions run
        doPred = physicsActive and self.mode=="collisions"
        # Print the header
        self.printHeader()
        # Print the triggers that we can make predictions for
        anytriggers = False
        if len(self.usableHLTTriggers)>0:
            print '*' * self.hlength
            print "Predictable HLT Triggers (ones we have a fit for)"
            print '*' * self.hlength
            anytriggers = True
        self.L1 = False
        self.printTableSection(self.usableHLTTriggers, doPred, aveLumi)
        if len(self.usableL1Triggers)>0:
            print '*' * self.hlength
            print "Predictable L1 Triggers (ones we have a fit for)"
            print '*' * self.hlength
            anytriggers = True
        self.L1 = True
        self.printTableSection(self.usableL1Triggers, doPred, aveLumi)
        # Print the triggers that we can't make predictions for
        if self.useAll:
            print '*' * self.hlength
            print "Unpredictable HLT Triggers (ones we have no fit for or do not try to fit)"
            print '*' * self.hlength
            self.L1 = False
            self.printTableSection(self.otherHLTTriggers, False)
            anytriggers = True
        if self.useL1:
            print '*' * self.hlength
            print "Unpredictable L1 Triggers (ones we have no fit for or do not try to fit)"
            print '*' * self.hlength
            self.L1 = True
            self.printTableSection(self.otherL1Triggers, False)
            anytriggers = True

        if not anytriggers:
            print '*' * self.hlength
            print "\n --- No useable triggers --- \n"

        # Print stream data
        StreamData = self.parser.getStreamData(self.runNumber, self.startLS, self.currentLS)
        print '*' * self.hlength
        streamSpacing = [ 50, 20, 25, 25, 25, 25 ]
        head = stringSegment("* Stream name", streamSpacing[0])
        head += stringSegment("* NLumis", streamSpacing[1])
        head += stringSegment("* Events", streamSpacing[2])
        head += stringSegment("* Stream rate (Hz)", streamSpacing[3])
        head += stringSegment("* Stream size (GB)", streamSpacing[4])
        head += stringSegment("* Stream bandwidth (GB/s)", streamSpacing[5])
        print head
        print '*' * self.hlength
        streamTable = ""
        for name in StreamData.keys():
            count = 0.0
            streamsize = 0
            aveBandwidth = 0
            aveRate = 0
            for LS, rate, size, bandwidth in StreamData[name]:
                streamsize += size
                aveRate += rate
                aveBandwidth += bandwidth
                count += 1
            if count > 0:
                aveRate /= count
                streamsize /= (1000000000.0)
                aveBandwidth /= (count*1000000000.0)
                row = stringSegment("* "+name, streamSpacing[0])
                row += stringSegment("* "+str(int(count)), streamSpacing[1])
                row += stringSegment("* "+str(int(aveRate*23.3*count)), streamSpacing[2])
                row += stringSegment("* "+"{0:.2f}".format(aveRate), streamSpacing[3])
                row += stringSegment("* "+"{0:.2f}".format(streamsize), streamSpacing[4])
                row += stringSegment("* "+"{0:.5f}".format(aveBandwidth), streamSpacing[5])
                streamTable += (row+"\n")
            else: pass
        if len(streamTable) > 0:
            print streamTable
        else: print "\n --- No streams to monitor --- \n"

        # Closing information
        print '*' * self.hlength
        print "SUMMARY:"
        print "Total Triggers: %s" % (self.total)
        if self.mode=="collisions": print "Triggers in Normal Range: %s   |   Triggers outside Normal Range: %s" % (self.normal, self.bad)
        print "Ave iLumi: %s" % (aveLumi)
        print '*' * self.hlength

    # Use: Prints the table header
    def printHeader(self):
        print "\n\n", '*' * self.hlength
        print "INFORMATION:"
        print "Run Number: %s" % (self.runNumber)
        print "LS Range: %s - %s" % (self.startLS, self.currentLS)
        print "Trigger Mode: %s (%s)" % (self.triggerMode, self.mode)
        print '*' * self.hlength
        print self.header
        
    # Use: Prints a section of a table, ie all the triggers in a trigger list (like usableHLTTriggers, otherHLTTriggers, etc)
    def printTableSection(self, triggerList, doPred, aveLumi=0):
        self.tableData = [] # A list of tuples, each a row in the table: ( { trigger, rate, predicted rate, sign of % diff, abs % diff, ave PS, comment } )
        for trigger in triggerList:
            self.getTriggerData(trigger, doPred, aveLumi)
        # Sort by % diff if need be
        if doPred:
            # [4] is % diff, [6] is deviation
            if self.usePerDiff: self.tableData.sort(key=lambda tup : tup[4])
            else: self.tableData.sort(key=lambda tup : tup[6])
        for trigger, rate, pred, sign, perdiff, dsign, dev, avePS, comment in self.tableData:
            info = stringSegment("* "+trigger, self.spacing[0])
            info += stringSegment("* "+"{0:.2f}".format(rate), self.spacing[1])
            if pred!="": info += stringSegment("* "+"{0:.2f}".format(pred), self.spacing[2])
            else: info += stringSegment("", self.spacing[2])
            if perdiff!="": info += stringSegment("* "+"{0:.2f}".format(sign*perdiff), self.spacing[3])
            else: info += stringSegment("", self.spacing[3])
            if dev!="": info += stringSegment("* "+"{0:.2f}".format(dsign*dev), self.spacing[4])
            else: info += stringSegment("", self.spacing[4])
            info += stringSegment("* "+"{0:.2f}".format(avePS), self.spacing[5])
            info += stringSegment("* "+comment, self.spacing[6])
            if (self.usePerDiff and perdiff!="INF" and perdiff!="" and perdiff>self.percAccept) \
                   or (dev!="INF" and dev!="" and dev>self.devAccept):
                if not self.noColors: write(bcolors.WARNING) # Write colored text 
                print info
                if not self.noColors: write(bcolors.ENDC)    # Stop writing colored text
            else: print info

    # Use: Gets a row of the table, self.tableData: ( { trigger, rate, predicted rate, sign of % diff, abs % diff, ave PS, comment } )
    # Parameters:
    # -- trigger : The name of the trigger
    # -- doPred  : Whether we want to make a prediction for this trigger
    # -- aveLumi : The average luminosity during the LS in question
    # Returns: (void)
    def getTriggerData(self, trigger, doPred, aveLumi):
        # If cosmics, don't do predictions
        if self.cosmics: doPred = False
        # Calculate rate
        if not self.cosmics and doPred:
            if not aveLumi is None:
                expected = self.calculateRate(trigger, aveLumi)
                mse = self.getMSE(trigger)
            else:
                expected = None
                mse = None
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
            # Make note if rate or PS are identically zero
            if aveRate == 0: comment += "Rate=0 "
            aveRate /= count
            avePS /= count
        else: comment += "PS=0"
        # Returns if we are not making predictions for this trigger and we are throwing zeros
        if not doPred and self.removeZeros and aveRate==0:
            return
        # We want this trigger to be in the table
        row = [trigger]
        row.append(aveRate)
        if doPred and not expected is None: row.append(expected)
        else: row.append("") # No predicted rate
        # Find the % diff
        if doPred:
            if expected == 0 or expected == "NONE":
                perc = "INF"
                dev = ""
                row.append(1)    # Sign of % diff
                row.append(perc) # abs % diff
                row.append(1)    # Sign of deviation
                row.append(dev)  # abs deviation
            else:
                diff = aveRate-expected
                perc = 100*diff/expected
                if mse!=0: dev = diff / mse
                else: dev = "INF"
                if perc>0: sign=1
                else: sign=-1
                row.append(sign)       # Sign of % diff
                row.append(abs(perc))  # abs % diff
                if mse>0: sign=1
                else: sign=-1
                row.append(sign)       # Sign of the deviation
                row.append(abs(dev))   # abs deviation
        else:
            row.append("") # No prediction, so no sign of a % diff
            row.append("") # No prediction, so no % diff
            row.append("") # No prediction, so no sign of deviation
            row.append("") # No prediction, so no deviation
        # Add the rest of the info to the row
        row.append(avePS)
        row.append(comment)
        # Add row to the table data
        self.tableData.append(row)
        # Check if the trigger is bad
        self.total += 1
        if doPred:
            if perc != "INF" and abs(perc) > self.percAccept:
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
                    print "Trigger %s has been out of line for more then %s minutes" % (trigger, self.badRates[trigger][0])
                elif self.badRates[trigger][0] >= self.maxCBR-1:
                    print "Warning: Trigger %s has been out of line for more then %s minutes" % (trigger, self.maxCBR-1)
        ##** TODO: incorporate mailed warnings
        
            
    # Use: Sleeps and prints out waiting dots
    def sleepWait(self):
        if not self.quiet: print "Sleeping for 60 sec before next query  "
        for iSleep in range(20):
            if not self.quiet: write(".")
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

    # Use: Gets the MSE of the fit
    def getMSE(self, triggerName):
        if not self.L1 and (self.InputFitHLT is None or not self.InputFitHLT.has_key(triggerName)):
            return 0
        elif self.L1 and ((self.InputFitL1 is None) or self.InputFitL1.has_key(triggerName)):
            return 0
        if self.L1: paramlist = self.InputFitL1[triggerName]
        else: paramlist = self.InputFitHLT[triggerName]
        return paramlist[5] # The MSE

    # Use: Sends an email alert
    def sendMail(self):
        pass
        #mail = "Run: %d, Lumisections: %s - %s \n \n" %(HeadParser.RunNumber,str(HeadLumiRange[0]),str(HeadLumiRange[-1]))
        #mail += "The following path rate(s) are deviating from expected values: \n"
        #for index,entry in enumerate(core_data):
        #    if Warn[index]:
        #        mail += " - %-30s \tmeasured rate: %-6.2f Hz, expected rate: %-6.2f Hz, difference: %-4.0f%%\n" % (core_data[index][0], core_data[index][1], core_data[index][2], core_data[index][3])
        #mailAlert(mail)

## ----------- End of class ShiftMonitor ------------ ##
