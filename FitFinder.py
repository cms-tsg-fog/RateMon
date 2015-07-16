#######################################################
# File: FitFinder.py
# Author: Nathaniel Carl Rupprecht
# Date Created: June 23, 2015
# Last Modified: July 8, 2015 by Nathaniel Rupprecht
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
        self.GraphNumber = 0          # How many graphs we have drawn (for debugging purposes)
        self.lowLimitY = 0            # A guess at what the lower limit on what the y intercept could be
        self.hightLimitY = 0          # A guess at what the upper limit on what the y intercept could be
        self.guessY = 0               # Guess at the y intercept
        self.guessX = 0               # An x value to do the binning at
        self.nBins = 20               # The number of bins that we use in guessing the slope
        self.nTrys = 15               # Number of y intercepts to try at
        self.bottomSkim = 0.15        # Portion of points with low y values that get removed
        self.topSkim = 0.0            # Portion of points with high y values that get removed
        self.saveDebug = False        # If true, we save a debug plot showing included and excluded points
        self.usePointSelection = True # If true, we use an algorithm to pick out "good" points to fit to
        self.forceLinear = False      # If true, we only try a linear fit
        self.preferLinear = 0.05      # If linear is within (self.preferLinear) of the min MSE, we still pick the linear (even if it has greater MSE)
        self.fit = None               # The fit function, a TF1

        self.goodPoints = None        # List of good points (for debugging
        self.badPoints = None         # List of bad points (for debugging)

    # Use: Trys to find the best fit to a set of points that is either an order < 4 poly or an exponential
    # This is the function that is called by the Rate Monitor class
    def findFit(self, xVals, yVals, name):
        # Point selectoin
        if self.usePointSelection: goodX, goodY = self.getGoodPoints2(xVals, yVals)
        else: goodX, goodY = xVals, yVals
        # Fitting
        if self.forceLinear: return self.findLinearFit(xVals, yVals, name)
        else: return self.tryFits(goodX, goodY, name)

    # Use: Gets a binning index based on the coordinates of a point
    # Parameters:
    # -- x: An x value
    # -- y: A y value
    # Returns: An int in the range [0, nBins) 
    def getIndex(self, x, y):
        # The x-0.1 is to ensure that we never get an angle of exactly pi/2 or -pi/2
        return int(self.nBins * (math.atan2((y-self.guessY)/self.yRatio, (x-self.guessX)/self.xRatio)/math.pi+0.5))

    # Use: Determines which points are good and returns them
    # Returns: A pair, { goodX, goodY }
    def getGoodPoints(self, xVals, yVals):
        # Find some properties of the values
        length = len(xVals)

        if length <= 0:
            print "No points."
            return

        maxX = max(xVals)
        maxY = max(yVals)
        aveY = sum(yVals)/length
        
        # Initialize arrays
        goodX = array.array('f')
        goodY = array.array('f')
        if self.saveDebug:
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
        self.lowLimitY = -0.5*aveY
        
        # Estimate slope
        self.xRatio = max([maxX,1])     # x factor
        self.yRatio = max([1.5*aveY,1]) # y factor
        self.guessX = min(xVals) - 0.1  # Minimum x value
        
        # Guess at a good y intercept and slope
        bin, maxCount = self.tryBins(xVals, yVals)
        
        for count in range(0,length):
            index = self.getIndex(xVals[count], yVals[count])
            if abs(index - bin) <= 0:
                goodX.append(xVals[count])
                goodY.append(yVals[count])
            elif self.saveDebug: # For Debugging
                badX.append(xVals[count])
                badY.append(yVals[count])

        if self.saveDebug:
            if len(goodX)>0:
                goodPoints = TGraph(len(goodX), goodX, goodY)
                goodPoints.SetMarkerStyle(7)
                goodPoints.SetMarkerColor(3)
                goodPoints.SetMaximum(1.2*max(yVals))
                goodPoints.SetMinimum(0)
                self.goodPoints = goodPoints
            if len(badX)>0:
                badPoints = TGraph(len(badX), badX, badY)
                badPoints.SetMarkerStyle(7)
                badPoints.SetMarkerColor(2)
                badPoints.SetMaximum(1.2*max(yVals))
                badPoints.SetMinimum(0)
                self.badPoints = badPoints
                
        return goodX, goodY

    # Use: Trys out a number of binnings to see which one captures the most data within a single bin
    # Parameters:
    # -- xVals: A list of x values
    # -- yVals: A list of y values
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
    # -- xVals: A list of x values
    # -- yVals: A list of y values
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

    # Use: Trys to fit the data to quadratic, cubic, and exponential fits
    # Parameters:
    # -- xVals: x values
    # -- yVals: y values
    # Returns: The best fit
    def tryFits(self, xVals, yVals, name):
        # Set up graph and functions
        fitGraph = TGraph(len(xVals), xVals, yVals)
        maxX = max(xVals)
        linear = TF1("Linear Fit", "pol1", 0, maxX)
        quad = TF1("Quad Fit", "pol2", 0, maxX)
        cube = TF1("Cubic Fit", "pol3", 0, maxX)
        exp = TF1("Exp Fit", "[0]+[1]*expo", 0, maxX)

        fitGraph = TGraph(len(xVals), xVals, yVals)
        # Linear Fit
        maxY = max(yVals)
        minY = min(yVals)
        maxindex = yVals.index(maxY)
        minindex = yVals.index(minY)
        slopeGuess = (maxY-minY)/(xVals[maxindex]-xVals[minindex])
        
        linear.SetParameters(0, slopeGuess)
        fitGraph.Fit(linear, "QNM", "rob=0.90")
        linearMSE = self.getMSE(linear, xVals, yVals)
        # Quadratic Fit
        quad.SetParameters(linear.GetParameter(0), linear.GetParameter(1), 0) # Seed with the parameters from the linear fit
        fitGraph.Fit(quad, "QNM", "rob=0.90")
        quadMSE = self.getMSE(quad, xVals, yVals)
        # Cubic Fit
        cube.SetParameters(quad.GetParameter(0), quad.GetParameter(1), quad.GetParameter(2), 0) # Seed with the parameters from the quadratic fit
        fitGraph.Fit(cube, "QNM", "rob=0.90")
        cubeMSE = self.getMSE(cube, xVals, yVals)
        # Exponential fit
        
        fitGraph.Fit(exp, "QNM", "rob=0.90")
        expMSE = self.getMSE(exp, xVals, yVals)

        # Define lists for finding best fit
        fitList = [linear, quad, cube, exp]
        mseList = [linearMSE, quadMSE, cubeMSE, expMSE]
        titleList = ["linear", "quad", "cube", "exp"]
        minMSE = min([linearMSE, quadMSE, cubeMSE, expMSE]) # Find the minimum MSE

        # Save debug graph
        if self.saveDebug and self.usePointSelection and name != "preprocess":
            self.saveDebugGraph(fitList, titleList, name, fitGraph)

        if self.forceLinear or (minMSE != 0 and (linearMSE-minMSE)/minMSE < self.preferLinear):
            OutputFit = ["linear"]
            OutputFit += [linear.GetParameter(0), linear.GetParameter(1), 0, 0]
            OutputFit += [minMSE, 0, linear.GetParError(0), linear.GetParError(1), 0, 0]
            OutputFit += [linear.GetChisquare()]
            self.fit = linear
            return OutputFit

        pickFit = ""
        for i in range(0,4):
            if minMSE == mseList[i]:
                pickFit = fitList[i]
                title = titleList[i]
                break
        
        # Set output fit and return
        self.fit = pickFit
        OutputFit = [title]
        OutputFit += [pickFit.GetParameter(0), pickFit.GetParameter(1), pickFit.GetParameter(2), pickFit.GetParameter(3)]
        OutputFit += [minMSE, 0, pickFit.GetParError(0), pickFit.GetParError(1), pickFit.GetParError(2), pickFit.GetParError(3)]
        OutputFit += [pickFit.GetChisquare()]

        return OutputFit

    # Use: Gets the best linear fit of the data
    # Returns: An output fit tuple
    def findLinearFit(self, xVals, yVals, name):
        maxX = 1.2*max(xVals)
        linear = TF1("Linear Fit", "pol1", 0, maxX)
        fitGraph = TGraph(len(xVals), xVals, yVals)
        fitGraph.Fit(linear, "QNM", "rob=0.90")
        linearMSE = self.getMSE(linear, xVals, yVals)
        self.fit = linear
        OutputFit = ["linear"]
        OutputFit += [linear.GetParameter(0), linear.GetParameter(1), 0, 0]
        OutputFit += [linearMSE, 0, linear.GetParError(0), linear.GetParError(1), 0, 0]
        OutputFit += [linear.GetChisquare()]

        fitList = [linear]
        titleList = ["linear"]
        # Save debug graph
        if self.saveDebug and self.usePointSelection and name != "preprocess":
            self.saveDebugGraph(fitList, titleList, name, fitGraph)
        
        return OutputFit
        
    # Use: Finds the root of the mean squared error of a fit
    # Returns: The square root of the mean squared error
    def getMSE(self, fitFunc, xVals, yVals):
        mse = 0
        for x,y in zip(xVals, yVals):
            mse += (fitFunc.Eval(x) - y)**2
        return math.sqrt(mse/len(xVals))

    # Use: Another method of getting good points to make a fit from
    def getGoodPoints2(self, xVals, yVals):
        if self.forceLinear: paramlist = self.findLinearFit(xVals, yVals, "preprocess")
        else: paramlist = self.tryFits(xVals, yVals, "preprocess")
        minMSE = paramlist[5]
        goodX = array.array('f')
        badX = array.array('f')
        goodY = array.array('f')
        badY = array.array('f')

        for x,y in zip(xVals,yVals):
            eval = self.fit.Eval(x)
            if eval + 1.5*minMSE > y and y > eval - 1.5*minMSE :
                goodX.append(x)
                goodY.append(y)
            elif self.saveDebug: # For Debugging
                badX.append(x)
                badY.append(y)
                    
        if self.saveDebug:
            if len(goodX)>0:
                goodPoints = TGraph(len(goodX), goodX, goodY)
                goodPoints.SetMarkerStyle(7)
                goodPoints.SetMarkerColor(3)
                goodPoints.SetMaximum(1.2*max(yVals))
                goodPoints.SetMinimum(0)
                self.goodPoints = goodPoints
            if len(badX)>0:
                badPoints = TGraph(len(badX), badX, badY)
                badPoints.SetMarkerStyle(7)
                badPoints.SetMarkerColor(2)
                badPoints.SetMaximum(1.2*max(yVals))
                badPoints.SetMinimum(0)
                self.badPoints = badPoints

        return goodX, goodY

                
    def saveDebugGraph(self, fitList, titleList, name, fitGraph):
        canvas = TCanvas("Debug_%s" % (name), "y", 1000, 700)
        # Add a legend
        legend = TLegend(0.8, 0.9, 1.0, 0.7)
        legend.SetHeader("Fits:")
        # Remove Debug.root if it already exists
        if os.path.exists("Debug.root") and self.GraphNumber == 0:
            os.remove("Debug.root")
            self.GraphNumber += 1
            
        # Make sure we did point skimming and created goodPoints and badPoints
        if not self.goodPoints is None: # goodPoints and badPoints are created together, so we only need to check one
            self.goodPoints.Draw("AP3")
            self.badPoints.Draw("P3")
            legend.AddEntry(self.goodPoints, "Good Points")
            legend.AddEntry(self.badPoints, "Bad Points")
        else:
            fitGraph.SetMarkerColor(4)
            fitGraph.SetMarkerStyle(7)
            fitGraph.Draw("AP3")
            
        count = 0 # Counting variable
        for fit in fitList:  # Draw fits
            legend.AddEntry(fit, titleList[count])
            fit.SetLineColor(count+6)
            fit.Draw("same")
            canvas.Update()
            count += 1
        legend.Draw()
        canvas.Update()
        file = TFile("Debug.root", "UPDATE")
        canvas.Write()
        file.Close()
            
## ----------- End of class FitFinder ------------ ## 
