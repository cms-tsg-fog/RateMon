#######################################################
# File: plotTriggerRates.py
# Author: Nathaniel Carl Rupprecht, Charlie Mueller
# Date Created: June 19, 2015
#
# Dependencies: RateMonitor.py DBParser.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects 
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
import getopt # For getting command line options
# Import the RateMonitor object
from DBParser import *
from RateMonitorNCR import *
#from RateMonitorNCR_multifit import *

## ----------- End Imports ------------ #

# Class MonitorController:
# Parsers command line input and uses it to set the parameters of an instance of RateMonitor which it contains. It then runs rateMonitor.
class MonitorController:

    # Default constructor for Monitor Controller class
    def __init__(self):
        self.rateMonitor = RateMonitor()

    # Use: Parses arguments from the command line and sets class variables
    # Returns: True if parsing was successful, False if not
    def parseArgs(self):
        # Get the command line arguments
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["fitFile=", "triggerList=", "runList=", "jsonFile=",
                                                       "runFile=","saveDirectory=","sigma=", "preferLinear=",
                                                       "Secondary", "updateOnlineFits", "All", "Raw", "Help", "createFit",
                                                       "debugFitter", "nonLinear","vsInstLumi",
                                                       "L1Triggers", "AllTriggers","datasetRate", "L1ARate", "streamRate", "streamBandwidth",
                                                       "streamSize", "useFills"])
                                                   
        except:
            print "Error geting options: command unrecognized. Exiting."
            return False

        if len(opt) == 0 and len(args) == 0:
            self.printOptions()
            return False
        
        # Process Options
        self.rateMonitor.ops = opt
        for label, op in opt:
            if label == "--Secondary":
                self.rateMonitor.certifyMode = True # Run in secondary mode
                self.rateMonitor.fit = False # We don't make fits in secondary mode
                self.rateMonitor.useFit = True 
                self.rateMonitor.L1Triggers = True
            elif label == "--fitFile":
                self.rateMonitor.fitFile = str(op)
                print "Using fit file:", self.rateMonitor.fitFile
            elif label == "--runList" or label == "--runFile":
                self.rateMonitor.runFile = str(op)
                print "Using the runs in file", self.rateMonitor.runFile
                self.loadRunsFromFile()
            elif label == "--jsonFile":
                self.rateMonitor.jsonFilter = True
                self.rateMonitor.jsonFile = str(op)
            elif label == "--Help":
                self.printOptions()
                return False
            elif label == "--sigma":
                self.rateMonitor.sigmas = float(op)
            #elif label == "--preferLinear":
                #self.rateMonitor.fitFinder.preferLinear = float(op)
            elif label == "--All":
                self.rateMonitor.processAll = True
            elif label == "--Raw":
                self.rateMonitor.varY = "rawRate"
            elif label == "--saveDirectory":
                self.rateMonitor.saveDirectory = str(op)
            elif label == "--triggerList":
                self.loadTriggersFromFile(str(op))
                self.rateMonitor.useTrigList = True
                self.rateMonitor.L1Triggers = True
            elif label == "--L1Triggers":
                self.rateMonitor.L1Triggers = True
                self.rateMonitor.HLTTriggers = False
            elif label == "--AllTriggers":
                self.rateMonitor.L1Triggers = True
            elif label == "--updateOnlineFits":
                self.rateMonitor.updateOnlineFits = True
            elif label == "--createFit":
                if not self.rateMonitor.certifyMode: self.rateMonitor.fit = True
                else: print "We do not create fits in secondary mode"
            elif label == "--debugFitter":
                self.rateMonitor.fitFinder.saveDebug = True
            elif label == "--nonLinear":
                self.rateMonitor.fitFinder.forceLinear = False
            elif label == "--vsInstLumi":
                self.rateMonitor.pileUp = False
            elif label == "--streamRate":
                self.rateMonitor.labelY = "rate [Hz]"
                self.rateMonitor.plotStreams = True
                self.rateMonitor.dataCol = 0
            elif label == "--streamSize":
                self.rateMonitor.labelY = "stream size [bytes]"
                self.rateMonitor.plotStreams = True
                self.rateMonitor.dataCol = 1
            elif label == "--streamBandwidth":
                self.rateMonitor.labelY = "stream bandwidth [bytes]"
                self.rateMonitor.dataCol = 2
                self.rateMonitor.plotStreams = True
            elif label == "--datasetRate":
                self.rateMonitor.labelY = "primary dataset rate [Hz]"
                self.rateMonitor.plotDatasets = True
                self.rateMonitor.dataCol = 0
            elif label == "--L1ARate":
                self.rateMonitor.labelY = "L1Physics rate [Hz]"
                self.rateMonitor.plotL1ARate = True
                self.rateMonitor.dataCol = 0
            elif label == "--useFills":
                self.rateMonitor.useFills = True
            else:
                print "Unimplemented option '%s'." % label
                return False
            
        # Process Arguments
        if len(args) > 0: # There are arguments to look at
            for item in args:
                if item.find('-') != -1:
                    rng = item.split('-')
                    if len(rng) != 2:
                        print "Error: Invalid range format."
                        return False
                    else: # Add the runs in the range to the run list
                        try:
                            for r in range(int(rng[0]), int(rng[1])+1):
                                if not int(r) in self.rateMonitor.runList:
                                    self.rateMonitor.runList.append(int(r))
                        except:
                            print "Error: Could not parse run range"
                            return False
                elif self.rateMonitor.useFills:
                    try:
                        if not int(item) in self.rateMonitor.fillList:
                            self.rateMonitor.fillList.append(int(item))
                    except:
                        print "Error: Could not parse fill arguments."
                        return False
                else: # Not a range, but a single run
                    try:
                        if not int(item) in self.rateMonitor.runList:
                            self.rateMonitor.runList.append(int(item))
                    except:
                        print "Error: Could not parse run arguments."
                        return False

        # If no runs were specified, we cannot run rate monitoring
        if len(self.rateMonitor.runList) == 0 and len(self.rateMonitor.fillList) == 0:
            print "Error: No runs/fills were specified."
            return False
        # If no fit file was specified, don't try to make a fit
        if self.rateMonitor.fitFile == "" and self.rateMonitor.certifyMode:
            print "Fit file needed for certification. Exiting."
            exit(0)
            
        if self.rateMonitor.fitFile == "":
            self.rateMonitor.useFit = False

        # Check JSON file exists
        if self.rateMonitor.jsonFilter:
            if not os.path.exists(self.rateMonitor.jsonFile):
                print "The specifed JSON file does not exist. Exiting."
                exit(0)
        
        return True

    # Use: Prints out all the possible options that you can specify in the command line
    # Returns: (void)
    def printOptions(self):
        print ""
        print "Usage: python plotTriggerRates.py [Options] <list of runs (optional)>"
        print "\n<list of runs>        : Either single runs (like '10000 10003 10007'), or ranges (like '10001-10003')"
        print ""
        print "OPTIONS:"
        print "\n--Help                 : Prints this display"
        #print "\nFile Options:"
        print "--fitFile=<name>       : Loads fit information from the file named <name>."
        print "--jsonFile=<name>      : Filter runs and lumisections according the to provided JSON file."
        print "--triggerList=<name>   : Loads a list of triggers to process from the file <name>. We will only process the triggers listed in triggerfiles."
        #print "\nRun Options:"
        print "--Secondary            : Run the program in 'secondary mode,' making plots of raw rate vs lumisection."
        #        print "\nFitting Options:"
        print "--createFit            : Make a fit for the data we plot. Only a primary mode feature."
        print "--sigma=<num>          : The acceptable tolerance for the fit. default is 3 sigma"
        #        print "--debugFitter          : Creates a root file showing all the points labeled as good and bad when doing the fit"
        print "--nonLinear            : Forces fits to be nonLinear"
        print "--vsInstLumi           : Plot rates vs inst. lumi"
        print "--L1Triggers           : ONLY L1 triggers are plotted for the runs."
        print "--AllTriggers          : Both L1 and HLT triggers are plotted for the runs."
        #        print "--preferLinear=<num>   : If the MSE for the linear fit is less then <num> worse then the best fit, we will use the linear fit."
        print "--streamRate           : Plots the stream rate vs inst lumi."
        print "--streamSize           : Plots the stream size vs inst lumi."
        #print "--streamBandwidth      : Plots the stream bandwidth vs inst lumi."
        print "--datasetRate          : Plots the PD rate vs inst lumi."
        #        print "\nCut/Normalization Options:" 
        #print "                         we skip that run. This overrides that functionality."
        print ""
        print "EXAMPLES:"
        print ""
        print "fit making mode:\n python plotTriggerRates.py --createFit --triggerList=monitorlist_COLLISIONS.list 251643 251638 251883 251244 251562\n"
        print "certification mode:\n python plotTriggerRates.py --Secondary --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl 276437 276453 276454 276455 276456 276457 276458"
        #print "You can specify runs by typing them in the form <run1> (single runs), or <run2>-<run3> (ranges), or both. Do this after all other arguments"
        #print "Multiple runFiles can be specified, and you can add more runs to the run list by specifying them on the command line as described in the above line."
        print ""

    # Use: Opens a file containing a list of runs and adds them to the RateMonitor class's run list
    # Note: We do not clear the run list, this way we could add runs from multiple files to the run list
    # Arguments:
    # -- fileName (Default=None): The name of the file that runs are contained in
    # Returns: (void)
    def loadRunsFromFile(self, fileName = None):
        # Use self.fileName as the default fileName
        if fileName == None:
            fileName = self.rateMonitor.runFile
        try:
            file = open(fileName, 'r')
        except:
            print "File", fileName, "(a run list file) failed to open."
            return
        # Load all the runs. There should only be run numbers and whitespaces in the run list file
        allRunNumbers = file.read().split() # Get all the numbers on the line, no argument -> split on any whitespace
        for run in allRunNumbers:
            # Check if the run is a range
            if run.find('-') != -1:
                try:
                    start, end = run.split('-')
                    for rn in range(start, end+1):
                        if not int(run) in self.rateMonitor.runList:
                            self.rateMonitor.runList.append(int(rn))
                except:
                    print "Range specified in file", fileName, "could not be parsed."
            else:
                try:
                    if not int(run) in self.rateMonitor.runList:
                        self.rateMonitor.runList.append(int(run))
                except:
                    print "Error in parsing run in file", fileName

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
        for triggerName in allTriggerNames:
            try:
                if not str(triggerName) in self.rateMonitor.TriggerList:
                    self.rateMonitor.TriggerList.append(stripVersion(str(triggerName)))
            except:
                print "Error parsing trigger name in file", fileName

    # Use: Runs the rateMonitor object using parameters supplied as command line arguments
    # Returns: (void)
    def run(self):
        if self.parseArgs(): self.rateMonitor.runBatch()

## ----------- End of class MonitorController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MonitorController()
    controller.run()

