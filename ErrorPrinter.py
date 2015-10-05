#######################################################
# File: ErrorPrinter
# Author: Nathaniel Carl Rupprecht Charlie Mueller
# Date Created: July 9, 2015
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

#prints bad LS in JSON format
def formatJSON(lumisection_list):
    list = "[" 
    minLS = lumisection_list[0]
    maxLS = minLS
    for i in range(1,len(lumisection_list)):
        if lumisection_list[i] > lumisection_list[i-1] + 1:
            list = list+"["+str(minLS)+","+str(maxLS)+"], "
            minLS = lumisection_list[i]
            maxLS = minLS
        else:
            maxLS = lumisection_list[i]
    if list == "[": list = "[["+str(minLS)+","+str(maxLS)+"]]"
    else: list = list+"["+str(minLS)+","+str(maxLS)+"]]"
    return list

# Class ErrorPrinter:
# Has member variables representing the runs, triggers, and lumisections that were irregular.
# Is able to output this information to an error file
class ErrorPrinter:
    # Default constructor for ErrorPrinter class
    def __init__(self):
        self.run_trig_ls = {} # [ runNumber ] [ triggerName ] ( LS )
        self.run_ls_trig = {} # [ runNumber ] [ LS ] ( triggerName )
        self.run_allLs = {} # [runNumber][triggerName] (LS)
        self.steamData = {}   # [ prediction, min predict, max predict, actual, error ]
        self.saveDirectory = "" #directory where output txt files are saved
        
    # Use: Outputs information to a file
    def outputErrors(self):
        # Output all kinds of info to a file
        sortedRuns = sorted(self.run_trig_ls)
        try:
            fileName = "badLumiSummary_run"+str(sortedRuns[0])+"_run"+str(sortedRuns[-1])+".txt"
            file = open(fileName, 'w') # come up with a name based on something about the runs
            print "Opening %s for LS error dump." % (fileName)            
        except:
            print "Error: could not open file to output ls data."
            return

        for runNumber in sortedRuns:
            file.write("Run Number: %s\n" % (runNumber))
            totalErrs = 0

            badLumiList = {}
            badLumiListSorted = {}

            for triggerName in sorted(self.run_trig_ls[runNumber]):
                file.write("     %s: " % (triggerName))
                list = formatJSON(sorted(self.run_trig_ls[runNumber][triggerName]))
                file.write(list+"\n")
                
                for LS in sorted(self.run_trig_ls[runNumber][triggerName]):
                    if badLumiList.has_key(LS): badLumiList[LS] += 1
                    else: badLumiList[LS] = 1

            file.write("\n")
            #sort the dict so the number of bad triggers is now the key
            for LS in sorted(badLumiList.keys(), key=badLumiList.__getitem__, reverse =True):
                if badLumiListSorted.has_key(badLumiList[LS]):
                    badLumiListSorted[badLumiList[LS]].append(LS)
                else:
                    badLumiListSorted[badLumiList[LS]] = [LS]

            file.write("     # of bad paths : lumis section(s)\n")
            for numBadTrigs in sorted(badLumiListSorted.keys(), reverse =True):                
                    file.write("     %s : %s\n"%(numBadTrigs, sorted(badLumiListSorted[numBadTrigs])))
                    totalErrs += len(sorted(badLumiListSorted[numBadTrigs]))

            for triggerName in self.run_allLs[runNumber]:
                totalLumis = len(self.run_allLs[runNumber][triggerName])
                break
            fractionBadLumis = 100.*float(totalErrs)/float(totalLumis)

            file.write("\n---- Total bad LS: %s  ( bad LS: >= 1 trigger(s) deviating more than 3 sigma from prediction )\n" % (totalErrs))
            file.write("---- Total LS: %s\n" % (totalLumis))
            file.write("---- Fraction bad LS: %s%% \n" % (fractionBadLumis))
            
        file.close()

    def outputSteamErrors(self):
        try:
            file = open("OutSteamErrors.err", 'w') # come up with a better name for this too sometime
            print "Opening OutSteamErrors.err for Steam comparison error dump."
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

            file.write("%s: STEAM prediction range: %s - %s\n" % (triggerName, lower, upper))
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
