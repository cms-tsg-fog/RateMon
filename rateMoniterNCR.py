#######################################################
# File: rateMoniterNCR.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 16, 2015
# Last Modified: June 19, 2015 by Nathaniel Rupprecht
#
# Dependencies: DBParser.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects 
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
import cPickle as pickle
import math
import array
# Not all these are necessary
from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend
from ROOT import TFile, TPaveText, TBrowser
import os
import sys
# For getting command line options
import getopt
# Import the DB interface class
from DBParser import *

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
            opt, args = getopt.getopt(sys.argv[1:],"",["fitFile=", "triggerList=", "runList=", "runFile=", "offset=", "SaveName=", "All", "Raw", "Help", "useList", "noFit"])
        except:
            print "Error geting options. Exiting."
            return False
        if len(opt) == 0:
            print "We do need some options to make this program work you know. We can't read your mind. Cancelling Execution."
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
            elif label == "--SaveName":
                self.rateMoniter.saveName = str(op)
            elif label == "--noFit":
                self.rateMoniter.doFit = False
            elif label == "--triggerList":
                self.loadTriggersFromFile(str(op))
            elif label == "--useList":
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
                                self.rateMoniter.runList.append(int(r))
                        except:
                            print "Error: Could not parse run range"
                            return False
                else: # Not a range, but a single run
                    try:
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
        print "--triggerList=<name>  : Loads a list of triggers to process from the file <name>."
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

# Class RateMoniter:
# Analyzes the rate vs instantaneous luminosity behavior of runs (held in a run list called self.runList) and make plots of the data
# Can also plot a fit from a given pickle file on the plots it produces
# Contains an instance of DBParser to get information from the database
class RateMoniter:
    # Default constructor for RateMoniter class
    def __init__(self):
        # Use batch mode so plots are not spit out in X11 as we make them
        gROOT.SetBatch(True)

        # Member variables
        self.runFile = "" # The name of the file that a list of runs is contained in
        self.runList = [] # A list of runs to process
        self.maxRuns = 12 # The maximum number of runs that we will process
        self.fitFile = "" # The name of the file that the fit info is contained in
        self.colorList = [1,3,4,6,7,8,9,28,38,30,40,46] # List of colors that we can use for graphing
        self.offset = 0   # Which run to start with if processing runs in a file (first, second, etc...)
        self.processAll = False  # If true, we process all the runs in the run list
        self.varX = "instLumi"   # Plot the instantaneous luminosity on the x axis
        self.varY = "psRate"     # Plot the prescaled rate on the y axis
        self.saveName = ""       # A name that we save the root file as
        self.parser = DBParser() # A database parser
        self.lastRun = 0         # The last run in the run list that will be considered
        self.TriggerList = []    # The list of triggers to consider in plot-making 

        # self.doFit:
        # If False, no fit will be plotted and all possible triggers will be used in graph making.
        # If True, only triggers in the fit file will be considered, and the fit will be plotted
        self.doFit = True                                 

        # self.useTrigList
        # If False, modify self.triggerList as neccessary
        # If True, only use triggers in self.triggerList
        self.useTrigList = False

    # Use: sets up the variables before the main loop in run()
    # Returns: (void)
    def setUp(self):
        pass
        
    # Use: Created graphs based on the information stored in the class (list of runs, fit file, etc)
    # Returns: (void)
    def run(self):
        length = len(self.runList)
        
        if self.processAll: offset = 0 # Override any offset

        # Make sure we have enough color options
        if len(self.colorList) < self.maxRuns or self.processAll:
            print "Warning: Potentially not enough unique colors for each run."

        if self.useTrigList: print "Only using triggers in current trig list." # Info message

        if self.processAll: "\nProcessing all runs in the run list." # Info message
    
        # The x and y variable names
        varX = "instLumi"      # Lumisection
        varY = "rawrate"       # Raw rate
        if not self.processAll: self.lastRun = min( [self.offset + self.maxRuns, length] )
        else: self.lastRun = length

        print "Processing %s runs:" % (self.lastRun-self.offset) # Info message

        # Info message
        if not self.doFit:
            print "Not plotting a fit."
            if not self.useTrigList:
                print "Using all possible triggers."

        minNum = min(self.runList[ self.offset : self.lastRun ])
        maxNum = max(self.runList[ self.offset : self.lastRun ])
    
        # File names and name templates
        RootNameTemplate = "HLT_%s_vs_%s_%s_Run%s-%s_cert.root"
        ErrFile = "rateMoniterNCR_%s_%s.err" % (minNum, maxNum)
        if self.doFit: fitOpt = "Fitted"
        else: fitOpt = "NoFit"
        RootFile = RootNameTemplate % (varX, varY, fitOpt, minNum, maxNum)
        
        # Remove any root files that already have that name
        if os.path.exists(RootFile): os.remove(RootFile)
        
        # Open a file for writing errors
        try: errFile = open(ErrFile, 'w')
        except: print "Could not open error file."

        # A dictionary [ trigger name ] [ run number ] { avePS, ( inst lumi's ), ( raw rates ) }
        plottingData = {}
                
        # If we are supposed to, get the fit, a dictionary: [ triggername ] [ ( fit parameters ) ]
        if self.doFit :
            InputFit = self.loadFit()
            if not self.useTrigList: self.TriggerList = sorted(InputFit)



        ### Starting the main loop ###
        print " "  # Print a newline (just for formatting)
        counter = 0 # Make sure we process at most MAX runs
        for runNumber in self.runList[self.offset : self.lastRun]:
            print "(",counter+1,") Processing run", runNumber
            
            # Get the raw rate vs iLumi
            Rates = self.parser.getRawRates(runNumber)
            iLumi = self.parser.getLumiInfo(runNumber)
            # Get the trigger list if doFit is false and we want to see all triggers (self.useTrigList is false)
            if not self.doFit and not self.useTrigList:
                for triggerName in sorted(Rates):
                    if not triggerName in self.TriggerList:
                        self.TriggerList.append(triggerName)
                #TriggerList = sorted(Rates)

            # Correct Rates for deadtime
            self.correctForDeadtime(Rates, runNumber)
            # Combine the rates and lumi into one dictionary dataList, [ trigger name ] { avePS, ( inst lumi's ), ( raw rates ) }
            dataList = self.combineInfo(Rates, iLumi)
            
            # Make plots for each trigger 
            for triggerName in self.TriggerList:
                if dataList.has_key(triggerName): # Add this run to plottingData[triggerName]
                    # Make sure the is an entry for this trigger in plottingData
                    if not plottingData.has_key(triggerName):
                        plottingData[triggerName] = {}
                    plottingData[triggerName][runNumber] = dataList[triggerName]
                else: # The trigger data was not taken from the DB or does not exist
                    # This should not occur if doFit is false, all triggers should be processed
                    message = "For run %s Trigger %s could not be processed\n" % (runNumber, triggerName)
                    errFile.write(message)

            # Make sure we only process at most MAX runs
            counter += 1
            if counter == self.maxRuns and not self.processAll:
                print "Truncating run list, final run:", runNumber,"\n"
                break # Exit the loop

        print "" # Print a newline
        # We have all our data, now plot it
        for triggerName in sorted(plottingData):
            if self.doFit: fitparams = self.getFitParams(InputFit, triggerName)
            else: fitparams = None
            self.graphAllData(plottingData[triggerName], fitparams, RootFile, triggerName)
            
        errFile.close() # Close the error file
        print "Error file saved to", ErrFile
        
        if self.saveName == "": print "File saved as %s\n" % (RootFile)
        else: print "File saved as %s\n" % (self.saveName)

    # Use: Modifies the rates in Rates, correcting them for deadtime
    # Parameters:
    # -- Rates: A dictionary [triggerName][LS] { raw rate, prescale }
    # Returns: (void), directly modifies Rates
    def correctForDeadtime(self, Rates, runNumber):
        # Get the deadtime
        deadTime = self.parser.getDeadTime(runNumber)
        for LS in deadTime:
            for triggerName in Rates:
                if Rates[triggerName].has_key(LS): # Sometimes, LS's are missing
                    Rates[triggerName][LS][0] *= (1-deadTime[LS])
                
    # Use: Combines the Rate data and instant luminosity data into a form that we can make a graph from
    # Parameters:
    # -- Rates: A dictionary [triggerName][LS] { raw rate, prescale }
    # -- iLumi: A list ( { LS, instLumi, deadTime } )
    # Returns: A dictionary: [ trigger name ] { ( inst lumi's ), ( raw rates ) }
    def combineInfo(self, Rates, iLumi):
        # Create a dictionary [ trigger name ] { ( inst lumi's ), ( raw rates ) }
        dataList = {}
        # For each trigger in Rates
        for triggerName in Rates:
            iLuminosity = array.array('f')
            rawRate = array.array('f')
            for LS, instLumi, deadTime in iLumi:
                if Rates[triggerName].has_key(LS):
                    iLuminosity.append(instLumi)           # Add the instantaneous luminosity for this LS
                    rawRate.append(Rates[triggerName][LS][0]) # Add the correspoinding raw rate
                else: pass
            dataList[triggerName] = [iLuminosity, rawRate] # The first value should be the ps value
        return dataList

    # Parameters:
    # -- InputFit: the array that contains all the fit information
    # -- triggerName: the name of the trigger that we are examining at the moment
    # Returns: A list of parameters { X0, X1, X2, X3, sigma, X0err }
    def getFitParams(self, InputFit, triggerName):
        # The fit type is the first entry in InputFit
        if not InputFit.has_key(triggerName):
            print "Trigger "+triggerName+" not here"
            return

        FitType = InputFit[triggerName][0]

        if FitType == "fit failed" or FitType == "parse failed" :
            # We will get no useful fit out of this
            print "Fit for" + triggerName + "experienced a failure" # Failure message
            return [FitType, 0, 0, 0, 0, 0, 0]
    
        else:
            X0 = InputFit[triggerName][1]
            X1 = InputFit[triggerName][2]
            X2 = InputFit[triggerName][3]
            X3 = InputFit[triggerName][4]
            sigma = InputFit[triggerName][5]*3 #Display 3 sigma band to show outliers more clearly
            X0err= InputFit[triggerName][7]
            return [FitType, X0, X1, X2, X3, sigma, X0err]

    # Parameters:
    # -- plottingData: A dictionary [ run number ] { ( inst lumi's ), ( raw rates ) }
    # -- paramList: An array [ fit type, X0, X1, X2, X3, ...##** ]
    # -- RootFile: The name of the root file that we want to save our graphs to
    # -- triggerName: The name of the trigger that we are examining
    # Returns: (void)
    def graphAllData(self, plottingData, paramList, RootFile, triggerName):        
        # Find that max and min values
        maximumRR = array.array('f')
        maximumIL = array.array('f')
        minimumIL = array.array('f')
        # Find minima and maxima so we create graphs of the right size
        for runNumber in plottingData:
            maximumRR.append(max(plottingData[runNumber][1]))
            maximumIL.append(max(plottingData[runNumber][0]))
            minimumIL.append(min(plottingData[runNumber][0]))
            
        if len(maximumRR) > 0: maxRR = max(maximumRR)
        else: return
        if len(maximumIL) > 0:
            maxIL = max(maximumIL)
            minIL = min(minimumIL)
        else: return

        # Create canvas
        nameX = "Instantaneous Luminosity"
        xunits = "(10^{30} Hz/cm^{2})"
        nameY = "Raw Rate"
        yunits = "(HZ)"
        canvas = TCanvas((self.varX+" "+xunits), (self.varY+" "+yunits), 1000, 600)
        canvas.SetName(triggerName+"_"+self.varX+"_vs_"+self.varX)

        if self.doFit:
            # Create the fit function. NOTE: We assume a linear fit was used
            funcStr = "( %s + %s * x )" % (paramList[1], paramList[2])    
            fitFunc = TF1("Fit_"+triggerName, funcStr, minIL, maxIL)
        
        # Go through all runs and plot them
        counter = 0        
        # This is the only way I have found to get an arbitrary number of graphs to be plotted on the same canvas. This took a while to get to work.
        graphList = []
        # Create legend
        top = 0.9; scaleFactor = 0.04; minimum = 0.1
        bottom = max( [top-scaleFactor*(len(plottingData)+1), minimum]) # Height we desire for the legend, adjust for number of entries
        legend = TLegend(0.9,top,1.0,bottom)
                
        for runNumber in plottingData:
            graphList.append(TGraph(len(plottingData[runNumber][0]), plottingData[runNumber][0], plottingData[runNumber][1]))

            #print "For run", runNumber, "trigger", triggerName, "has", len(plottingData[runNumber][1]), "points"
            
            # Set some stylistic settings for dataGraph
            graphList[-1].SetMarkerStyle(7)
            graphList[-1].SetMarkerSize(1.0)
            graphList[-1].SetMarkerColor(self.colorList[counter % self.maxRuns])
            # If we have more runs then colors, we just reuse colors (instead of crashing the program)
            
            graphList[-1].GetXaxis().SetTitle(nameX+" "+xunits)
            graphList[-1].GetXaxis().SetLimits(minIL, 1.1*maxIL)
            graphList[-1].GetYaxis().SetTitle(nameY+" "+yunits)
            graphList[-1].SetMinimum(0)
            graphList[-1].SetMaximum(1.2*maxRR)
            graphList[-1].SetTitle(triggerName)
            
            if counter == 0: graphList[-1].Draw("AP")
            else: graphList[-1].Draw("P")

            canvas.Update()
            legend.AddEntry(graphList[-1], "Run %s" %(runNumber))
            counter += 1

        if self.doFit:
            legend.AddEntry(fitFunc, "Fit")
            fitFunc.Draw("same") # Draw the fit function on the same graph
        legend.SetHeader("Run Legend (%s runs)" % (len(plottingData)))
        legend.Draw() 
        canvas.Update()
        # Update root file
        if self.saveName == "": file = TFile(RootFile, "UPDATE")
        else: file = TFile(self.saveName, "UPDATE")
        canvas.Modified()
        canvas.Write()
        file.Close()
        
    # Use: Loads the fit data from the fit file
    # Parameters:
    # -- fitFile: The file that the fit data is stored in (a pickle file)
    # Returns: The input fit data
    def loadFit(self):
        InputFit = {} # Initialize InputFit (as an empty dictionary)
        # Try to open the file containing the fit info
        try:
            pkl_file = open(self.fitFile, 'rb')
            InputFit = pickle.load(pkl_file)
            pkl_file.close()
        except:
            # File failed to open
            print "ERROR: could not open fit file: %s" % (fitFile)
            exit(2)
        return InputFit
        
## ----------- End of class RateMoniter ------------ #


## --- Main --- ##
if __name__ == "__main__":
    controller = MoniterController()
    controller.run()    
