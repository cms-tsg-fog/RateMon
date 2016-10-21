# PROGRESS: FINISHED!!
#####################################################################
# File: plotTriggerRates_rewrite.py
# Author: Charlie Mueller, Andrew Wightman, Nathaniel Carl Rupprecht
# Date Created: August 31, 2016
#
# Dependencies: None
#
# Data Type Key:
#    ( a, b, c, ... )       -- denotes a tuple
#    [ a, b, c, ... ]       -- denotes a list
#    { key:obj }            -- denotes a dictionary
#    { key1:{ key2:obj } }  -- denotes a nested dictionary
#####################################################################
import cPickle as pickle
import math
import array
import os

from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend
from ROOT import TFile, TPaveText, TBrowser

class FitFinder:
    def __init__(self):
        self.fits_to_try = ["linear","quad","cube"]
        self.use_point_selection = True

    def getGoodPoints(self, xVals, yVals):
        goodX = array.array('f')
        goodY = array.array('f')
        average_x, std_dev_x = self.getSD(xVals)
        average_y, std_dev_y = self.getSD(yVals)
        sigma_x = 4 #how many standard deviations before we cut out points
        sigma_y = 4 #how many standard deviations before we cut out points
        for x,y in zip(xVals,yVals):
            if abs(x-average_x) < sigma_x*std_dev_x and abs(y-average_y) < sigma_y*std_dev_y:
                goodX.append(x)
                goodY.append(y)

        return goodX, goodY

    #Use: Removes pts with a y-val equal to ptVal
    def removePoints(self, xVals, yVals, ptVal=0):
        arrX = array.array('f')
        arrY = array.array('f')
        for x,y in zip(xVals,yVals):
            if y != ptVal:
                arrX.append(x)
                arrY.append(y)

        return arrX, arrY

    #returns SD of PU for a given run 
    def getSD(self,xVals):
        _sum = 0
        for x in xVals: _sum += x
        try: average_x = _sum/len(xVals)
        except: return 0, 0; 
        mse = 0
        for x in xVals: mse += (x - average_x)**2

        return average_x, math.sqrt(mse/len(xVals)) 

    # Use: Finds the root of the mean squared error of a fit
    # Returns: The square root of the mean squared error
    def getMSE(self, fitFunc, xVals, yVals):
        mse = 0
        for x,y in zip(xVals, yVals):
            mse += (fitFunc.Eval(x) - y)**2

        return math.sqrt(mse/len(xVals))

    def emptyFit(self):
        maxX = 1
        linear = TF1("Linear Fit", "pol1", 0, maxX)
        OutputFit = ["linear"]
        OutputFit += [0, 0, 0, 0]
        OutputFit += [0, 0, 0, 0, 0, 0]
        OutputFit += [0]

        return OutputFit

    def tryFit(self, xVals, yVals, name, fit_type):
        supported_fits = ["linear","quad","cube","exp"]
        if not fit_type in supported_fits:
            print "Fit not supported, generating empty fit..."
            return self.emptyFit()

        #print "x-vals: %d" % len(xVals)
        #print "y-vals: %d" % len(yVals)
        #print "Trigger: %s" % name
        #print "Type: %s" % fit_type


        # Set up graph and functions
        fitGraph = TGraph(len(xVals), xVals, yVals)
        maxX = max(xVals)

        if fit_type == "linear":
            fit_func = TF1("Linear Fit","pol1",0,maxX)
        elif fit_type == "quad":
            fit_func = TF1("Quadratic Fit","pol2",0,maxX)
        elif fit_type == "cube":
            fit_func = TF1("Cubic Fit" ,"pol3",0,maxX)
        elif fit_type == "exp":
            fit_func = TF1("Exp Fit","[0]+[1]*expo(2)",0,maxX)

        fitGraph.Fit(fit_func,"QNM","rob=0.90")
        fitMSE = self.getMSE(fit_func,xVals,yVals)

        OutputFit = [fit_type]
        OutputFit += [fit_func.GetParameter(0),fit_func.GetParameter(1),fit_func.GetParameter(2),fit_func.GetParameter(3)]
        OutputFit += [fitMSE, 0, fit_func.GetParError(0), fit_func.GetParError(1), fit_func.GetParError(2), fit_func.GetParError(3)]
        OutputFit += [fit_func.GetChisquare()]

        return OutputFit

    def findFit(self, xVals, yVals, name, default="quad"):
        output_fits = {}
        if self.use_point_selection:
            goodX, goodY = self.getGoodPoints(xVals,yVals)
            goodX, goodY = self.removePoints(goodX,goodY,0)
        else:
            goodX, goodY = xVals, yVals

        if len(goodX) == 0 or len(goodY) == 0:
            print "%s: No points - generating empty fit..." % name
            print "\tlen(xVals): %s" % len(goodX)
            print "\tlen(yVals): %s" % len(goodY)
            return self.emptyFit()

        for fit_type in self.fits_to_try:
            output_fits[fit_type] = self.tryFit(goodX,goodY,name,fit_type)

        return output_fits[default]

        ## ----------- End of class FitFinder ------------ ## 