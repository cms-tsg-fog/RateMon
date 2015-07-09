#######################################################
# File: ErrorPrinter
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
import array
# Not all these are necessary
from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend

## ----------- End Imports ------------ ##

# Class ErrorPrinter:
# Has member variables representing the runs, triggers, and lumisections that were irregular.
# Is able to output this information to an error file
class ErrorPrinter:
    # Default constructor for ErrorPrinter class
    def __init__(self):
        self.run_trig_ls = {} # [ runNumber ] [ triggerName ] ( LS )
        self.run_ls_trig = {} # [ runNumber ] [ LS ] ( triggerName )
        self.steamData = {}   # [ prediction, min predict, max predict, actual, error ]

    # Use: Outputs information to a file
    def outputErrors(self):
        # Output all kinds of info to a file
        try:
            file = open("OutLSErrors.err", 'w') # come up with a name based on something about the runs
            print "Opening OutLSErrors.err for LS error dump."
        except:
            print "Error: could not open file to output ls data."
            return
        
        for runNumber in sorted(self.run_trig_ls):
            file.write("Run Number: %s\n" % (runNumber))
            totalErrs = 0
            for triggerName in sorted(self.run_trig_ls[runNumber]):
                file.write("     %s: " % (triggerName))
                for LS in sorted(self.run_trig_ls[runNumber][triggerName]):
                    file.write("%s " % (LS))
                    totalErrs += 1
                file.write("\n")
            file.write("---- Total bad LS: %s \n" % (totalErrs))
            file.write("---- Ave bad LS per trigger: %s \n" % (totalErrs/len(self.run_trig_ls[runNumber])))
            file.write("\n")
                    
        file.close()

    def outputSteamErrors(self):
        try:
            file = open("OutSteamErrors.err", 'w') # come up with a better name for this too sometime
            print "Opening OutSteamErrors.err for LS error dump."
        except:
            print "Error: could non open file to output steam data."

        TriggersInError = []

        file.write("\nTrigger and Prediction Data: \n\n")
        file.write("***********************************************************\n\n\n")

        # self.steamData -> [ prediction, min predict, max predict, actual, error ]
        for triggerName in sorted(self.steamData):
            fitpred = self.steamData[triggerName][0] # The prediction based on the fit function we created
            steampred = self.steamData[triggerName][3] # The prediction based on the steam .csv file
            steamerr = self.steamData[triggerName][4]  # The error based on the steam .csv file
            upper = steampred + steamerr               # The upper error range on the steam data
            lower = steampred - steamerr               # The lower error range on the steam data
            high = self.steamData[triggerName][1]      # The upper error prediction based on the uncertainty of our fit
            low = self.steamData[triggerName][2]       # The lower error prediction based on the uncertainty of our fit  

            file.write("%s: Acceptable range: %s - %s\n" % (triggerName, lower, upper))
            file.write("     Predicted value (from fit): %s \n" % (str(fitpred)))
            file.write("     Uncertainty in fit yeilds range: %s - %s\n" % ( str(low), str(high) ) )
            
            if self.steamData[triggerName][0] <= upper and lower <= self.steamData[triggerName][0] :
                file.write("     This is fine.\n\n")
            else:
                file.write("     ---> Prediction does not fall within steam uncertainty")
                if (fitpred < lower and high > lower) or (fitpred > upper and low < upper):
                    file.write(", but uncertainty in the fit can explain this discrepancy.\n\n")
                else:
                    file.write("\n----- ERROR: Not in acceptable range. -----\n\n")
                    TriggersInError.append(triggerName)

        file.write("\n\n***********************************************************\nSUMMARY of TRIGGERS in ERROR:")
        if len(TriggersInError) == 0:
            file.write("     No errors. All triggers we could check were good.\n")
        else: file.write("\n")
        for triggerName in TriggersInError:
            file.write("     " + triggerName + "\n")
        file.close()
        
## ----------- End class ErrorPrinter ----------- #
