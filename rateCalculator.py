#######################################################
# File: LumiWizard.py
# Author: Nathaniel Carl Rupprecht
# Date Created: July 9, 2015
# Last Modified: July 9, 2015 by Nathaniel Rupprecht
#
# Dependencies: None
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects
####################################################### 

# Imports
import getopt # For getting command line options
import sys
import cPickle as pickle
from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend

## ----------- End Imports ------------ #

class LumiWizard:

    def __init__(self):
        self.instLumi = 0                   # The instantaneous luminosity
        self.bunches = 1                    # The number of colliding bunches
        self.fitFile = ""                   # The name of the fit file
        self.outName = "predict.csv"        # The name of the file that we dump the data to
        self.InputFit = {}                  # The fit that we make our predictions from
        self.acceptableChiSquared = 10      # The chi squared acceptance threshold

    def parseArgs(self):
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["saveName=", "fitFile=", "bunches=", "instLumi=", "Help"])
        except:
            print "Error geting options: command unrecognized. Exiting."
            return False

        if len(opt)==0:
            print "We need some options to run the program, a fit file, the number of bunches, and the instantaneous luminosity."
            print "Use python LumiWizard.py --Help to see the help menu."
            return False
        # Parse arguments
        for label, op in opt:
            if label == "--saveName":
                self.outName = str(op)
            if label == "--fitFile":
                self.fitFile = str(op)
            if label == "--bunches":
                self.bunches = int(op)
            if label == "--instLumi":
                self.instLumi = float(op)
            if label == "--Help":
                self.printOptions()
        return True

    # Use: Prints out all the command line options that can be used
    def printOptions(self):
        print ""
        print "Usage: python LumiWizard.py [Options]"
        print "Note that instantaneous luminosities are times 10^30"
        print ""
        print "Options:"
        print "--fitFile=<name>      : The name of the file that your fit is stored in."
        print "--bunches=<num>       : The number of colliding bunches you want your predictions to be made for."
        print "--instLumi=<num>         : The instantaneous luminosity that you want to make your prediction at."
        print "--Help                : Prints this help message. But you probably already know that."
        print ""
        print "Program by Nathaniel Rupprecht, created July 9, 2015. For questions, email nrupprec@nd.edu"

    def run(self):
        if self.parseArgs():
            self.loadFit(self.fitFile)
            self.makePredictions()

    # Use: Loads the fit data from the fit file
    # Parameters:
    # -- fitFile: The file that the fit data is stored in (a pickle file)
    # Returns: The input fit data 
    def loadFit(self, fileName):
        InputFit = {} # Initialize InputFit (as an empty dictionary)
        # Try to open the file containing the fit info
        try:
            pkl_file = open(self.fitFile, 'rb')
            self.InputFit = pickle.load(pkl_file)
            pkl_file.close()
        except:
            # File failed to open
            print "ERROR: could not open fit file: %s" % (self.fitFile)
            exit(2)
                    
    def makePredictions(self):
        # Open a file to write to
        if self.outName == "":
            print "No out file specified. Exiting"
            exit()
        try:
            file = open(self.outName, 'wb')
        except:
            print "Output file failed to open. Exiting."
            exit()
        # Iterate over all triggers
        file.write("TRIGGERNAME, PREDICTION or ERROR, CHI SQUARED (of fit function)\n\n")
        for triggerName in self.InputFit:
            paramlist = self.InputFit[triggerName]
            # TODO: we might have different acceptable Chi squared thresholds for each trigger
            if paramlist[11] > self.acceptableChiSquared : 
                file.write(triggerName + ", Poor fit - no prediction, ChiSqr=%s\n" % (paramlist[11]))
            else:
                if paramlist[0]=="exp": funcStr = "%s + %s*expo(%s+%s*x)" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Exponential
                else: funcStr = "%s+x*(%s+ x*(%s+x*%s))" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4]) # Polynomial
                fitFunc = TF1("Fit_"+triggerName, funcStr, 0.8*self.instLumi, 1.1*self.instLumi)
                # Make the prediction, write it to the file
                pred = fitFunc.Eval(self.instLumi*self.bunches)
                file.write(triggerName + ", " + str(pred) + ", %s\n" % paramlist[11])
        file.close()
        print "Wrote prediction to %s" % (self.outName)

## ----------- End of class LumiWizard ------------ #

## ----------- Main -----------## 
if __name__ == "__main__":
    LW = LumiWizard()
    LW.run()
