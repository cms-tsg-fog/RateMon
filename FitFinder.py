#######################################################
# File: FitFinder.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 23, 2015
# Last Modified: June 24, 2015 by Nathaniel Rupprecht
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
import os
# Not all these are necessary
from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend
from ROOT import TFile, TPaveText, TBrowser

## ----------- End Imports ------------ ##

class FitFinder:
    # Default constructor for FitFinder class
    def __init__(self):
        self.GraphNumber = 0    # How many graphs we have drawn (for debugging purposes)
        self.lowLimitY = 0      # A guess at what the lower limit on what the y intercept could be
        self.hightLimitY = 0    # A guess at what the upper limit on what the y intercept could be
        self.guessY = 0         # Guess at the y intercept
        self.nBins = 20         # The number of bins that we use in guessing the slope
        self.nTrys = 15         # Number of y intercepts to try at
        self.bottomSkim = 0.15  # Portion of points with low y values that get removed
        self.topSkim = 0.0      # Portion of points with high y values that get removed
        self.saveDebug = False  # If true, we save a debug plot showing included and excluded points

    # Use: Gets a binning index based on the coordinates of a point
    # Parameters:
    # --x: An x value
    # --y: A y value
    # Returns: An int in the range [0, nBins) 
    def getIndex(self, x, y):
        # The x-0.1 is to ensure that we never get an angle of exactly pi/2 or -pi/2
        return int(self.nBins * (math.atan2((y-self.guessY)/self.yRatio, (x+0.1)/self.xRatio)/math.pi+0.5))

    # Use: Finds a linear fit for the data given to it
    # Parameters:
    # --xVals: A list of x values
    # --yVals: A list of y values
    # Returns: A tuple representing a fit: ["line", X0, X1, 0, 0, 0, 0, X0err, X1err, 0, 0] 
    def findFit(self, xVals, yVals):
        # Find some properties of the values
        length = len(xVals)
        maxX = max(xVals)
        maxY = max(yVals)
        aveY = sum(yVals)/length

        # Initialize arrays
        if self.saveDebug:
            goodX = array.array('f')
            goodY = array.array('f')
            badX = array.array('f')
            badY = array.array('f')
                
        # Estimate y intercept
        sortY = sorted(zip(yVals,xVals))
        selectY = sortY[int(self.bottomSkim*len(sortY)) : int((1-self.topSkim)*len(sortY))] # Remove bottom 20% and top 10% of points

        if self.saveDebug:
            for i in range(0, int(self.bottomSkim*len(sortY))): # Add lower points to badX, badY
                badX.append(sortY[i][1])
                badY.append(sortY[i][0])
            for i in range(int((1-self.topSkim)*len(sortY)), length): # Add upper points to badX, badY
                badX.append(sortY[i][1])
                badY.append(sortY[i][0])

        # Reset points
        yVals, xVals = zip(*selectY)
        length = len(xVals)
        self.highLimitY = 1.5*aveY
        self.lowLimitY = -0.2*aveY

        # Estimate slope
        self.xRatio = maxX   # x factor
        self.yRatio = 1.5*aveY # y factor

        # Guess at a good y intercept and slope
        [bin, maxCount] = self.tryBins(xVals, yVals)
        
        for count in range(0,length):
            index = self.getIndex(xVals[count], yVals[count])
            if abs(index - bin) <= 0:
                goodX.append(xVals[count])
                goodY.append(yVals[count])
            elif self.saveDebug: # For Debugging
                badX.append(xVals[count])
                badY.append(yVals[count])

        # The graph of good points that we will fit to
        goodPoints = TGraph(len(goodX), goodX, goodY)

        if self.saveDebug:
            canvas = TCanvas("Debug%s" % (self.GraphNumber), "y", 600, 600 )
            if len(goodX)>0:
                goodPoints.SetMarkerStyle(7)
                goodPoints.SetMarkerColor(3)
                goodPoints.SetMaximum(1.2*max(yVals))
                goodPoints.SetMinimum(0)
                goodPoints.Draw("AP")
                canvas.Update()
                
            if len(badX)>0:
                badPoints = TGraph(len(badX), badX, badY)
                badPoints.SetMarkerStyle(7)
                badPoints.SetMaximum(1.2*max(yVals))
                badPoints.SetMinimum(0)
                badPoints.Draw("P")
                canvas.Update()
        
        # Do the fit
        fitFunc = TF1("fit", "pol1", 0, max(xVals)) # First order polynomial (linear)
        result = goodPoints.Fit(fitFunc, "QNM", "rob=0.90")
        
        if self.saveDebug:
            fitFunc.Draw("same")
            canvas.Update()

            if os.path.exists("Debug.root") and self.GraphNumber == 0:
                os.remove("Debug.root")
            file = TFile("Debug.root", "UPDATE")
            self.GraphNumber += 1
            canvas.Write()
            file.Close()
            
        # For consistency with the old program
        sigma = 0
        meanrawrate = 0
        # Add fit info to the output fit
        OutputFit = ["line"]
        OutputFit += [fitFunc.GetParameter(0), fitFunc.GetParameter(1), fitFunc.GetParameter(2), fitFunc.GetParameter(3)]
        OutputFit += [sigma, meanrawrate, fitFunc.GetParError(0), fitFunc.GetParError(1), 0, 0]

        return OutputFit

    # Use: Trys out a number of binnings to see which one captures the most data within a single bin
    # Parameters:
    # --xVals: A list of x values
    # --yVals: A list of y values
    # Returns: A tuple [ bin number, counts in that bin ] for the bin with the most counts for the guessY that results in a binning
    #          whose max bin has the most counts out of all max bins in all binnings tried
    def tryBins(self, xVals, yVals):
        bin = 0
        binSlopes = []
        maxCount = 0
        diffY = self.highLimitY-self.lowLimitY
        goodGuess = 0
        # Try some number of times
        for x in range(0,self.nTrys):
            self.guessY = (float(x)/self.nTrys)*diffY + self.lowLimitY
            [testBin, testCount] = self.binData(xVals, yVals)
            if testCount > maxCount:
                maxCount = testCount
                bin = testBin
                goodGuess = self.guessY
        self.guessY = goodGuess
        return [bin, maxCount]

    # Use: Bins points according to their angle from self.guessY, finds which bin has the most points and how many points that is 
    # Parameters:
    # --xVals: A list of x values
    # --yVals: A list of y values
    # Returns: A tuple [ bin number, counts in that bin] for the bin in this binning with the most counts
    def binData(self, xVals, yVals):
        # Estimate slope
        binSlopes = [ 0 for _ in range(0,self.nBins) ] # Create empty bins
        length = len(xVals)
        for count in range(0,length):
            index = self.getIndex(xVals[count], yVals[count])
            binSlopes[ index ] += 1
            
        # Find most full bin
        maxCount = 0
        bin = 0
        for i in range(0,self.nBins): # Go through all the bins
            if binSlopes[i] > maxCount:
                maxCount = binSlopes[i]
                bin = i
        return [bin, maxCount]

## ----------- End of class FitFinder ------------ ## 
