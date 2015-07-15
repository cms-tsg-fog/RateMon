#######################################################
# File: plotTriggerRates.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 19, 2015
# Last Modified: July 9, 2015 by Nathaniel Rupprecht
#
# Dependencies: RateMonitor.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects 
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
import getopt # For getting command line options
# Import the RateMonitor object
from RateMonitorNCR import *

## ----------- End Imports ------------ #

# Class MonitorController:
# Parsers command line input and uses it to set the parameters of an instance of RateMonitor which it contains. It then runs rateMonitor.
class MonitorController:

    # Default constructor for Monitor Controller class
    def __init__(self):
        self.rateMonitor = RateMonitor()
        self.batchMode = False # Will not run rateMonitor in batch mode
        self.doAnyways = False # Will run in secondary mode even if there is no fit file

    # Use: Parses arguments from the command line and sets class variables
    # Returns: True if parsing was successful, False if not
    def parseArgs(self):
        # Get the command line arguments
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["lumiCut=", "rateCut=","maxRuns=", "maxBatches=", "fitFile=", "triggerList=", "runList=",
                                                       "runFile=", "offset=", "saveName=", "fitSaveName=", "saveDirectory=", "sigmas=", "preferLinear=",
                                                       "steamFile=", "Secondary", "All", "Raw", "Help", "batch", "overrideBatch", "createFit",
                                                       "debugFitter", "doAnyways", "rawPoints", "linear", "includeNoneBunches", "normalizeCollidingBx",
                                                       "L1Triggers", "AllTriggers", "aLaMode"])
        except:
            print "Error geting options: command unrecognized. Exiting."
            return False

        if len(opt) == 0 and len(args) == 0:
            print "\nWe do need some options to make this program work you know. We can't read your mind."
            print "Use 'python plotTriggerRates.py --Help' to see options.\n"
            return False
        
        # Process Options
        for label, op in opt:
            if label == "--Secondary":
                self.rateMonitor.mode = True # Run in secondary mode
                self.batchMode = True # Use batch mode
                self.rateMonitor.outputOn = False
                self.rateMonitor.maxRuns = 1 # Only do one run at a time
                self.rateMonitor.fit = False # We don't make fits in secondary mode
                self.rateMonitor.useFit = False # We don't plot a function, just a prediction
                self.rateMonitor.divByBunches = False # We don't divide the LS by the # of bunches
            elif label == "--fitFile":
                self.rateMonitor.fitFile = str(op)
                print "Using fit file:", self.rateMonitor.fitFile
            elif label == "--steamFile":
                self.rateMonitor.steam = True
                self.rateMonitor.steamFile = str(op)
            elif label == "--runList" or label == "--runFile":
                self.rateMonitor.runFile = str(op)
                print "Using the runs in file", self.rateMonitor.runFile
                self.loadRunsFromFile()
            elif label == "--offset":
                self.rateMonitor.offset = int(op)
            elif label == "--Help":
                self.printOptions()
                return False
            elif label == "--maxRuns":
                self.rateMonitor.maxRuns = int(op)
            elif label == "--maxBatches":
                self.rateMonitor.maxBatches = int(op)
            elif label == "--sigmas":
                self.rateMonitor.sigmas = float(op)
            elif label == "--preferLinear":
                self.rateMonitor.fitFinder.preferLinear = float(op)
            elif label == "--All":
                self.rateMonitor.processAll = True
            elif label == "--Raw":
                self.rateMonitor.varY = "rawRate"
            elif label == "--saveName":
                if not self.batchMode: # We do not allow a user defined save name in batch mode
                    self.rateMonitor.saveName = str(op)
                    self.rateMonitor.nameGiven = True
                else:
                    print "We do not allow a user defined save name while using batch or secondary mode."
            elif label == "--fitSaveName":
                if not self.batchMode: # We do not allow a user defined fit save name in batch mode
                    self.rateMonitor.outFitFile = str(op)
                else:
                    print "We do not allow a user defined fit save name while using batch or secondary mode"
            elif label == "--saveDirectory":
                self.rateMonitor.saveDirectory = str(op)
            elif label == "--triggerList":
                self.loadTriggersFromFile(str(op))
                self.rateMonitor.useTrigList = True
            elif label == "--L1Triggers":
                self.rateMonitor.L1Triggers = True
                self.rateMonitor.HLTTriggers = False
            elif label == "--AllTriggers":
                self.rateMonitor.L1Triggers = True
            elif label == "--batch":
                self.batchMode = True
                self.rateMonitor.outputOn = False
                self.rateMonitor.nameGiven = False # We do not allow a user defined save name in batch mode
            elif label == "--createFit":
                if not self.rateMonitor.mode: self.rateMonitor.fit = True
                else: print "We do not create fits in secondary mode"
            elif label == "--debugFitter":
                self.rateMonitor.fitFinder.saveDebug = True
            elif label == "--doAnyways":
                self.doAnyways = True
            elif label == "--rawPoints":
                self.rateMonitor.fitFinder.usePointSelection = False
            elif label == "--linear":
                self.rateMonitor.fitFinder.forceLinear = True
            elif label == "--normalizeCollidingBx":
                if not self.rateMonitor.mode:
                    self.rateMonitor.divByBunches = True
            elif label == "--includeNoneBunches":
                self.rateMonitor.includeNoneBunches = Trues
            elif label == "--lumiCut":
                self.rateMonitor.doLumiCut = True
                self.rateMonitor.lumiCut = float(op)
            elif label == "--rateCut":
                self.rateMonitor.doRateCut = True
                self.rateMonitor.rateCut = float(op)
            elif label == "--aLaMode":
                self.aLaMode()
            else:
                print "Unknown option '%s'." % label
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
                else: # Not a range, but a single run
                    try:
                        if not int(item) in self.rateMonitor.runList:
                            self.rateMonitor.runList.append(int(item))
                    except:
                        print "Error: Could not parse run arguments."
                        return False

        # If no runs were specified, we cannot run rate monitoring
        if len(self.rateMonitor.runList) == 0:
            print "Error: No runs were specified."
            return False
        # If no fit file was specified, don't try to make a fit
        if self.rateMonitor.fitFile == "":

            if self.rateMonitor.mode and not self.doAnyways:
                print "We require a fit file in secondary mode unless the --doAnyways flag is specified. Exiting."
                exit(0)
            
            self.rateMonitor.useFit = False

        return True

    # Use: Prints out all the possible options that you can specify in the command line
    # Returns: (void)
    def printOptions(self):
        print ""
        print "Usage: python plotTriggerRates.py [Options] <list of runs (optional)>"
        print "<list of runs>        : Either single runs (like '10000') or ranges (like '10001-10003'). If you specified a file with a list of runs"
        print "                        in it, you do not need to specify runs on the command line. If you do both, they will simply be added to the "
        print "                        RateMonitor class's internal list of runs to process"
        print ""
        print "OPTIONS:"
        print "Help:"
        print "--Help                 : Prints out the display that you are looking at now. You probably used this option to get here."
        print "\nFile Options:"
        print "--fitFile=<name>       : Loads fit information from the file named <name>."
        print "--runFile=<name>       : Loads a list of runs to consider from the file named <name>."
        print "--runList=<name>       : Same as --runFile (see above)."
        print "--steamFile=<name>     : Uses the data from the .csv file <name> to plot steam's predicted rates."
        print "--steamFile=<name>     : A .csv file containing steam data estimates to plot on the graph."
        print "--triggerList=<name>   : Loads a list of triggers to process from the file <name>. We will only process the triggers listed in triggerfiles."
        print "\nSave Options:"
        print "--saveName=<name>      : Saves the root output as a file named <name>."
        print "--fitSaveName=<name>   : A name to save the fit file in. Primary mode feature only, not for batch mode."
        print "--saveDirectory=<name> : The name of a directory that we will save all our file in. Useful for batch mode."
        print "\nRun Options:"
        print "--offset=<number>      : Allows us to start processing with the <number>th entry in our list of runs. Note: The first entry would be --offset=1, etc."
        print "--maxRuns=<number>     : Changes the maximum number of runs that the program will put on a single chart. The default is 12 since we have 12 unique colors specified."
        print "--Secondary            : Run the program in 'secondary mode,' making plots of raw rate vs lumisection."
        print "--All                  : Overrides the maximum number of runs and processes all runs in the run list."
        print "\nBatch Options:"
        print "--batch                : Runs the program over all triggers in the trigger list in batches. Adjust maxRuns to set the number of runs per batch."
        print "--maxBatches=<num>     : The max number of batches to do when using batch mode. Also, the max number of runs to look at in secondary mode. By default 9999."
        print "\nFitting Options:"
        print "--createFit            : Make a fit for the data we plot. Only a primary mode feature."
        print "--debugFitter          : Creates a root file showing all the points labeled as good and bad when doing the fit"
        print "--rawPoints            : Don't do point selection in making fits"
        print "--linear               : Forces fits to be linear"
        print "--preferLinear=<num>   : If the MSE for the linear fit is less then <num> worse then the best fit, we will use the linear fit."
        print "\nCut/Normalization Options:"
        print "--lumiCut=<num>        : Any lumisection with inst lumi less then <num> will not be plotted or considered in the fit making. By default, this value is 0.1"
        print "--rateCut=<num>        : Any lumisection with rate less then <num> will not be plotted or considered in the fit making. By default, this value is 0.0"
        print "--normalizeCollidingBx : Divides the instantaneous luminosity by the number of colliding bunches."
        print "--includeNoneBunches   : By default, if we normalize by the number of colliding bunches and we find a run where we cannot retrieve the number of colliding bunches,"
        print "                         we skip that run. This overrides that functionality."
        print "Trigger Options"
        print "--L1Triggers           : ONLY L1 triggers are monitored for the runs."
        print "--AllTriggers          : Both L1 and HLT triggers are monitored for the runs."
        print "\nSecret Options"
        print "--???"
        print ""
        print "In your run file, you can specify runs by typing them in the form <run1> (single runs), or <run2>-<run3> (ranges), or both. Do this after all other arguments"
        print "Multiple runFiles can be specified, and you can add more runs to the run list by specifying them on the command line as described in the above line."
        print ""
        print "Program by Nathaniel Rupprecht, created June 16th, 2015. For questions, email nrupprec@nd.edu"

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
                    self.rateMonitor.TriggerList.append(str(triggerName))
            except:
                print "Error parsing trigger name in file", fileName

    def aLaMode(self):
        print ""
        print """        .-"''"-.   """
        print "       /        \  "
        print "       |        |  "
        print "       /'---'--`\  "
        print "      |          | "
        print "      \.--.---.-./ "
        print "      (_.--._.-._) "
        print "        \=-=-=-/   "
        print "         \=-=-/    "
        print "          \=-/     "
        print "           \/      "
        print ""
    
                                    
    # Use: Runs the rateMonitor object using parameters supplied as command line arguments
    # Returns: (void)
    def run(self):
        if self.parseArgs():
            if self.batchMode:
                self.rateMonitor.runBatch()
            else:
                self.rateMonitor.run()

## ----------- End of class MonitorController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MonitorController()
    controller.run()
