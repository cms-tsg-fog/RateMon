#######################################################
# File: RateMoniterNCR.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 16, 2015
# Last Modified: June 22, 2015 by Nathaniel Rupprecht
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
# Import the DB interface class
from DBParser import *

## ----------- End Imports ------------ #

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
        self.varY = "rawRate"     # Plot the prescaled rate on the y axis
        self.saveName = ""       # A name that we save the root file as
        self.nameGiven = False   # Whether a user defined name was given as the save name
        self.parser = DBParser() # A database parser
        self.lastRun = 0         # The last run in the run list that will be considered
        self.TriggerList = []    # The list of triggers to consider in plot-making 
        self.savedAFile = False  # True if we saved at least one file
        self.makeErrFile = False # If true, we will write an error file
        self.errFileName = ""    # The name of the error file
        self.errFile = None      # A file to output errors to
        self.mode = False        # False -> Primary mode, True -> Secondary mode
        self.runsToProcess = 12  # How many runs we are about to process
        self.outputOn = True     # If true, print messages to the screen

        # Batch mode variables
        self.batchSize = 12      # Number of runs to process in a single batch
        self.batchMode = False   # If true, we will process all the runs in batches of size (self.batchSize)
        self.maxBatches = 999    # Then maximum number of batches we will do when using batch mode

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
        if self.outputOn: print "" # Formatting
        length = len(self.runList)
        if self.mode: self.varX = "LS" # We are in secondary mode
        if self.processAll: offset = 0 # Override any offset
        
        # Make sure we have enough color options
        if len(self.colorList) < self.maxRuns or self.processAll and self.outputOn:
            print "Warning: Potentially not enough unique colors for each run." # Info message

        # Info message
        if not self.doFit and self.outputOn:
            print "Not plotting a fit."
            if not self.useTrigList:
                print "Using all possible triggers."

        if self.mode and self.outputOn: print "Secondary Mode in use"
        if self.useTrigList and self.outputOn: print "Only using triggers in current trig list." # Info message
        if self.processAll:
            if self.outputOn: print "\nProcessing all runs in the run list." # Info message
            self.lastRun = length
        else: self.lastRun = min( [self.offset + self.maxRuns, length] )

        self.runsToProcess = self.lastRun-self.offset
        if self.runsToProcess > 1: plural = "s"
        else: plural = ""

        if self.outputOn: print "Processing %s run%s:" % (self.runsToProcess, plural) # Info message
                    
        minNum = min(self.runList[ self.offset : self.lastRun ])
        maxNum = max(self.runList[ self.offset : self.lastRun ])
        
        # File names and name templates
        RootNameTemplate = "HLT_%s_vs_%s_%s_Run%s-%s_cert.root"
        if self.doFit: fitOpt = "Fitted"
        else: fitOpt = "NoFit"
        if not self.nameGiven: self.saveName = RootNameTemplate % (self.varX, self.varY, fitOpt, minNum, maxNum)
        
        # Remove any root files that already have that name
        if os.path.exists(self.saveName): os.remove(self.saveName)

        # Open a file for writing errors
        if self.makeErrFile:
            self.errFileName = "rateGrapher_%s_%s.err" % (minNum, maxNum) # Define the error file name
            try: self.errFile = open(self.errFileName, 'w')
            except: print "Could not open error file."

    def runBatch(self):
        self.processAll = False # This should already be false
        total = 0 # How many runs we have processed so far
        count = 1
        while total < len(self.runList) and count <= self.maxBatches:
            print "Processing batch %s:" % (count)
            self.offset = total
            self.run()
            total += self.runsToProcess # Update the count by how many runs we just processed
            count += 1
            print "" # Newline for formatting
    
    # Use: Created graphs based on the information stored in the class (list of runs, fit file, etc)
    # Returns: (void)
    def run(self):
        # Set up parameters and data structures
        self.setUp()
        
        # A dictionary [ trigger name ] [ run number ] { ( inst lumi's || LS ), ( raw rates ) }
        plottingData = {}
                
        # If we are supposed to, get the fit, a dictionary: [ triggername ] [ ( fit parameters ) ]
        if self.doFit :
            InputFit = self.loadFit()
            if not self.useTrigList: self.TriggerList = sorted(InputFit)

        ### Starting the main loop ###
        if self.outputOn: print ""  # Print a newline (just for formatting)
        counter = 0 # Make sure we process at most MAX runs
        for runNumber in self.runList[self.offset : self.lastRun]:
            print "(",counter+1,") Processing run", runNumber
            # Get run info in a dictionary: [ trigger name ] { ( inst lumi's ), ( raw rates ) }
            dataList = self.getData(runNumber)
            
            # Make plots for each trigger 
            for triggerName in self.TriggerList:
                if dataList.has_key(triggerName): # Add this run to plottingData[triggerName]
                    # Make sure the is an entry for this trigger in plottingData
                    if not plottingData.has_key(triggerName):
                        plottingData[triggerName] = {}
                    plottingData[triggerName][runNumber] = dataList[triggerName]
                elif self.makeErrFile: # The trigger data was not taken from the DB or does not exist
                    # This should not occur if doFit is false, all triggers should be processed
                    message = "For run %s Trigger %s could not be processed\n" % (runNumber, triggerName)
                    self.errFile.write(message)

            # Make sure we only process at most MAX runs
            counter += 1
            if counter == self.maxRuns and not self.processAll:
                if self.outputOn: print "Truncating run list, final run:", runNumber,"\n"
                break # Exit the loop

        if self.outputOn: print "" # Print a newline
        # We have all our data, now plot it
        for triggerName in sorted(plottingData):
            if self.doFit: fitparams = self.getFitParams(InputFit, triggerName)
            else: fitparams = None
            self.graphAllData(plottingData[triggerName], fitparams, triggerName)
        # Try to close the error file
        if self.makeErrFile:
            try:
                self.errFile.close() # Close the error file
                print "Error file saved to", self.errFileName # Info message
            except: print "Could not save error file."
        # End message
        if self.savedAFile: print "File saved as %s" % (self.saveName) # Info message
        else: print "No files were saved. Perhaps none of the triggers you requested were in use for this run"
        if self.outputOn: print "" # Final newline for formatting

    # Use: Gets the data we desire in primary mode (rawrate vs inst lumi) or secondary mode (rawrate vs LS)
    # Parameters:
    # -- runNumber: The number of the run we want data from
    # Returns: A dictionary:  [ trigger name ] { ( inst lumi's || LS ), ( raw rates ) }
    def getData(self, runNumber):
        # Get the raw rate vs iLumi
        Rates = self.parser.getRawRates(runNumber)
        # If we are in primary mode, we need luminosity info
        if not self.mode: iLumi = self.parser.getLumiInfo(runNumber)
        # Get the trigger list if doFit is false and we want to see all triggers (self.useTrigList is false)
        if not self.doFit and not self.useTrigList:
            for triggerName in sorted(Rates):
                if not triggerName in self.TriggerList:
                    self.TriggerList.append(triggerName)
                    
        # Correct Rates for deadtime
        self.correctForDeadtime(Rates, runNumber)

        if self.mode == False:
            # Combine the rates and lumi into one dictionary, [ trigger name ] { ( inst lumi's ), ( raw rates ) } and return
            return self.combineInfo(Rates, iLumi)
        else: # self.mode == True
            return self.sortRates(Rates)

    # Use: Modifies the rates in Rates, correcting them for deadtime
    # Parameters:
    # -- Rates: A dictionary [ triggerName ] [ LS ] { raw rate, prescale }
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
    # -- Rates: A dictionary [ triggerName ] [ LS ] { raw rate, prescale }
    # -- iLumi: A list ( { LS, instLumi } )
    # Returns: A dictionary: [ trigger name ] { ( inst lumi's ), ( raw rates ) }
    def combineInfo(self, Rates, iLumi):
        # Create a dictionary [ trigger name ] { ( inst lumi's ), ( raw rates ) }
        dataList = {}
        # For each trigger in Rates
        for triggerName in Rates:
            iLuminosity = array.array('f')
            rawRate = array.array('f')
            for LS, ilum in iLumi:
                if Rates[triggerName].has_key(LS):
                    iLuminosity.append(ilum)           # Add the instantaneous luminosity for this LS
                    rawRate.append(Rates[triggerName][LS][0]) # Add the correspoinding raw rate
                else: pass
            dataList[triggerName] = [iLuminosity, rawRate]
        return dataList

    # Use: Combines the Rate data and instant luminosity data into a form that we can make a graph from
    # Parameters:
    # -- Rates: A dictionary [ triggerName ] [ LS ] { raw rate, prescale }
    # Returns: A dictionary: [ trigger name ] { ( LS ), ( raw rates ) }
    def sortRates(self, Rates):
        # Create a dictionary [ trigger name ] { ( LS ), (raw rates ) }
        dataList = {}
        for triggerName in Rates:
            lumisecs = array.array('f')
            rawRate = array.array('f')
            for LS in Rates[triggerName]:
                lumisecs.append(LS)
                rawRate.append(Rates[triggerName][LS][0])
            dataList[triggerName] = [lumisecs, rawRate]
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
    # -- triggerName: The name of the trigger that we are examining
    # Returns: (void)
    def graphAllData(self, plottingData, paramList, triggerName):        
        # Find that max and min values
        maximumRR = array.array('f')
        maximumVals = array.array('f')
        minimumVals = array.array('f')
        # Find minima and maxima so we create graphs of the right size
        for runNumber in plottingData:
            maximumRR.append(max(plottingData[runNumber][1]))
            maximumVals.append(max(plottingData[runNumber][0]))
            minimumVals.append(min(plottingData[runNumber][0]))
        if len(maximumRR) > 0: maxRR = max(maximumRR)
        else: return
        if len(maximumVals) > 0:
            maxVal = max(maximumVals)
            minVal = min(minimumVals)
        else: return

        # Set axis names/units, create canvas
        if self.mode:
            xunits = "(LS)"
            nameX = "Lumisection"
        else:
            xunits = "(10^{30} Hz/cm^{2})"
            nameX = "Instantaneous Luminosity"
        nameY = "Raw Rate"
        yunits = "(HZ)"
        canvas = TCanvas((self.varX+" "+xunits), (self.varY+" "+yunits), 1000, 600)
        canvas.SetName(triggerName+"_"+self.varX+"_vs_"+self.varY)

        if self.doFit and not paramList is None:
            # Create the fit function. NOTE: We assume a linear fit was used
            funcStr = "( %s + %s * x )" % (paramList[1], paramList[2])    
            fitFunc = TF1("Fit_"+triggerName, funcStr, minVal, maxVal)
        # Go through all runs and plot them
        counter = 0        
        # This is the only way I have found to get an arbitrary number of graphs to be plotted on the same canvas. This took a while to get to work.
        graphList = []
        # Create legend
        top = 0.9; scaleFactor = 0.04; minimum = 0.1
        bottom = max( [top-scaleFactor*(len(plottingData)+1), minimum]) # Height we desire for the legend, adjust for number of entries
        legend = TLegend(0.9,top,1.0,bottom)

        # We only load the iLumi info for one of the runs to make the prediction, use the run with the most LS's
        pickRun = 0
        maxLS = 0
                
        for runNumber in plottingData:
            numLS = len(plottingData[runNumber][0])
            # See if this run has more LS's then the previous runs
            if numLS > maxLS:
                maxLS = numLS
                pickRun = runNumber
            graphList.append(TGraph(numLS, plottingData[runNumber][0], plottingData[runNumber][1]))
            # Set some stylistic settings for dataGraph
            graphList[-1].SetMarkerStyle(7)
            graphList[-1].SetMarkerSize(1.0)
            graphList[-1].SetLineColor(0)
            graphList[-1].SetFillColor(0)
            graphList[-1].SetMarkerColor(self.colorList[counter % self.maxRuns]) # If we have more runs then colors, we just reuse colors (instead of crashing the program)
            graphList[-1].GetXaxis().SetTitle(nameX+" "+xunits)
            graphList[-1].GetXaxis().SetLimits(minVal, 1.1*maxVal)
            graphList[-1].GetYaxis().SetTitle(nameY+" "+yunits)
            graphList[-1].SetMinimum(0)
            graphList[-1].SetMaximum(1.2*maxRR)
            graphList[-1].SetTitle(triggerName)
            
            if counter == 0: graphList[-1].Draw("AP")
            else: graphList[-1].Draw("P")

            canvas.Update()
            legend.AddEntry(graphList[-1], "Run %s" %(runNumber))
            counter += 1


        if self.doFit and not paramList is None:
            if self.mode:
                # Make a prediction graph of raw rate vs LS for values between minVal and maxVal
                iLumi = self.parser.getLumiInfo(pickRun)
                # iLumi is a list: ( { LS, instLumi } )
                fitGraph = self.makeFitGraph(fitFunc, minVal, maxVal, maxRR, iLumi)
                fitGraph.Draw("P3")
                canvas.Update()
                legend.AddEntry(fitGraph)
            else:
                legend.AddEntry(fitFunc, "Fit")
                fitFunc.Draw("same") # Draw the fit function on the same graph
        legend.SetHeader("Run Legend (%s runs)" % (len(plottingData)))
        legend.SetFillColor(0)
        legend.Draw() 
        canvas.Update()
        # Update root file
        file = TFile(self.saveName, "UPDATE")
        canvas.Modified()
        canvas.Write()
        file.Close()
        self.savedAFile = True

    # Use: Creates a graph of predicted raw rate vs lumisection data
    # Parameters:
    # -- fitFunc: The fit function (a TF1)
    # -- minVal: The minimum LS
    # -- maxVal: The maximum LS
    # -- maxRR: The maximum raw rate (y value)
    # -- iLumi: A list: ( { LS, instLumi } )
    # Returns: A TGraph of predicted values
    def makeFitGraph(self, fitFunc, minVal, maxVal, maxRR, iLumi):
        # Initialize our point arrays
        lumisecs = array.array('f')
        predictions = array.array('f')
        # Create our point arrays
        for LS, ilum in iLumi:
            if not ilum is None:
                lumisecs.append(LS)
                predictions.append(fitFunc.Eval( ilum ))
        # Set some graph options
        fitGraph = TGraph(len(lumisecs), lumisecs, predictions)
        fitGraph.SetMarkerStyle(7)
        fitGraph.SetMarkerSize(1.0)
        fitGraph.SetMarkerColor(2) # Red
        fitGraph.GetXaxis().SetLimits(minVal, 1.1*maxVal)
        
        return fitGraph
        
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
