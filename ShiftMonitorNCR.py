#######################################################)
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 13, 2015
# Last Modified: August 17, 2015 by Nathaniel Rupprecht
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
import ROOT
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
from mailAlert import mailAlert

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
        # Suppress root warnings
        ROOT.gErrorIgnoreLevel = 7000
        # Fits and fit files
        self.fitFile = ""               # The fit file, can contain both HLT and L1 triggers
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
        self.displayRawRates = False    # display raw rates, to display prescaled rates, set = True
        # Triggers
        self.cosmics_triggerList = "monitorlist_COSMICS.list" #default list used when in cosmics mode
        self.collisions_triggerList = "monitorlist_COLLISIONS.list" #default list used when in cosmics mode 
        self.triggerList = ""           # A list of all the L1 and HLT triggers we want to monitor
        self.userSpecTrigList = False   #user specified trigger list 
        self.usableHLTTriggers = []     # HLT Triggers active during the run that we have fits for (and are in the HLT trigger list if it exists)
        self.otherHLTTriggers = []      # HLT Triggers active during the run that are not usable triggers
        self.usableL1Triggers = []      # L1 Triggers active during the run that have fits for (and are in the L1 trigger list if it exists)
        self.otherL1Triggers = []       # L1 Triggers active during that run that are not usable triggers
        self.redoTList = True           # Whether we need to update the trigger lists
        self.useAll = False             # If true, we will print out the rates for all the HLT triggers
        self.useL1 = False              # If true, we will print out the rates for all the L1 triggers
        self.totalHLTTriggers = 0       # The total number of HLT Triggers on the menu this run
        self.totalL1Triggers = 0        # The total number of L1 Triggers on the menu this run
        self.fullL1HLTMenu = []
        # Restrictions
        self.removeZeros = False         # If true, we don't show triggers that have zero rate
        self.requireLumi = False        # If true, we only display tables when aveLumi is not None
        # Trigger behavior
        self.percAccept = 50.0          # The acceptence for % diff
        self.devAccept = 3            # The acceptence for deviation
        self.badRates = {}              # A dictionary: [ trigger name ] { num consecutive bad , whether the trigger was bad last time we checked, rate, expected, dev }
        self.recordAllBadTriggers = {}  # A dictionary: [ trigger name ] < total times the trigger was bad >
        self.maxCBR = 1                 # The maximum consecutive db queries a trigger is allowed to deviate from prediction by specified amount before it's printed out
        self.displayBadRates = -1        # The number of bad rates we should show in the summary. We use -1 for all
        self.usePerDiff = False         # Whether we should identify bad triggers by perc diff or deviatoin
        self.sortRates = True           # Whether we should sort triggers by their rates
        # Trigger Rate
        self.maxHLTRate = 200          # The maximum prescaled rate we allow an HLT Trigger to have
        self.maxL1Rate = 30000           # The maximum prescaled rate we allow an L1 Trigger to have
        # Other options
        self.quiet = False              # Prints fewer messages in this mode
        self.noColors = False           # Special formatting for if we want to dump the table to a file
        self.sendMailAlerts = False     # Whether we should send alert mails
        self.showStreams = True         # Whether we should print stream information
        self.showPDs = False             # Whether we should print pd information
        self.totalStreams = 0           # The total number of streams
        self.maxStreamRate = 1000000       # The maximum rate we allow a "good" stream to have
        self.maxPDRate = 10000000       # The maximum rate we allow a "good" pd to have        
        

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
            # Recognize comments
            if triggerName[0]=='#': continue
            try:
                if not str(triggerName) in TriggerList:
                    TriggerList.append(stripVersion(str(triggerName)))
            except:
                print "Error parsing trigger name in file", fileName
        return TriggerList

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

        self.header = ""                # The table header
        self.header += stringSegment("* TRIGGER NAME", self.spacing[0])
        if (self.displayRawRates): self.header += stringSegment("* RAW [Hz]", self.spacing[1])
        else: self.header += stringSegment("* ACTUAL [Hz]", self.spacing[1])
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
        if self.fitFile!="":
            inputFit = self.loadFit(self.fitFile)
            for triggerName in inputFit:
                if triggerName[0:3]=="L1_":
                    if self.InputFitL1 is None: self.InputFitL1 = {}
                    self.InputFitL1[triggerName] = inputFit[triggerName]
                elif triggerName[0:4] =="HLT_":
                    if self.InputFitHLT is None: self.InputFitHLT = {}
                    self.InputFitHLT[triggerName] = inputFit[triggerName]
        
        # Sort trigger list into HLT and L1 trigger lists
        if self.triggerList!="":
            for triggerName in self.triggerList:
                if triggerName[0:3]=="L1_":
                    self.TriggerListL1.append(triggerName)
                else:
                    self.TriggerListHLT.append(triggerName)
        # If there aren't preset trigger lists, use all the triggers that we can fit
        else:
            if not self.InputFitHLT is None: self.TriggerListHLT = self.InputFitHLT.keys()
            if not self.InputFitL1 is None: self.TriggerListL1 = self.InputFitL1.keys()

        # Get run info: The current run number, if the detector is collecting (?), if the data is good (?), and the trigger mode
        if not self.assignedNum:
            self.runNumber, _, _, mode = self.parser.getLatestRunInfo()
            self.triggerMode = mode[0]
            # Info message
            print "The current run number is %s." % (self.runNumber)
        # If we are observing a single run from the past
        elif not self.simulate:
            self.triggerMode = self.parser.getTriggerMode(self.runNumber)[0]
            self.getRates()
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
            try:
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
            except KeyboardInterrupt:
                print "Quitting. Bye."
                break
            
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
        self.normal = 0
        self.bad = 0

        redoTList = False # Re-do trigger lists            
        # If we have started a new run
        if self.lastRunNumber != self.runNumber:
            print "Starting a new run: Run %s" % (self.runNumber)
            self.lastLS = 1
            self.currentLS = 0
            # Check what mode we are in
            self.setMode()
            self.getRates()
            self.redoTriggerLists()
            
        # Get Rates: [triggerName][LS] { raw rate, prescale }
        if not self.simulate: self.getRates()
        #Construct (or reconstruct) trigger lists
        if self.redoTList:
            self.redoTriggerLists()

        # Make sure there is info to use
        if len(self.HLTRates) == 0 and len(self.L1Rates) == 0:
            print "No new information can be retrieved. Waiting... (There may be no new LS, or run active may be false)"
            return
        
        # If we are not simulating a previous run. Otherwise, we already set lastLS and currentLS
        if not self.simulate:
            lslist = []
            for trig in self.Rates.keys():
                if len(self.Rates[trig])>0: lslist.append(max(self.Rates[trig]))
            # Update lastLS
            self.lastLS = self.currentLS
            # Update current LS
            if len(lslist)>0: self.currentLS = max(lslist)
            
            if self.useLSRange: # Adjust runs so we only look at those in our range
                self.slidingLS = -1 # No sliding LS window
                self.lastLS = max( [self.lastLS, self.LSRange[0]] )
                self.currentLS = min( [self.currentLS, self.LSRange[1] ] )
        # If there are lumisection to show, print info for them
        if self.currentLS > self.lastLS: self.printTable()
        else: print "Not enough lumisections. Last LS was %s, current LS is %s. Waiting." % (self.lastLS, self.currentLS)

    def setMode(self):
        self.triggerMode = self.parser.getTriggerMode(self.runNumber)[0]
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
        # Reset the trigger lists
        self.usableHLTTriggers = []
        self.otherHLTTriggers = []
        self.useableL1Triggers = []
        self.otherL1Triggers = []
        # Reset bad rate records
        self.badRates = {}           # A dictionary: [ trigger name ] { num consecutive bad, trigger bad last check, rate, expected, dev }
        self.recordAllBadRates = {}  # A dictionary: [ trigger name ] < total times the trigger was bad >

        #set trigger lists automatically based on mode
        if not self.useAll and not self.userSpecTrigList:
            if self.mode == "cosmics" or self.mode == "circulate":
                self.triggerList = self.loadTriggersFromFile(self.cosmics_triggerList)
                print "monitoring triggers in: ", self.cosmics_triggerList
            elif self.mode == "collisions":
                self.triggerList = self.loadTriggersFromFile(self.collisions_triggerList)
                print "monitoring triggers in: ", self.collisions_triggerList
            else:
                self.triggerList = ""
                print "No lists to monitor: trigger mode not recognized"

            self.TriggerListL1 = []
            self.TriggerListHLT = []
            for triggerName in self.triggerList:
                if triggerName[0:3]=="L1_":
                    self.TriggerListL1.append(triggerName)
                elif triggerName[0:4]=="HLT_":
                    self.TriggerListHLT.append(triggerName)

        # Re-make trigger lists
        for trigger in self.HLTRates.keys():
            if (not self.InputFitHLT is None and self.InputFitHLT.has_key(trigger)) and \
            (len(self.TriggerListHLT) !=0 and trigger in self.TriggerListHLT):
                self.usableHLTTriggers.append(trigger)
            elif trigger[0:4] == "HLT_" and (self.triggerList == "" or trigger in self.TriggerListHLT):
                self.otherHLTTriggers.append(trigger)
            elif (trigger[0:4] == "HLT_"): self.fullL1HLTMenu.append(trigger) 


        for trigger in self.L1Rates.keys():
            if (not self.InputFitL1 is None and self.InputFitL1.has_key(trigger)) and \
            (len(self.TriggerListL1) != 0 and trigger in self.TriggerListL1):
                self.usableL1Triggers.append(trigger)
            elif trigger[0:3] == "L1_" and (self.triggerList =="" or trigger in self.TriggerListL1):
                self.otherL1Triggers.append(trigger)
            elif (trigger[0:3] == "L1_"): self.fullL1HLTMenu.append(trigger) 
                        
        self.getHeader()

    # Use: Gets the rates for the lumisections we want
    def getRates(self):
        if not self.useLSRange:
            self.HLTRates = self.parser.getRawRates(self.runNumber, self.lastLS)
            self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.lastLS)
            self.streamData = self.parser.getStreamData(self.runNumber, self.lastLS)
            self.pdData = self.parser.getPrimaryDatasets(self.runNumber, self.lastLS)
        else:
            self.HLTRates = self.parser.getRawRates(self.runNumber, self.LSRange[0], self.LSRange[1])
            self.L1Rates = self.parser.getL1RawRates(self.runNumber, self.LSRange[0], self.LSRange[1])
            self.streamData = self.parser.getPrimaryDatasets(self.runNumber, self.LSRange[0], self.LSRange[1])
            self.pdData = self.parser.getStreamData(self.runNumber, self.LSRange[0], self.LSRange[1])
        self.totalStreams = len(self.streamData.keys())
        self.Rates = {}
        self.Rates.update(self.HLTRates)
        self.Rates.update(self.L1Rates)
        self.totalHLTTriggers = len(self.HLTRates.keys())
        self.totalL1Triggers = len(self.L1Rates.keys())
                
    # Use: Retrieves information and prints it in table form
    def printTable(self):
        if self.slidingLS == -1:
            self.startLS = self.lastLS
        else: self.startLS = max( [0, self.currentLS-self.slidingLS ] )+1
        # Reset variable
        self.normal = 0
        self.bad = 0
        # Get the inst lumi
        aveLumi = 0
        try:
            deadTimeData = self.parser.getDeadTime(self.runNumber)
            aveDeadTime = 0
        except:
            deadTimeData = {}
            aveDeadTime = None
            print "Error getting deadtime data"
            
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
                    if not aveDeadTime is None and deadTimeData.has_key(LS):
                        aveDeadTime += deadTimeData[LS]
                    aveLumi += instLumi
                    count += 1
            if count == 0:
                aveLumi = "NONE"
                expected = "NONE"
            else:
                aveLumi /= float(count)
                aveDeadTime /= float(count)
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

        #check the full menu for paths deviating past thresholds
        for trigger in self.fullL1HLTMenu: self.getTriggerData(trigger, doPred, aveLumi)        

        # Print the triggers that we can't make predictions for
        if self.useAll or self.mode != "collisions" or self.InputFitHLT is None:
            print '*' * self.hlength
            print "Unpredictable HLT Triggers (ones we have no fit for or do not try to fit)"
            print '*' * self.hlength
            self.L1 = False
            self.printTableSection(self.otherHLTTriggers, False)
            self.printTableSection(self.otherL1Triggers, False)
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
        if self.showStreams:
            print '*' * self.hlength
            streamSpacing = [ 50, 20, 25, 25, 25, 25 ]
            head = stringSegment("* Stream name", streamSpacing[0])
            head += stringSegment("* NLumis", streamSpacing[1])
            head += stringSegment("* Events", streamSpacing[2])
            head += stringSegment("* Stream rate [Hz]", streamSpacing[3])
            head += stringSegment("* Stream size [GB]", streamSpacing[4])
            head += stringSegment("* Stream bandwidth [GB/s]", streamSpacing[5])
            print head
            print '*' * self.hlength
            for name in self.streamData.keys():
                count = 0
                streamsize = 0
                aveBandwidth = 0
                aveRate = 0
                for LS, rate, size, bandwidth in self.streamData[name]:
                    streamsize += size
                    aveRate += rate
                    aveBandwidth += bandwidth
                    count += 1
                if count > 0:
                    aveRate /= count
                    streamsize /= (count*1000000000.0)
                    aveBandwidth /= (count*1000000000.0)
                    row = stringSegment("* "+name, streamSpacing[0])
                    row += stringSegment("* "+str(int(count)), streamSpacing[1])
                    row += stringSegment("* "+str(int(aveRate*23.3*count)), streamSpacing[2])
                    row += stringSegment("* "+"{0:.2f}".format(aveRate), streamSpacing[3])
                    row += stringSegment("* "+"{0:.2f}".format(streamsize), streamSpacing[4])
                    row += stringSegment("* "+"{0:.5f}".format(aveBandwidth), streamSpacing[5])
                    if not self.noColors and aveRate > self.maxStreamRate: write(bcolors.WARNING) # Write colored text
                    print row
                    if not self.noColors and aveRate > self.maxStreamRate: write(bcolors.ENDC)    # Stop writing colored text 
                else: pass

        # Print PD data
        if self.showPDs:
            print '*' * self.hlength
            pdSpacing = [ 50, 20, 25, 25]
            head = stringSegment("* Primary Dataset name", pdSpacing[0])
            head += stringSegment("* NLumis", pdSpacing[1])
            head += stringSegment("* Events", pdSpacing[2])
            head += stringSegment("* Dataset rate [Hz]", pdSpacing[3])
            print head
            print '*' * self.hlength
            for name in self.pdData.keys():
                count = 0
                aveRate = 0
                for LS, rate in self.pdData[name]:
                    aveRate += rate
                    count += 1
                if count > 0:
                    aveRate /= count
                    row = stringSegment("* "+name, pdSpacing[0])
                    row += stringSegment("* "+str(int(count)), pdSpacing[1])
                    row += stringSegment("* "+str(int(aveRate*23.3*count)), pdSpacing[2])
                    row += stringSegment("* "+"{0:.2f}".format(aveRate), pdSpacing[3])
                    if not self.noColors and aveRate > self.maxPDRate: write(bcolors.WARNING) # Write colored text
                    print row
                    if not self.noColors and aveRate > self.maxPDRate: write(bcolors.ENDC)    # Stop writing colored text 
                else: pass

        # Closing information
        print '*' * self.hlength
        print "SUMMARY:"
        if self.mode=="collisions": print "Triggers in Normal Range: %s   |   Triggers outside Normal Range: %s" % (self.normal, self.bad)
        print "Average inst. lumi: %s" % (aveLumi)
        print "Average dead time: %s" % (aveDeadTime)
        print '*' * self.hlength

    # Use: Prints the table header
    def printHeader(self):
        print "\n\n", '*' * self.hlength
        print "INFORMATION:"
        print "Run Number: %s" % (self.runNumber)
        print "LS Range: %s - %s" % (self.startLS, self.currentLS)
        print "Trigger Mode: %s (%s)" % (self.triggerMode, self.mode)
        print "Number of HLT Triggers: %s \nNumber of L1 Triggers: %s" % (self.totalHLTTriggers, self.totalL1Triggers)
        print "Number of streams:", self.totalStreams
        print '*' * self.hlength
        print self.header
        
    # Use: Prints a section of a table, ie all the triggers in a trigger list (like usableHLTTriggers, otherHLTTriggers, etc)
    def printTableSection(self, triggerList, doPred, aveLumi=0):
        self.tableData = [] # A list of tuples, each a row in the table: ( { trigger, rate, predicted rate, sign of % diff, abs % diff, sign of sigma, abs sigma, ave PS, comment } )
        # Get the trigger data
        for trigger in triggerList:
            self.getTriggerData(trigger, doPred, aveLumi)
        # Sort by % diff if need be
        if doPred:
            # [4] is % diff, [6] is deviation
            if self.usePerDiff: self.tableData.sort(key=lambda tup : tup[4])
            else: self.tableData.sort(key=lambda tup : tup[6])
        elif self.sortRates:
            self.tableData.sort(key=lambda tup: tup[1])
            self.tableData.reverse()
        for trigger, rate, pred, sign, perdiff, dsign, dev, avePS, comment in self.tableData:
            info = stringSegment("* "+trigger, self.spacing[0])
            if (self.displayRawRates or avePS == 0):
                info += stringSegment("* "+"{0:.2f}".format(rate), self.spacing[1])
                if pred!="": info += stringSegment("* "+"{0:.2f}".format(pred), self.spacing[2])
                else: info += stringSegment("", self.spacing[2])
            elif avePS != 0:
                info += stringSegment("* "+"{0:.2f}".format(rate/avePS), self.spacing[1])
                if pred!="": info += stringSegment("* "+"{0:.2f}".format(pred/avePS), self.spacing[2])
                else: info += stringSegment("", self.spacing[2])
            if perdiff=="": info += stringSegment("", self.spacing[3])
            elif perdiff=="INF": info += stringSegment("* INF", self.spacing[3])
            else: info += stringSegment("* "+"{0:.2f}".format(sign*perdiff), self.spacing[3])
            if dev=="": info += stringSegment("", self.spacing[4])
            elif dev=="INF" or dev==">1E6": info += stringSegment("* "+dev, self.spacing[4])
            else: info += stringSegment("* "+"{0:.2f}".format(dsign*dev), self.spacing[4])
            info += stringSegment("* "+"{0:.2f}".format(avePS), self.spacing[5])
            info += stringSegment("* "+comment, self.spacing[6])

            # Color the bad triggers with warning colors
            if avePS>0 and self.isBadTrigger(perdiff, dev, rate/avePS, trigger[0:3]=="L1_"):
                if not self.noColors: write(bcolors.WARNING) # Write colored text 
                print info
                if not self.noColors: write(bcolors.ENDC)    # Stop writing colored text
            # Don't color normal triggers
            else:
                print info

    # Use: Returns whether a given trigger is bad
    # Returns: Whether the trigger is bad
    def isBadTrigger(self, perdiff, dev, psrate, isL1):
        if ((self.usePerDiff and perdiff!="INF" and perdiff!="" and perdiff>self.percAccept) \
                                or (dev!="INF" and dev!="" and (dev==">1E6" or dev>self.devAccept))) or \
                                ((perdiff!="INF" and perdiff!="" and perdiff>self.percAccept and \
                                dev!="INF" and dev!="" and dev>self.devAccept)) or (isL1 and psrate>self.maxL1Rate) \
                                or (not isL1 and psrate>self.maxHLTRate): return True
        return False

    # Use: Gets a row of the table, self.tableData: ( { trigger, rate, predicted rate, sign of % diff, abs % diff, ave PS, comment } )
    # Parameters:
    # -- trigger : The name of the trigger
    # -- doPred  : Whether we want to make a prediction for this trigger
    # -- aveLumi : The average luminosity during the LS in question
    # Returns: (void)
    def getTriggerData(self, trigger, doPred, aveLumi):
        # In case of critical error (this shouldn't occur)
        if not self.Rates.has_key(trigger): return
        # If cosmics, don't do predictions
        if self.cosmics: doPred = False
        # Calculate rate
        if not self.cosmics and doPred:
            if not aveLumi is None:
                expected = self.calculateRate(trigger, aveLumi)
                # Don't let expected value be negative
                if expected<0: expected = 0
                # Get the MSE
                mse = self.getMSE(trigger)
            else:
                expected = None
                mse = None
        # Find the ave rate since the last time we checked
        aveRate = 0
        properAvePSRate = 0
        avePS = 0
        count = 0
        comment = "" # A comment
        for LS in self.Rates[trigger].keys():
            # If using a LSRange
            if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
            elif LS < self.startLS or LS > self.currentLS: continue
            # Average the rate
            if self.Rates[trigger][LS][1] > 0: # If not prescaled to 0
                aveRate += self.Rates[trigger][LS][0]
                properAvePSRate += self.Rates[trigger][LS][0]/self.Rates[trigger][LS][1] 
                count += 1
                avePS += self.Rates[trigger][LS][1]
        if count > 0:
            # Make note if rate or PS are identically zero
            if aveRate == 0: comment += "Rate=0 "
            aveRate /= count
            properAvePSRate /= count
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
            if expected == "NONE":
                perc = "UNDEF"
                dev = "UNDEF"
                row.append(1)    # Sign of % diff
                row.append(perc) # abs % diff
                row.append(1)    # Sign of deviation
                row.append(dev)  # abs deviation
            else:
                diff = aveRate-expected
                if expected!=0: perc = 100*diff/expected
                else: perc = "INF"
                if mse!=0:
                    dev = diff/mse
                    if abs(dev)>1000000: dev = ">1E6"
                else: dev = "INF"
                if perc>0: sign=1
                else: sign=-1
                row.append(sign)       # Sign of % diff
                if perc!="INF": row.append(abs(perc))  # abs % diff
                else: row.append("INF")
                if mse>0: sign=1
                else: sign=-1
                row.append(sign)       # Sign of the deviation
                if dev!="INF" and dev!=">1E6":
                    row.append(abs(dev))   # abs deviation
                else: row.append(dev)
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

        #do not warn on triggers that are ZeroBias
        if trigger.find("ZeroBias") > -1: return
        # Check if the trigger is bad
        if doPred:
            # Check for bad rates.
            #if (self.usePerDiff and perc!="INF" and perc>self.percAccept) or \
            #(not self.usePerDiff and dev!="INF" and (dev==">1E6" or dev>self.devAccept)):
            if self.isBadTrigger(perc, dev, properAvePSRate, trigger[0:3]=="L1_"):
                self.bad += 1
                # Record if a trigger was bad
                if not self.recordAllBadRates.has_key(trigger):
                    self.recordAllBadRates[trigger] = 0
                self.recordAllBadRates[trigger] += 1
                # Record consecutive bad rates
                if not self.badRates.has_key(trigger):
                    self.badRates[trigger] = [1, True, aveRate, expected, dev ]
                else:
                    last = self.badRates[trigger]
                    self.badRates[trigger] = [ last[0]+1, True, aveRate, expected, dev ]
            else:
                self.normal += 1
                # Remove warning from badRates
                if self.badRates.has_key(trigger):
                    self.badRates[trigger] = [ 0, False, aveRate, expected, dev ]
                    del self.badRates[trigger]
                    
        else:
            if self.isBadTrigger("", "", properAvePSRate, trigger[0:3]=="L1_"):
                self.bad += 1
                # Record if a trigger was bad
                if not self.recordAllBadRates.has_key(trigger):
                    self.recordAllBadRates[trigger] = 0
                self.recordAllBadRates[trigger] += 1
                # Record consecutive bad rates
                if not self.badRates.has_key(trigger):
                    self.badRates[trigger] = [ 1, True, aveRate, -999, -999 ]
                else:
                    last = self.badRates[trigger]
                    self.badRates[trigger] = [ last[0]+1, True, aveRate, -999, -999 ]
            else:
                self.normal += 1
                # Remove warning from badRates
                if self.badRates.has_key(trigger):
                    del self.badRates[trigger]
                    

    # Use: Checks triggers to make sure none have been bad for to long
    def checkTriggers(self):
        if self.displayBadRates != 0:
            count = 0
            if self.displayBadRates != -1: write("First %s triggers that are bad: " % (self.displayBadRates)) 
            elif len(self.badRates) > 0 : write("All triggers deviating past thresholds from fit and/or L1 rate > %s Hz, HLT rate > %s Hz: " %(self.maxL1Rate,self.maxHLTRate))
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
        mailTriggers = [] # A list of triggers that we should mail alerts about
        for trigger in self.badRates:
            if self.badRates[trigger][1]:
                if self.badRates[trigger][0] >= self.maxCBR:
                    print "Trigger %s has been out of line for more then %s minutes" % (trigger, self.badRates[trigger][0])
                # We want to mail an alert whenever a trigger exits the acceptable threshold envelope
                if self.badRates[trigger][0] == 1:
                    mailTriggers.append( [ trigger, self.badRates[trigger][2], self.badRates[trigger][3], self.badRates[trigger][4] ] )
        # Send mail alerts
        if self.sendMailAlerts and len(mailTriggers)>0: self.sendMail(mailTriggers)    
            
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
        elif self.L1 and ((self.InputFitL1 is None) or not self.InputFitL1.has_key(triggerName)):
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
        elif self.L1 and ((self.InputFitL1 is None) or not self.InputFitL1.has_key(triggerName)):
            return 0
        if self.L1: paramlist = self.InputFitL1[triggerName]
        else: paramlist = self.InputFitHLT[triggerName]
        return paramlist[5] # The MSE

    # Use: Sends an email alert
    # Parameters:
    # -- mailTriggers: A list of triggers that we should include in the mail, ( { triggerName, aveRate, expected rate, standard dev } )
    # Returns: (void)
    def sendMail(self, mailTriggers):
        mail = "Run: %d, Lumisections: %s - %s \n \n" % (self.runNumber, self.lastLS, self.currentLS)
        mail += "The following path rate(s) are deviating from expected values: \n"

        for triggerName, rate, expected, dev in mailTriggers:
            mail += stringSegment(triggerName, 35) +": Expected: %s, Actual: %s, Abs Deviation: %s\n" % (expected, rate, dev)

        mail += " \n"
        mail += " \n"
        mail += "Email warnings triggered when: \n"
        mail += "   - L1 or HLT rates deviate by more than %s standard deviations from fit \n" % (self.devAccept)
        mail += "   - HLT rates > %s Hz \n" % (self.maxHLTRate)
        mail += "   - L1 rates > %s Hz \n" % (self.maxL1Rate)

        print "--- SENDING MAIL ---\n"+mail+"\n--------------------"
        mailAlert(mail)

## ----------- End of class ShiftMonitor ------------ ##
