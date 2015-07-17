#######################################################
# File: RateMonitorNCR.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 16, 2015
# Last Modified: July 10, 2015 by Nathaniel Rupprecht
#
# Dependencies: DBParser.py, FitFinder.py, ErrorPrinter.py
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
from ROOT import TFile, TPaveText, TBrowser, TLatex
import os
import sys
# Import the DB interface class
from DBParser import *
# From the fit finding class
from FitFinder import *
# For Printing errors
from ErrorPrinter import *

## ----------- End Imports ------------ ##

# Class RateMonitor:
# Analyzes the rate vs instantaneous luminosity behavior of runs (held in a run list called self.runList) and make plots of the data
# Can also plot a fit from a given pickle file on the plots it produces
# Contains an instance of DBParser to get information from the database
class RateMonitor:
    # Default constructor for RateMonitor class
    def __init__(self):
        # Set ROOT properties
        gROOT.SetBatch(True) # Use batch mode so plots are not spit out in X11 as we make them
        gStyle.SetPadRightMargin(0.2) # Set the canvas right margin so the legend can be bigger

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
        self.saveDirectory = ""  # A directory that we can save all our files in if we are in batch mode
        self.nameGiven = False   # Whether a user defined name was given as the save name
        
        self.parser = DBParser() # A database parser
        self.lastRun = 0         # The last run in the run list that will be considered
        self.TriggerList = []    # The list of triggers to consider in plot-making 

        # Trigger Options
        self.L1Triggers = False  # If True, then we get the L1 trigger Data
        self.HLTTriggers = True  # If True, then we get the HLT trigger Data
        self.savedAFile = False  # True if we saved at least one file

        # Error File Options
        self.makeErrFile = False # If true, we will write an error file
        self.errFileName = ""    # The name of the error file
        self.errFile = None      # A file to output errors to
        
        self.mode = False        # False -> Primary mode, True -> Secondary mode
        self.runsToProcess = 12  # How many runs we are about to process
        self.outputOn = True     # If true, print messages to the screen
        self.sigmas = 3.0        # How many sigmas the error bars should be
        
        self.allRates = {}       # Retain a copy of rates to use for validating lumisections later on: [ runNumber ] [ triggerName ] [ LS ] { rawRate, ps }
        self.predictionRec = {}  # A dictionary used to store predictions and prediction errors: [ triggerName ] { ( LS ), ( prediction ), (error) }
        self.minStatistics = 10  # The minimum number of points that we will allow for a run and still consider it
        self.fit = False         # If true, we fit the data to fit functions
        self.InputFit = None     # The fit from the fit file that we open
        self.OutputFit = None    # The fit that we can make in primary mode
        self.outFitFile = ""     # The name of the file that we will save an output fit to
        self.fitFinder = FitFinder()  # A fit finder object
        self.divByBunches = False     # If true, we divide by the number of colliding bunches
        self.bunches = 1         # The number of colliding bunches if divByBunches is true, 1 otherwise
        self.includeNoneBunches = False  # Whether we should plot data from runs where we can't get the number of colliding bunches
        
        # Batch mode variables
        self.batchSize = 12      # Number of runs to process in a single batch
        self.batchMode = False   # If true, we will process all the runs in batches of size (self.batchSize)
        self.maxBatches = 9999   # Then maximum number of batches we will do when using batch mode

        # Steam Compair
        self.steam = False       # If true, we plot a steam prediction
        self.steamFile = ""      # The csv file with the steam data
        self.steamData = {}      # Steam Data, gotten from the steam file
        self.steamILumi = 5000   # For what inst lumi the steam prediction is for (currently 5e33)

        # Cuts
        self.lumiCut = 0.1       # The lumi cut value
        self.doLumiCut = True    # If true, we only plot data points with inst lumi > self.lumiCut
        self.rateCut = 0.0       # The rate cut value
        self.doRateCut = True    # If true, we only plot data points with rate > self.rateCut
        self.minPointsToFit = 10 # The minimum number of points we need to make a fit

        # self.useFit:
        # If False, no fit will be plotted and all possible triggers will be used in graph making.
        # If True, only triggers in the fit file will be considered, and the fit will be plotted
        self.useFit = True                                 

        # self.useTrigList
        # If False, modify self.triggerList as neccessary to include as many triggers as possible
        # If True, only use triggers in self.triggerList
        self.useTrigList = False

    # Use: sets up the variables before the main loop in run()
    # Returns: (void)
    def setUp(self):
        if self.outputOn: print "" # Formatting
        length = len(self.runList)
        self.bunches = 1 # Reset bunches, just in case
        if self.mode: self.varX = "LS" # We are in secondary mode
        if self.processAll: offset = 0 # Override any offset
        # Reset self.savedAFile
        self.savedAFile = False
        # Make sure we have enough color options
        if len(self.colorList) < self.maxRuns or self.processAll and self.outputOn:
            print "Warning: Potentially not enough colors to have a unique one for each run." # Info message

        # Make a fit of the data
        if self.steam:
            self.fit = True
        
        if not self.useFit and self.outputOn:
            if not self.fit: print "Not plotting a fit."
            if not self.useTrigList:
                print "Using all possible triggers."

        if self.fit and self.outputOn:
            print "Creating a fit from data."

        if self.useTrigList and self.outputOn: print "Only using triggers in current trig list." # Info message
        if self.processAll:
            if self.outputOn: print "\nProcessing all runs in the run list." # Info message
            self.lastRun = length
        else: self.lastRun = min( [self.offset + self.maxRuns, length] )

        self.runsToProcess = self.lastRun-self.offset
        if self.runsToProcess > 1: plural = "s" # Get our grammar right
        else: plural = ""

        if self.outputOn: print "Processing %s run%s:" % (self.runsToProcess, plural) # Info message
        
        minNum = min(self.runList[ self.offset : self.lastRun ])
        maxNum = max(self.runList[ self.offset : self.lastRun ])

        # If we are supposed to, get the fit, a dictionary: [ triggername ] [ ( fit parameters ) ]
        if self.useFit or self.mode: # Always try to load a fit in secondary mode
            self.InputFit = self.loadFit()
            if not self.useTrigList and not self.InputFit is None: self.TriggerList = sorted(self.InputFit)
        
        # File names and name templates
        RootNameTemplate = "HLT_%s_vs_%s_%s_Run%s-%s_Tot%s_cert.root"
        if self.outFitFile=="": self.outFitFile = "HLT_Fit_Run%s-%s_Tot%s_fit.pkl" % (minNum, maxNum, self.runsToProcess)
        if self.useFit or self.fit or (self.mode and not self.InputFit is None): fitOpt = "Fitted"
        else: fitOpt = "NoFit"
        if not self.nameGiven: self.saveName = RootNameTemplate % (self.varX, self.varY, fitOpt, minNum, maxNum, self.runsToProcess)

        if self.saveDirectory != "": # Save in the right directory
            if not os.path.exists(self.saveDirectory):
                os.mkdir(self.saveDirectory)
                print "Created the directory %s as it did not already exist." % (self.saveDirectory)
            self.saveName = self.saveDirectory + "/" + self.saveName

        # Remove any root files that already have that name
        if os.path.exists(self.saveName): os.remove(self.saveName)

        # Open a file for writing errors
        if self.makeErrFile:
            self.errFileName = "rateGrapher_%s_%s.err" % (minNum, maxNum) # Define the error file name
            try: self.errFile = open(self.errFileName, 'w')
            except: print "Could not open error file."

        # If we are going to save fit find debug graph, delete any old ones
        if self.fitFinder.saveDebug and os.path.exists("Debug.root"): os.remove("Debug.root")

    def runBatch(self):
        total = 0 # How many runs we have processed so far
        count = 1 # Iteration variable
        if not self.processAll: print "Batch size is %s." % (self.maxRuns) # Info message
        while total < len(self.runList) and (count <= self.maxBatches or self.processAll):
            print "Processing batch %s:" % (count)
            self.offset = total
            self.run()
            total += self.runsToProcess # Update the count by how many runs we just processed
            count += 1
            print "" # Newline for formatting
        if self.mode: # Operating in secondary mode, do checks
            self.doChecks()
    
    # Use: Created graphs based on the information stored in the class (list of runs, fit file, etc)
    # Returns: (void)
    def run(self):
        # Set up parameters and data structures
        self.setUp()
        
        # A dictionary [ trigger name ] [ run number ] { ( inst lumi's || LS ), ( raw rates ) }
        plottingData = {}
                
        ### Starting the main loop ###
        if self.outputOn: print ""  # Print a newline (just for formatting)
        counter = 0 # Make sure we process at most MAX runs
        for runNumber in self.runList[self.offset : self.lastRun]:
            print "(",counter+1,") Processing run", runNumber

            # Get number of bunches (if requested)
            if self.divByBunches:
                self.bunches = self.parser.getNumberCollidingBunches(runNumber)
                if self.bunches is None and not self.includeNoneBunches:
                    print "Cannot get number of bunches for this run: skipping this run.\n"
                    counter += 1
                    continue # Skip this run
                print "Run %s has %s bunches.\n" % (runNumber, self.bunches)
                
            # Get run info in a dictionary: [ trigger name ] { ( inst lumi's ), ( raw rates ) }
            dataList = self.getData(runNumber)

            if dataList == {}:
                # The run does not exist (or some other critical error occured)
                print "Fatal error for run %s, could not retrieve data. Moving on." % (runNumber) # Info message
                counter += 1
                continue
                
            # Make plots for each trigger
            for triggerName in self.TriggerList:
                if dataList.has_key(triggerName): # Add this run to plottingData[triggerName]
                    # Make sure the is an entry for this trigger in plottingData
                    if not plottingData.has_key(triggerName):
                        plottingData[triggerName] = {}
                    plottingData[triggerName][runNumber] = dataList[triggerName]
                elif self.makeErrFile: # The trigger data was not taken from the DB or does not exist
                    # This should not occur if useFit is false, all triggers should be processed
                    message = "For run %s Trigger %s could not be processed\n" % (runNumber, triggerName)
                    self.errFile.write(message)

            # Make sure we only process at most MAX runs
            counter += 1
            if counter == self.maxRuns and not self.processAll:
                if self.outputOn: print "Truncating run list, final run:", runNumber,"\n"
                break # Exit the loop
            
        # If we are fitting the data
        if self.fit:
            self.findFit(plottingData)
        if self.outputOn: print "" # Print a newline

        # Get our steam data
        if self.steam:
            self.loadSteamData()
        # We have all our data, now plot it
        if self.useFit or (self.mode and not self.InputFit is None): fitparams = self.InputFit
        elif self.fit: fitparams = self.OutputFit # Plot the fit that we made
        else: fitparams = None
        for triggerName in sorted(plottingData):
            if fitparams is None or not fitparams.has_key(triggerName): fit = None
            else: fit = fitparams[triggerName]
            self.graphAllData(plottingData[triggerName], fit, triggerName)
        # Print steam checks
        if self.steam:
            self.steamChecks()
        # Try to close the error file
        if self.makeErrFile:
            try:
                self.errFile.close() # Close the error file
                print "Error file saved to", self.errFileName # Info message
            except: print "Could not save error file."
        if self.fitFinder.saveDebug and self.fitFinder.usePointSelection:
            print "Fit finder debug file saved to Debug.root.\n" # Info message
        if self.savedAFile: print "File saved as %s" % (self.saveName) # Info message
        else: print "No files were saved. Perhaps none of the triggers you requested were in use for this run"
        if self.outputOn: print "" # Final newline for formatting

    # Use: Gets the data we desire in primary mode (rawrate vs inst lumi) or secondary mode (rawrate vs LS)
    # Parameters:
    # -- runNumber: The number of the run we want data from
    # Returns: A dictionary:  [ trigger name ] { ( inst lumi's || LS ), ( raw rates ) }
    def getData(self, runNumber):
        Rates = {}
        # Get the HLT raw rate vs LS
        if self.HLTTriggers:
            Rates = self.parser.getRawRates(runNumber)
        # Get the L1 raw rate vs LS
        if self.L1Triggers:
            L1Rates = self.parser.getL1RawRates(runNumber)
            Rates.update(L1Rates)
        
        if Rates == {}: return {} # The run (probably) doesn't exist
        # If we are in primary mode, we need luminosity info, otherwise, we just need the physics bit
        iLumi = self.parser.getLumiInfo(runNumber)
        # Get the trigger list if useFit is false and we want to see all triggers (self.useTrigList is false)
        if not self.useFit and not self.useTrigList:
            for triggerName in sorted(Rates):
                if not triggerName in self.TriggerList:
                    self.TriggerList.append(triggerName)
        # Correct Rates for deadtime
        self.correctForDeadtime(Rates, runNumber)
        self.allRates[runNumber] = Rates
        # Depending on the mode, we return different pairs of data
        if not self.mode:
            # Combine the rates and lumi into one dictionary, [ trigger name ] { ( inst lumi's ), ( raw rates ) } and return
            return self.combineInfo(Rates, iLumi)
        else: # self.mode == True
            return self.sortRates(Rates, iLumi)

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
    # -- iLumi: A list ( { LS, instLumi, cms active } )
    # Returns: A dictionary: [ trigger name ] { ( inst lumi's ), ( raw rates ) }
    def combineInfo(self, Rates, iLumi):
        # Create a dictionary [ trigger name ] { ( inst lumi's ), ( raw rates ) }
        dataList = {}
        # For each trigger in Rates
        for triggerName in Rates:
            iLuminosity = array.array('f')
            rawRate = array.array('f')
            for LS, ilum, phys in iLumi:
                if Rates[triggerName].has_key(LS) and not ilum is None:
                    # We apply our cuts here if they are called for
                    normedILumi = ilum/self.bunches
                    rate = Rates[triggerName][LS][0]
                    if (not self.doLumiCut or normedILumi > self.lumiCut) and (not self.doRateCut or rate > self.rateCut) and phys:
                        iLuminosity.append(ilum/self.bunches)     # Add the instantaneous luminosity for this LS
                        rawRate.append(rate) # Add the correspoinding raw rate
                else: pass

            if len(iLuminosity) > 0:
                dataList[triggerName] = [iLuminosity, rawRate]
            else: pass
        return dataList

    # Use: Combines the Rate data and instant luminosity data into a form that we can make a graph from
    # Parameters:
    # -- Rates: A dictionary [ triggerName ] [ LS ] { raw rate, prescale }
    # Returns: A dictionary: [ trigger name ] { ( LS ), ( raw rates ) }
    def sortRates(self, Rates, iLumi):
        # Create a dictionary [ trigger name ] { ( LS ), (raw rates ) }
        dataList = {}
        for triggerName in Rates:
            lumisecs = array.array('f')
            rawRate = array.array('f')

            for LS, _, phys in iLumi:
                if phys and Rates[triggerName].has_key(LS):
                    lumisecs.append(LS)
                    rawRate.append(Rates[triggerName][LS][0])
            dataList[triggerName] = [lumisecs, rawRate]
        return dataList

    # Use: Graphs the data from all runs and triggers onto graphs and saves them to the root file
    # Parameters:
    # -- plottingData: A dictionary [ run number ] { ( inst lumi's ), ( raw rates ) }
    # -- paramlist: A tuple: { FitType, X0, X1, X2, X3, sigma, meanrawrate, X0err, X1err, X2err, X3err } 
    # -- triggerName: The name of the trigger that we are examining
    # Returns: (void)
    def graphAllData(self, plottingData, paramlist, triggerName):        
        # Find that max and min values
        maximumRR = array.array('f')
        maximumVals = array.array('f')
        minimumVals = array.array('f')
        # Find minima and maxima so we create graphs of the right size
        for runNumber in plottingData:
            if len(plottingData[runNumber][0]) > 0: # It can happen that this is not true, though I'm not sure how
                maximumRR.append(max(plottingData[runNumber][1]))
                maximumVals.append(max(plottingData[runNumber][0]))
                minimumVals.append(min(plottingData[runNumber][0]))

        if len(maximumRR) > 0: maxRR = max(maximumRR)
        else: return
        if len(maximumVals) > 0:
            maxVal = max(maximumVals)
            minVal = min(minimumVals)
        else: return
        if maxVal==0 or maxRR==0: # No good data
            return
        # Set axis names/units, create canvas
        if self.mode:
            xunits = "(LS)"
            nameX = "Lumisection"
        else:
            xunits = "(10^{30} Hz/cm^{2})"
            nameX = "Instantaneous Luminosity"
        nameY = "Raw Rate"
        if self.divByBunches :
            nameX += "/ (num colliding bunches)"
        yunits = "(HZ)"
        canvas = TCanvas((self.varX+" "+xunits), (self.varY+" "+yunits), 1000, 600)
        canvas.SetName(triggerName+"_"+self.varX+"_vs_"+self.varY)
        funcStr = ""
        if (self.useFit or self.fit) and not paramlist is None:
            # Create the fit function.
            if paramlist[0]=="exp": funcStr = "%s + %s*expo(%s+%s*x)" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Exponential
            else: funcStr = "%s+x*(%s+ x*(%s+x*%s))" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Polynomial
            fitFunc = TF1("Fit_"+triggerName, funcStr, minVal, maxVal)
        # Go through all runs and plot them
        counter = 0        
        # This is the only way I have found to get an arbitrary number of graphs to be plotted on the same canvas. This took a while to get to work.
        graphList = []
        # Create legend
        left = 0.8; right = 1.0; top = 0.9; scaleFactor = 0.05; minimum = 0.1
        bottom = max( [top-scaleFactor*(len(plottingData)+1), minimum]) # Height we desire for the legend, adjust for number of entries
        legend = TLegend(left,top,right,bottom)

        # We only load the iLumi info for one of the runs to make the prediction, use the run with the most LS's
        pickRun = 0
        maxLS = 0
        for runNumber in plottingData:
            numLS = len(plottingData[runNumber][0])
            if numLS == 0: continue
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
            graphList[-1].SetMarkerColor(self.colorList[counter % len(self.colorList)]) # If we have more runs then colors, we just reuse colors (instead of crashing the program)
            graphList[-1].GetXaxis().SetTitle(nameX+" "+xunits)
            graphList[-1].GetXaxis().SetLimits(0, 1.1*maxVal)
            graphList[-1].GetYaxis().SetTitle(nameY+" "+yunits)
            graphList[-1].SetMinimum(0)
            graphList[-1].SetMaximum(1.2*maxRR)
            graphList[-1].SetTitle(triggerName)
            if counter == 0: graphList[-1].Draw("AP")
            else: graphList[-1].Draw("P")

            canvas.Update()
            legend.AddEntry(graphList[-1], "Run %s" %(runNumber))
            counter += 1
        # There is steam data to use, and we should use it
        if self.steam and self.steamData and self.steamData.has_key(triggerName):
            try:
                Xval = array.array('f'); Xval.append(self.steamILumi) # Steam data point
                Yval = array.array('f'); Yval.append(float(self.steamData[triggerName][0]))
                Xerr = array.array('f'); Xerr.append(0.0)
                Yerr = array.array('f'); Yerr.append(float(self.steamData[triggerName][1]))
                steamGraph = TGraphErrors(1, Xval, Yval, Xerr, Yerr)
                steamGraph.SetMarkerStyle(3)
                steamGraph.SetMarkerSize(3)
                steamGraph.SetMarkerColor(2)
                steamGraph.Draw("P")
            except: pass # Sometimes, this might fail if there are two items seperated by commas in the Group column
        if (self.useFit or self.fit or self.mode or self.steam) and not paramlist is None:
            if self.mode: # Secondary Mode
                # Make a prediction graph of raw rate vs LS for values between minVal and maxVal
                iLumi = self.parser.getLumiInfo(pickRun)
                # iLumi is a list: ( { LS, instLumi } )
                fitGraph = self.makeFitGraph(paramlist, minVal, maxVal, maxRR, iLumi, triggerName)
                fitGraph.Draw("PZ3")
                canvas.Update()
                legend.AddEntry(fitGraph, "Fit (%s sigmas)" % (self.sigmas))
            else: # Primary Mode
                legend.AddEntry(fitFunc, "Fit")
                fitFunc.Draw("same") # Draw the fit function on the same graph
        # Draw function string on the plot
        if not funcStr == "":
            funcLeg = TLegend(.146, .71, .57, .769)
            funcLeg.SetHeader("f(x) = " + funcStr)
            funcLeg.SetFillColor(0)
            funcLeg.Draw()
            canvas.Update()
        # Draw Legend
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

    # Use: Get a fit for all the data that we have collected
    # Parameters:
    # -- plottingData: A dictionary [triggerName] [ run number ] { ( inst lumi's ), ( raw rates ) }
    # Returns: (void)
    def findFit(self, plottingData):
        self.OutputFit = {}
        # Combine data
        for triggerName in sorted(plottingData):
            instLumis = array.array('f')
            rawRates = array.array('f')
            for runNumber in sorted(plottingData[triggerName]):
                # Combine all data
                instLumis += plottingData[triggerName][runNumber][0]
                rawRates += plottingData[triggerName][runNumber][1]

            if len(instLumis) > self.minPointsToFit:
                self.OutputFit[triggerName] = self.fitFinder.findFit(instLumis, rawRates, triggerName)
            else:
                print "Not enough points to fit %s, we need %s, we have %s" % (triggerName, self.minPointsToFit, len(instLumis))
        # Save the fit
        self.saveFit()

    # Use: Save a fit to a file
    def saveFit(self):
        outputFile = open(self.outFitFile, "wb")
        pickle.dump(self.OutputFit, outputFile, 2)
        outputFile.close()

        self.sortFit()

        print "\nFit file saved to", self.outFitFile # Info message

    # Use: Sorts trigger fits by their chi squared value and writes it to a file
    def sortFit(self):
        outputFile = open("SortedChiSqr.txt", "wb")

        chisqrDict = {}
        for trigger in self.OutputFit:
            _,_,_,_,_,_,_,_,_,_,_,chisqr = self.OutputFit[trigger]
            chisqrDict[chisqr] = trigger

        for chisqr in sorted(chisqrDict):
            outputFile.write(chisqrDict[chisqr] + ": " + str(chisqr) + "\n")
        outputFile.close
        print "Sorted chi-square saved to SortedChiSqr.txt"
            
    # Use: Creates a graph of predicted raw rate vs lumisection data
    # Parameters:
    # -- paramlist: A tuple of parameters { FitType, X0, X1, X2, X3, sigma, meanrawrate, X0err, X1err, X2err, X3err, ChiSqr } 
    # -- minVal: The minimum LS
    # -- maxVal: The maximum LS
    # -- maxRR: The maximum raw rate (y value)
    # -- iLumi: A list: ( { LS, instLumi } )
    # -- triggerName: The name of the trigger we are making a fit for
    # Returns: A TGraph of predicted values
    def makeFitGraph(self, paramlist, minVal, maxVal, maxRR, iLumi, triggerName):
        # Initialize our point arrays
        lumisecs = array.array('f')
        predictions = array.array('f')
        lsError = array.array('f')
        predError = array.array('f')
        # Unpack values
        type, X0, X1, X2, X3, sigma, meanraw, X0err, X1err, X2err, X3err, ChiSqr = paramlist
        # Create our point arrays
        for LS, ilum in iLumi:
            if not ilum is None:
                lumisecs.append(LS)
                # Either we have an exponential fit, or a polynomial fit
                if type == "exp": rr = X0 + X1*math.exp(X2+X3*x)
                else: rr = X0 + ilum*X1 + (ilum**2)*X2 + (ilum**3)*X3 # Maybe save some multiplications
                if rr<0: rr=0 # Make sure prediction is non negative
                predictions.append(rr)
                lsError.append(0)
                predError.append(self.sigmas*sigma)
        # Record for the purpose of doing checks
        self.predictionRec[triggerName] = zip(lumisecs, predictions, predError) # Put these lists together into a list of triples
        # Set some graph options
        fitGraph = TGraphErrors(len(lumisecs), lumisecs, predictions, lsError, predError)
        fitGraph.SetTitle("Fit (%s sigma)" % (self.sigmas)) 
        fitGraph.SetMarkerStyle(8)
        fitGraph.SetMarkerSize(0.8)
        fitGraph.SetMarkerColor(2) # Red
        fitGraph.SetFillColor(4)
        fitGraph.SetFillStyle(3003)
        fitGraph.GetXaxis().SetLimits(minVal, 1.1*maxVal)
        
        return fitGraph
        
    # Use: Loads the fit data from the fit file
    # Parameters:
    # -- fitFile: The file that the fit data is stored in (a pickle file)
    # Returns: The input fit data
    def loadFit(self):
        if self.fitFile == "":
            print "No fit file specified."
            return None
        InputFit = {} # Initialize InputFit (as an empty dictionary)
        # Try to open the file containing the fit info
        try:
            pkl_file = open(self.fitFile, 'rb')
            InputFit = pickle.load(pkl_file)
            pkl_file.close()
        except:
            # File failed to open
            print "Error: could not open fit file: %s" % (self.fitFile)
        return InputFit

    # Use: Loads the data from a steam created google doc (downloaded to a .csv file)
    def loadSteamData(self):
        try:
            # Assume the group column has been deleted
            steam_file = open(self.steamFile, 'rb')
            count = 0
            for line in steam_file:
                if count < 2:
                    count += 1
                    continue
                tuple = line.split(',')
                triggerName = stripVersion(tuple[0])
                if not self.steamData.has_key(triggerName):
                    self.steamData[triggerName] = [float(tuple[1]), float(tuple[3])]
            steam_file.close()
        except:
            # File failed to open
            print "ERROR: could not open steam file:", self.steamFile

    # Use: Check raw rates in lumisections against the prediction, take note if any are outside a certain sigma range
    # Returns: (void)
    def doChecks(self):
        eprint = ErrorPrinter()
        # Look at all lumisections for each trigger for each run. Check which ones are behaving badly
        for triggerName in self.TriggerList: # We may want to look at the triggers from somewhere else, but for now I assume this will work
            for runNumber in self.allRates:
                if self.predictionRec.has_key(triggerName):
                    if self.allRates[runNumber].has_key(triggerName): # In case some run did not contain this trigger
                        data = self.allRates[runNumber][triggerName]
                        predList = self.predictionRec[triggerName]
                        for LS, pred, err in predList:
                            if data.has_key(LS): # In case this LS is missing
                                if(abs(data[LS][0] - pred) > err):
                                    if err != 0: errStr = str((data[LS][0]-pred)/err)
                                    else: errStr = "inf"
                                    # Add data to eprint.run_ls_trig
                                    if not eprint.run_ls_trig.has_key(runNumber):
                                        eprint.run_ls_trig[runNumber] = {}
                                    if not eprint.run_ls_trig[runNumber].has_key(int(LS)):
                                        eprint.run_ls_trig[runNumber][int(LS)] = []
                                    eprint.run_ls_trig[runNumber][LS].append(triggerName)
                                    # Add data to eprint.run_trig_ls
                                    if not eprint.run_trig_ls.has_key(runNumber):
                                        eprint.run_trig_ls[runNumber] = {}
                                    if not eprint.run_trig_ls[runNumber].has_key(triggerName):
                                        eprint.run_trig_ls[runNumber][triggerName] = []
                                    eprint.run_trig_ls[runNumber][triggerName].append(int(LS))

        eprint.outputErrors()

    # Use: Checks fit predictions against steam predictions given to us in a .csv file
    # Returns: (void)
    def steamChecks(self):
        sprint = ErrorPrinter()
        for triggerName in self.steamData:
            if triggerName in self.TriggerList and self.OutputFit.has_key(triggerName):
                paramlist = self.OutputFit[triggerName]
                if paramlist[0]=="exp":
                    funcStr = "%s + %s*expo(%s+%s*x)" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Exponential
                    minFStr = "(%s+%s) + (%s+%s)*expo((%s+%s)+(%s+%s)*x)" % (paramlist[1], paramlist[7], paramlist[2], paramlist[8],
                                                                             paramlist[3], paramlist[9], paramlist[4], paramlist[10])
                    maxFStr = "(%s-%s) + (%s-%s)*expo((%s-%s)+(%s-%s)*x)" % (paramlist[1], paramlist[7], paramlist[2], paramlist[8],
                                                                             paramlist[3], paramlist[9], paramlist[4], paramlist[10])
                else:
                    funcStr = "%s+x*(%s+ x*(%s+x*%s))" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Polynomial
                    minFStr = "(%s+%s)+x*((%s+%s) + x*((%s+%s) + x*(%s+%s)))" % (paramlist[1], paramlist[7], paramlist[2], paramlist[8],
                                                                                 paramlist[3], paramlist[9], paramlist[4], paramlist[10])
                    maxFStr = "(%s-%s)+x*((%s-%s) + x*((%s-%s) + x*(%s-%s)))" % (paramlist[1], paramlist[7], paramlist[2], paramlist[8],
                                                                                 paramlist[3], paramlist[9], paramlist[4], paramlist[10])

                fitFunc = TF1("Fit_"+triggerName, funcStr, 0, 1.2*self.steamILumi)
                maxFunc = TF1("Max_"+triggerName, maxFStr, 0, 1.2*self.steamILumi)
                minFunc = TF1("Min_"+triggerName, minFStr, 0, 1.2*self.steamILumi)
                ilum = self.steamILumi
                sprint.steamData[triggerName] = [fitFunc.Eval(ilum), minFunc.Eval(ilum), maxFunc.Eval(ilum),
                                                 self.steamData[triggerName][0], self.steamData[triggerName][1]] # [ prediction, min predict, max predict, actual, error ]
        sprint.outputSteamErrors()
## ----------- End of class RateMonitor ------------ ##
