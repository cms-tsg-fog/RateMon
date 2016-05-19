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

import array
from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend, TFile, TLine, TLatex, TH1D

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
        gStyle.SetOptStat(0)

    # Use: Outputs information to a file
    def outputErrors(self):
        # Output all kinds of info to a file
        rootFileName = "%s/CertificationSummaries.root" % (self.saveDirectory)
        rootFile = TFile(rootFileName,"RECREATE")
        print "\nWriting summary root file %s" % (rootFileName)

        sortedRuns = sorted(self.run_trig_ls)
        try:
            fileName = "CertificationSummary_run"+str(sortedRuns[0])+"_run"+str(sortedRuns[-1])+".txt"
            file = open(self.saveDirectory+"/"+fileName, 'w') # come up with a name based on something about the runs
            print "\nCertification Summary txt file:  %s/%s \n" % (self.saveDirectory,fileName)            
        except:
            print "Error writing certification summary ."
            return

        for runNumber in sortedRuns:
            file.write("Run Number: %s\n" % (runNumber))
            file.write("\n")
            file.write("     TRIGGERS: BAD LUMIECTION(S) \n")
            file.write("\n")

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

            totalLumis = len( self.run_allLs[runNumber][self.run_allLs[runNumber].keys()[0]] )
            minLumi = min( self.run_allLs[runNumber][self.run_allLs[runNumber].keys()[0]] )
            maxLumi = max( self.run_allLs[runNumber][self.run_allLs[runNumber].keys()[0]] )
            #            maxNumBadPaths = sorted(badLumiListSorted.keys(), reverse =True)[0]
            maxNumBadPaths = len( self.run_allLs[runNumber] )

            canvas = TCanvas("can", "can", 1000, 600)
            canvas.SetName("Certification Summary of Run %s" % runNumber)
            canvas.SetGridx(1);
            canvas.SetGridy(1); 
            summaryHist = TH1D("Certification_Summary_of_Run%s" % (runNumber), "Run %s" % (runNumber), (totalLumis+2), (minLumi-1), (maxLumi+1))
            summaryHist.GetXaxis().SetTitle("LS")
            summaryHist.GetYaxis().SetTitle("Number of bad paths")
            summaryHist.SetMaximum(1.2 * maxNumBadPaths)


            #sort the dict so the number of bad triggers is now the key
            for LS in sorted(badLumiList.keys(), key=badLumiList.__getitem__, reverse =True):
                summaryHist.Fill(LS,badLumiList[LS])
                if badLumiListSorted.has_key(badLumiList[LS]):
                    badLumiListSorted[badLumiList[LS]].append(LS)
                else:
                    badLumiListSorted[badLumiList[LS]] = [LS]
            testVariable = 0
            file.write("     # OF BAD PATHS : LUMISECTION(S)\n")
            file.write("\n")
            for numBadTrigs in sorted(badLumiListSorted.keys(), reverse =True):
                testVariable += numBadTrigs*(len(sorted(badLumiListSorted[numBadTrigs])))                
                file.write("     %s : %s\n"%(numBadTrigs, sorted(badLumiListSorted[numBadTrigs])))
                totalErrs += len(sorted(badLumiListSorted[numBadTrigs]))

            maxLine = TLine(minLumi-1, maxNumBadPaths, maxLumi+1, maxNumBadPaths)
            maxLine.SetLineStyle(9)
            maxLine.SetLineColor(2)
            maxLine.SetLineWidth(2)

            summaryHist.Draw("hist")
            summaryHist.SetLineColor(4)
            summaryHist.SetFillColor(4)
            summaryHist.SetFillStyle(3004)
            canvas.Update()
            latex = TLatex()
            latex.SetNDC()
            latex.SetTextColor(1)
            latex.SetTextAlign(11)
            latex.SetTextFont(62)
            latex.SetTextSize(0.05)
            latex.DrawLatex(0.15, 0.84, "CMS")
            latex.SetTextSize(0.035)
            latex.SetTextFont(52)
            latex.DrawLatex(0.15, 0.80, "Rate Monitoring")
            canvas.Update()
            maxLine.Draw("same")
            canvas.Update()
            canvas.Modified()
            canvas.Write()
            
            canvas.Print("%s/CertificationSummary_run%s.png" % (self.saveDirectory, runNumber), "png")

            fractionBadLumis = 100.*float(totalErrs)/float(totalLumis)
            fractionBadRun = 100.*summaryHist.Integral()/float((totalLumis+2) * maxNumBadPaths) 
            file.write("\n")
            file.write("BAD LS SUMMARY: \n")
            file.write("\n---- Total bad LS: %s  ( bad LS: >= 1 trigger(s) deviating more than 3 sigma from prediction )\n" % (totalErrs))
            file.write("---- Total LS: %s\n" % (totalLumis))
            file.write("---- Fraction bad LS: %s\n" % (fractionBadLumis))

            fractionBadpaths = (100.*(float(testVariable)/(float(totalLumis*maxNumBadPaths))))
            totalPossPaths = float(totalLumis*maxNumBadPaths)
            totalBadPaths = float(testVariable)
            file.write("\n")
            file.write("BAD PATH SUMMARY: \n")
            file.write("\n")
            file.write("---- Total Bad Paths: %.1f\n" % (totalBadPaths))
            file.write("---- Total Possible Paths: %.1f\n" % (totalPossPaths))
            file.write("---- Fraction that are Bad Paths: %.1f\n" % (float(fractionBadpaths)))
            file.write("\n")
            file.write("----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n")
  
        file.close()        
        rootFile.Close()

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
