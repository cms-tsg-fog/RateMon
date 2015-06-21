#######################################################
# File: rateGraphingNCR.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 19, 2015
# Last Modified: June 19, 2015 by Nathaniel Rupprecht
#
# Dependencies: RateMoniter.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects 
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
import getopt # For getting command line options
# Import the RateMoniter object
from RateMoniterNCR import *

## ----------- End Imports ------------ #

# Class MoniterController:
# Parsers command line input and uses it to set the parameters of an instance of RateMoniter which it contains. It then runs rateMoniter.
class MoniterController:

    # Default constructor for Moniter Controller class
    def __init__(self):
        self.rateMoniter = RateMoniter()

    # Use: Parses arguments from the command line and sets class variables
    # Returns: True if parsing was successful, False if not
    def parseArgs(self):
        # Get the command line arguments
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["maxRuns=", "fitFile=", "triggerList=", "runList=", "runFile=", "offset=", "saveName=", "All", "Raw", "Help", "useList", "noFit"])
        except:
            print "Error geting options. Exiting."
            return False

        if len(opt) == 0 and len(args) == 0:
            print "\nWe do need some options to make this program work you know. We can't read your mind."
            print "Use 'python rateMoniterNCR.py --Help' to see options.\n"
            return False
        
        # Process Options
        for label, op in opt:
            if label == "--fitFile":
                self.rateMoniter.fitFile = str(op)
                print "Using fit file:", self.rateMoniter.fitFile
            elif label == "--runList" or label == "--runFile":
                self.rateMoniter.runFile = str(op)
                print "Using the runs in file", self.rateMoniter.runFile
                self.loadRunsFromFile()
            elif label == "--offset":
                self.rateMoniter.offset = int(op)
            elif label == "--Help":
                self.printOptions()
                return False
            elif label == "--maxRuns":
                self.rateMoniter.maxRuns = int(op)
            elif label == "--All":
                self.rateMoniter.processAll = True
            elif label == "--Raw":
                self.rateMoniter.varY = "rawRate"
            elif label == "--saveName":
                self.rateMoniter.saveName = str(op)
            elif label == "--noFit":
                self.rateMoniter.doFit = False
            elif label == "--triggerList":
                self.loadTriggersFromFile(str(op))
                self.rateMoniter.useTrigList = False
            elif label == "--useList":
                # Depreciated (no longer necessary to use this with the --triggerList option)
                self.rateMoniter.useTrigList = True
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
                                if not int(r) in self.rateMoniter.runList:
                                    self.rateMoniter.runList.append(int(r))
                        except:
                            print "Error: Could not parse run range"
                            return False
                else: # Not a range, but a single run
                    try:
                        if not int(item) in self.rateMoniter.runList:
                            self.rateMoniter.runList.append(int(item))
                    except:
                        print "Error: Could not parse run arguments."
                        return False

        # If no runs were specified, we cannot run rate monitering
        if len(self.rateMoniter.runList) == 0:
            print "Error: No runs were specified."
            return False
        # If no fit file was specified, don't try to make a fit
        if self.rateMoniter.fitFile == "":
            self.rateMoniter.doFit = False

        return True

    # Use: Prints out all the possible options that you can specify in the command line
    # Returns: (void)
    def printOptions(self):
        print ""
        print "Usage: python rateMoniterNCR.py [Options] <list of runs (optional)>"
        print "<list of runs>        : Either single runs (like '10000') or ranges (like '10001-10003'). If you specified a file with a list of runs"
        print "                        in it, you do not need to specify runs on the command line. If you do both, they will simply be added to the "
        print "                        RateMoniter class's internal list of runs to process"
        print ""
        print "Options:"
        print "--fitFile=<name>      : Loads fit information from the file named <name>."
        print "--runFile=<name>      : Loads a list of runs to consider from the file named <name>."
        print "--runList=<name>      : Same as --runFile (see above)."
        print "--triggerList=<name>  : Loads a list of triggers to process from the file <name>. We will only process the triggers listed in triggerfiles."
        print "--saveName=<name>     : Saves the root output as a file named <name>."
        print "--offset=<number>     : Allows us to start processing with the <number>th entry in our list of runs."
        print "--maxRuns=<number>    : Changes the maximum number of runs that the program will put on a single chart. The default is 12 since we have 12 unique colors specified."
        print "--All                 : Overrides the maximum number of runs and processes all runs in the run list"
        print "--noFit               : Does not load a fit file. Also, prints all possible triggers."
        print "--useList             : Only consider triggers specified in the triggerList file. You need to pass in a trigger list file using --triggerList=<name> (see above)."
        print "--Help                : Prints out the display that you are looking at now. You probably used this option to get here."
        print ""
        print "In your run file, you can specify runs by typing them in the form <run1> (single runs), or <run2>-<run3> (ranges), or both. Do this after all other arguments"
        print "Multiple runFiles can be specified, and you can add more runs to the run list by specifying them on the command line as described in the above line."
        print ""
        print "Program by Nathaniel Rupprecht, created June 16th 2015. For questions, email nrupprec@nd.edu"

    # Use: Opens a file containing a list of runs and adds them to the RateMoniter class's run list
    # Note: We do not clear the run list, this way we could add runs from multiple files to the run list
    # Arguments:
    # -- fileName (Default=None): The name of the file that runs are contained in
    # Returns: (void)
    def loadRunsFromFile(self, fileName = None):
        # Use self.fileName as the default fileName
        if fileName == None:
            fileName = self.rateMoniter.runFile
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
                        if not int(run) in self.rateMoniter.runList:
                            self.rateMoniter.runList.append(int(rn))
                except:
                    print "Range specified in file", fileName, "could not be parsed."
            else:
                try:
                    if not int(run) in self.rateMoniter.runList:
                        self.rateMoniter.runList.append(int(run))
                except:
                    print "Error in parsing run in file", fileName

    # Use: Opens a file containing a list of trigger names and adds them to the RateMoniter class's trigger list
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
                if not str(triggerName) in self.rateMoniter.TriggerList:
                    self.rateMoniter.TriggerList.append(str(triggerName))
            except:
                print "Error parsing trigger name in file", fileName
                                    
    # Use: Runs the rateMoniter object using parameters supplied as command line arguments
    # Returns: (void)
    def run(self):
        if self.parseArgs():
            self.rateMoniter.run()
        
## ----------- End of class MoniterController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MoniterController()
    controller.run()
