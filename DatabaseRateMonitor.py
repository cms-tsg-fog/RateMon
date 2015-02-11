#!/usr/bin/env python

from ReadConfig import RateMonConfig
import sys
import os
import cPickle as pickle
import getopt
import time
from StreamMonitor import *
from colors import *
try:
    from TablePrint import *
except ImportError:
    sys.stderr.write("Exception of environment variables. try:\nsource set.sh\n")
    sys.exit(2)
    
from AddTableInfo_db import MoreTableInfo
from math import *
from DatabaseParser import *
from TablePrint import *

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMRunInfoPage = "https://cmswbm/cmsdb/runSummary/RunSummary_1.html"
RefRunNameTemplate = "RefRuns/%s/Run_%s.pk"

# define a function that clears the terminal screen
def clear():
    print("\x1B[2J")


def usage():
    print sys.argv[0]+" [Options]"
    print "This script gets the current HLT trigger rates and compares them to a reference run or a fit to multiple runs"
    print "Options: "
    print "--AllowedPercDiff=<diff>             Warn only if difference in trigger rate is greater than <diff>%"
    print "--AllowedSigmaDiff=<diff>            Warn only if difference in trigger rate is greater than <diff> standard deviations"
    print "--CompareRun=<Run #>                 Compare run <Run #> to the reference run (Default = Current Run)"
    print "--FindL1Zeros                        Look for physics paths with 0 L1 rate"    
    print "--FirstLS=<ls>                       Specify the first lumisection to consider. This will set LSSlidingWindow to -1"
    print "--NumberLS=<#>                       Specify the last lumisection to consider. Make sure LastLS > LSSlidingWindow"
    print "                                        or set LSSlidingWindow = -1"  
    print "--IgnoreLowRate=<rate>               Ignore triggers with an actual and expected rate below <rate>"
    print "--AllTriggers                   Prints the paths that are not compared by this script and their rate in the CompareRun"
    print "--PrintLumi                          Prints Instantaneous, Delivered, and Live lumi by LS for the run"
    print "--RefRun=<Run #>                     Specifies <Run #> as the reference run to use (Default in defaults.cfg)"
    print "--ShowPSTriggers                     Show prescaled triggers in rate comparison"
    print "--sortBy=<field>                     Sort the triggers by field.  Valid fields are: name, rate, rateDiff"
    print "--force                              Override the check for collisions run"
    print "--write                              Writes rates to .csv file"
    print "--ShowAllBadRates                    Show a list of all triggers (not just those in the monitor list) with bad rates"
    print "--help                               Print this help"

def pickYear():
    global thisyear
    thisyear="2012"
    ##print "Year set to ",thisyear

def main():
    pickYear()
    try:
        opt, args = getopt.getopt(sys.argv[1:],"",["AllowedPercDiff=","AllowedSigmaDiff=","CompareRun=","FindL1Zeros",\
                                                   "FirstLS=","NumberLS=","IgnoreLowRate=","AllTriggers",\
                                                   "PrintLumi","RefRun=","ShowPSTriggers","force","sortBy=","write","ShowAllBadRates","help"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    Config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))
    for o,a in opt:
        if o=="--ConfigFile":
            Config.CFGfile=a
    Config.ReadCFG()


    if "NoV" in Config.FitFileName:
        Config.NoVersion=True
    #print "NoVersion=",Config.NoVersion

    ShowSigmaAndPercDiff = Config.DefShowSigmaAndPercDiff
    WarnOnSigmaDiff = Config.DefWarnOnSigmaDiff
    AllowedRatePercDiff   = Config.DefAllowRatePercDiff
    AllowedRateSigmaDiff  = Config.DefAllowRateSigmaDiff    
    CompareRunNum     = ""
    FindL1Zeros       = False
    FirstLS           = 9999
    NumLS             = -10
    IgnoreThreshold   = Config.DefAllowIgnoreThresh
    AllTriggers  = Config.AllTriggers
    PrintLumi         = False
    RefRunNum         = int(Config.ReferenceRun)
    ShowPSTriggers    = True
    Force             = False
    writeb            = False
    SortBy            = "rate"
    ShifterMode       = int(Config.ShifterMode) # get this from the config, but can be overridden by other options
    ShowAllBadRates   = Config.ShowAllBadRates
    MaxBadRates       = Config.DefaultMaxBadRatesToShow
    
    if Config.LSWindow > 0:
        NumLS = -1*Config.LSWindow

    for o,a in opt: # get options passed on the command line
        if o=="--AllowedPercDiff":
            AllowedRatePercDiff = float(a)
        elif o=="--AllowedSigmaDiff":
            AllowedRateSigmaDiff = float(a)
        elif o=="--CompareRun":
            CompareRunNum=int(a)
            ShifterMode = False
        elif o=="--FindL1Zeros":
            FindL1Zeros = True
        elif o=="--FirstLS":
            FirstLS = int(a)
            ShifterMode = False
        elif o=="--NumberLS":
            NumLS = int(a)
        elif o=="--IgnoreLowRate":
            IgnoreThreshold = float(a)
        elif o=="--AllTriggers":
            AllTriggers=True
            ShifterMode = False
        elif o=="--PrintLumi":
            PrintLumi = True
        elif o=="--RefRun":
            RefRunNum=int(a)
        elif o=="--ShowPSTriggers":
            ShowPSTriggers=True
        elif o=="--sortBy":
            SortBy = a
        elif o=="--force":
            Force = True
        elif o=="--write":
            writeb = True
        elif o=="--ShowAllBadRates":
            ShowAllBadRates=True
        elif o=="--help":
            usage()
            sys.exit(0)
        else:
            print "Invalid Option "+a
            sys.exit(1)

        
    RefLumisExists = False
    """
    RefRunFile=RefRunNameTemplate % str(RefRunNum)
    if RefRunNum > 0:
        RefRates = {}
        for Iterator in range(1,100):
            if RefLumisExists:  ## Quits at the end of a run
                if max(RefLumis[0]) <= (Iterator+1)*10:
                    break

                    RefRunFile = RefRunNameTemplate % str( RefRunNum*100 + Iterator )  # place to save the reference run info
            print "RefRunFile=",RefRunFile
            if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
                print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
                print RefRunFile[:RefRunFile.rfind('/')]
                sys.exit(0)

            if not os.path.exists(RefRunFile):  # if the reference run is not saved, get it from wbm
                print "Reference Run File for run "+str(RefRunNum)+" iterator "+str(Iterator)+" does not exist"
                print "Creating ..."
                try:
                    RefParser = GetRun(RefRunNum, RefRunFile, True, Iterator*10, (Iterator+1)*10)
                    print "parsing"
                except:
                    print "GetRun failed from LS "+str(Iterator*10)+" to "+str((Iterator+1)*10)
                    continue
                    
            else: # otherwise load it from the file
                RefParser = pickle.load( open( RefRunFile ) )
                print "loading"
            if not RefLumisExists:
                RefLumis = RefParser.LumiInfo
                RefLumisExists = True

            try:
                RefRates[Iterator] = RefParser.TriggerRates # get the trigger rates from the reference run
                LastSuccessfulIterator = Iterator
            except:
                print "Failed to get rates from LS "+str(Iterator*10)+" to "+str((Iterator+1)*10)
    
    """
    RefRunFile = RefRunNameTemplate % (thisyear,RefRunNum)
    RefParser = DatabaseParser()
    ##print "Reference Run: "+str(RefRunNum)
    if RefRunNum > 0:
        print "Getting RefRunFile",RefRunFile
        if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
            print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
            print RefRunFile[:RefRunFile.rfind('/')]
            sys.exit(0)
            s
            return
        if not os.path.exists(RefRunFile):
            print "RefRunFile does not exist"
            # create the reference run file
            try:
                RefParser.RunNumber = RefRunNum
                RefParser.ParseRunSetup()
                print "RefParser is setup"
                #RefParser.GetAllTriggerRatesByLS()
                #RefParser.Save( RefRunFile )
            except e:
                print "PROBLEM GETTING REFERNCE RUN"
                raise  
        else:
            RefParser = pickle.load(open(RefRunFile))
            
    # OK, Got the Reference Run
    # Now get the most recent run

    SaveRun = False
    if CompareRunNum=="":  # if no run # specified on the CL, get the most recent run
        CompareRunNum,isCol,isGood = GetLatestRunNumber()
            
        if not isGood:
            print "NO TRIGGER KEY FOUND for run ",CompareRunNum
            ##sys.exit(0)

        if not isCol:
            print "Most Recent run, "+str(CompareRunNum)+", is NOT collisions"
            print "Monitoring only stream A and Express"
            #if not Force:
            #    sys.exit(0) # maybe we should walk back and try to find a collisions run, but for now just exit

        else:
            print "Most Recent run is "+str(CompareRunNum)
    else:
        CompareRunNum,isCol,isGood = GetLatestRunNumber(CompareRunNum)
        if not isGood:
            print "NO TRIGGER KEY FOUND for run ", CompareRunNum
            ##sys.exit(0)

    HeadParser = DatabaseParser()
    HeadParser.RunNumber = CompareRunNum
        
    try:
        HeadParser.ParseRunSetup()
        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,isCol)
        LastGoodLS=HeadParser.GetLastLS(isCol)+1
        tempLastGoodLS=LastGoodLS
        CurrRun=CompareRunNum

    except:
        HeadLumiRange=[]
        LastGoodLS=-1
        tempLastGoodLS=LastGoodLS-1
        CurrRun=CompareRunNum
        isGood=0
        
    if len(HeadLumiRange) is 0:
        print "No lumisections that are taking physics data 0"
        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,False)
        if len(HeadLumiRange)>0:
            isGood=1
            isCol=0
        ##sys.exit(0)

    ## This reduces the sensitivity for a rate measurement to cause a warning during the beginning of a run
    if len(HeadLumiRange) > 0 and len(HeadLumiRange) < 10:
        AllowedRateSigmaDiff = AllowedRateSigmaDiff*10 / len(HeadLumiRange)
    
    if PrintLumi:
        for LS in HeadParser.LumiInfo[0]:
            try:
                if (LS < FirstLS or LS > LastLS) and not FirstLS==999999:
                    continue
                print str(LS)+'  '+str(round(HeadParser.LumiInfo[2][LS],1))+'  '+str(round((HeadParser.LumiInfo[3][LS] - HeadParser.LumiInfo[3][LS-1])*1000/23.3,0))+'  '+str(round((HeadParser.LumiInfo[4][LS] - HeadParser.LumiInfo[4][LS-1])*1000/23.3,0))
            except:
                print "Lumisection "+str(LS-1)+" was not parsed from the LumiSections page"
                                                                                                                                 
                sys.exit(0)

    if RefRunNum == 0:
        RefRates = 0
        RefLumis = 0
        LastSuccessfulIterator = 0

### Now actually compare the rates, make tables and look at L1. Loops for ShifterMode
    ###isGood=1##if there is a trigger key
    try:
        while True:
            if isGood:
                tempLastGoodLS=LastGoodLS
                LastGoodLS=HeadParser.GetLastLS(isCol)
                ##print "Last Good=",LastGoodLS, tempLastGoodLS
                if LastGoodLS==tempLastGoodLS:
                    write(bcolors.OKBLUE)
                    print "Trying to get new Run"
                    write(bcolors.ENDC+"\n")
                else:
                    RefMoreLumiArray = HeadParser.GetMoreLumiInfo()
                    isBeams=True
                    for lumisection in HeadLumiRange:
                        try: 
                            if not (RefMoreLumiArray["b1pres"][lumisection] and RefMoreLumiArray["b2pres"][lumisection] and RefMoreLumiArray["b1stab"][lumisection] and RefMoreLumiArray["b2stab"][lumisection]):
                                isBeams=False
                        except:
                            isBeams=False

                    if not (isCol and isBeams):
                        MoreTableInfo(HeadParser,HeadLumiRange,Config,False)
                    else:
                        if (len(HeadLumiRange)>0):
                            if not isSequential(HeadLumiRange):
                                print "Some lumisections have been skipped. Averaging over most recent sequential lumisections..."
                                sequential_chunk = getSequential(HeadLumiRange)
                                HeadLumiRange = sequential_chunk                                
                            RunComparison(HeadParser,RefParser,HeadLumiRange,ShowPSTriggers,AllowedRatePercDiff,AllowedRateSigmaDiff,IgnoreThreshold,Config,AllTriggers,SortBy,WarnOnSigmaDiff,ShowSigmaAndPercDiff,writeb,ShowAllBadRates,MaxBadRates)
                            if FindL1Zeros:
                                CheckL1Zeros(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedRatePercDiff,AllowedRateSigmaDiff,IgnoreThreshold,Config)
                        else:
                            print "No lumisections that are taking physics data 1"

            if not ShifterMode:
                print "Expert Mode. Quitting."
                sys.exit(0)

            print "Sleeping for 1 minute before repeating  "

            for iSleep in range(20):
                write(".")
                sys.stdout.flush()
                time.sleep(3)
            write("  Updating\n")
            sys.stdout.flush()
            
            ##print "\nminLS=",min(HeadLumiRange),"Last LS=",HeadParser.GetLastLS(isCol),"run=",HeadParser.RunNumber
            ###Get a new run if DAQ stops
            ##print "\nLastGoodLS=",LastGoodLS

            ##### NEED PLACEHOLDER TO COMPARE CURRENT RUN TO LATEST RUN #####
            
            NewRun,isCol,isGood = GetLatestRunNumber(9999999)  ## update to the latest run and lumi range
            
            try:
                maxLumi=max(HeadLumiRange)
            except:
                maxLumi=0
            
            ##### THESE ARE CONDITIONS TO GET NEW RUN #####
            if maxLumi>(LastGoodLS+1) or not isGood or NewRun!=CurrRun:
                print "Trying to get new Run"
                try:
                    HeadParser = DatabaseParser()
                    HeadParser.RunNumber = NewRun
                    HeadParser.ParseRunSetup()
                    CurrRun,isCol,isGood=GetLatestRunNumber(9999999)
                    FirstLS=9999
                    HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,isCol)    
                    if len(HeadLumiRange) is 0:
                        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,False)
                        print "No lumisections that are taking physics data 2"
                        if len(HeadLumiRange)>0:
                            isGood=1
                            isCol=0
                            
                    #tempLastGoodLS=LastGoodLS
                    #LastGoodLS=HeadParser.GetLastLS(isCol)
                    ##print CurrRun, isCol, isGood
                except:
                    isGood=0
                    isCol=0
                    print "failed"

            else:
                try:
                    HeadParser.ParseRunSetup()
                    HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,isCol)
                    if len(HeadLumiRange) is 0:
                        HeadLumiRange = HeadParser.GetLSRange(FirstLS,NumLS,False)
                        print "No lumisections that are taking physics data"
                        if len(HeadLumiRange)>0:
                            isGood=1
                            isCol=0
                    #LastGoodLS=HeadParser.GetLastLS(isCol)
                except:
                    isGood=0
                    isCol=0
                    clear()
                    print "NO TRIGGER KEY FOUND YET for run", NewRun ,"repeating search"
                

    except KeyboardInterrupt:
        print "Quitting. Peace Out."

            
def RunComparison(HeadParser,RefParser,HeadLumiRange,ShowPSTriggers,AllowedRatePercDiff,AllowedRateSigmaDiff,IgnoreThreshold,Config,AllTriggers,SortBy,WarnOnSigmaDiff,ShowSigmaAndPercDiff,writeb,ShowAllBadRates,MaxBadRates):
    Data   = []
    Warn   = []
    IgnoredRates=[]
    
    [HeadAvInstLumi,HeadAvLiveLumi,HeadAvDeliveredLumi,HeadAvDeadTime,HeadPSCols] = HeadParser.GetAvLumiInfo(HeadLumiRange)
    ##[HeadUnprescaledRates, HeadTotalPrescales, HeadL1Prescales, HeadTriggerRates] = HeadParser.UpdateRun(HeadLumiRange)
    HeadUnprescaledRates = HeadParser.UpdateRun(HeadLumiRange)
    if Config.DoL1:
        L1RatesALL=HeadParser.GetL1RatesALL(HeadLumiRange)
        for L1seed in L1RatesALL.iterkeys():
            HeadUnprescaledRates[L1seed]=L1RatesALL[L1seed]
        
    [PSColumnByLS,InstLumiByLS,DeliveredLumiByLS,LiveLumiByLS,DeadTimeByLS,PhysicsByLS,ActiveByLS] = HeadParser.LumiInfo
    deadtimebeamactive=HeadParser.GetDeadTimeBeamActive(HeadLumiRange)
    try:
        pkl_file = open(Config.FitFileName, 'rb')
        FitInput = pickle.load(pkl_file)
        pkl_file.close()
        ##print "fit file name=",Config.FitFileName
        
    except:
        print "No fit file specified"
        sys.exit(2)

    ###fitfile by L1seedchange
    if Config.L1SeedChangeFit:
        try:
            PSfitfile=Config.FitFileName.replace("HLT_NoV","HLT_NoV_ByPS")
            #print "Opening", PSfitfile
            pkl_filePS = open(PSfitfile, 'rb')
            FitInputPS = pickle.load(pkl_filePS)
            pkl_filePS.close()
            #print "fit file name=",Config.FitFileName
        
        except:
            print "No fit file by L1seed change specified.  Have you run DatabaseRatePredictor with DoL1 in defaults.cfg set to true?"
            sys.exit(2)
    else:
        FitInputPS={} ##define empty dict when not in use
    try:    
        refrunfile="RefRuns/%s/Rates_HLT_10LS_JPAP.pkl" % (thisyear)
        pkl_file = open(refrunfile, 'rb')
        RefRatesInput = pickle.load(pkl_file)
        pkl_file.close()
    except:
        RefRatesInput={}
        #print "Didn't open ref file"


    trig_list=Config.MonitorList
    
    if Config.NoVersion:
        trig_list=[]
        
        for trigger in Config.MonitorList:
            trig_list.append(StripVersion(trigger))
        
        L1HLTseeds = HeadParser.GetL1HLTseeds()
        if Config.DoL1:
            for HLTkey in trig_list:
                if "L1" in HLTkey:
                    continue
                else:
                    try:
                        for L1seed in L1HLTseeds[HLTkey]:
                            if L1seed not in trig_list:
                                trig_list.append(L1seed)
                    except:
                        pass

        for trigger in FitInput.iterkeys():
            FitInput[StripVersion(trigger)] = FitInput.pop(trigger)
        for trigger in HeadUnprescaledRates:
            HeadUnprescaledRates[StripVersion(trigger)] = HeadUnprescaledRates.pop(trigger)

    RefAvInstLumi = 0
    found_ref_rates = True
    for HeadName in HeadUnprescaledRates:
        if HeadName not in trig_list and not AllTriggers and not ShowAllBadRates:
            continue
        if HeadName not in FitInput.keys() and not AllTriggers and not ShowAllBadRates:
            continue                   

        masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_Zero","HLT_BeamHalo"]
        masked_trig = False
        for mask in masked_triggers:
            if str(mask) in HeadName:
                masked_trig = True
        if masked_trig:
            continue

        skipTrig=False
        TriggerRate = round(HeadUnprescaledRates[HeadName][2],2)
                
        if RefParser.RunNumber == 0:  ## Use rate prediction functions
            PSCorrectedExpectedRate = Config.GetExpectedRate(HeadName,FitInput,FitInputPS,HeadAvLiveLumi,HeadAvDeliveredLumi,deadtimebeamactive,Config.L1SeedChangeFit,HeadLumiRange,PSColumnByLS)
            VC = PSCorrectedExpectedRate[2]
            try:
                sigma = PSCorrectedExpectedRate[1]*sqrt(PSCorrectedExpectedRate[0])/(sqrt(len(HeadLumiRange))* HeadUnprescaledRates[HeadName][1])
                ExpectedRate = round((PSCorrectedExpectedRate[0] / HeadUnprescaledRates[HeadName][1]),2)                
            except:
                sigma = 0.0
                ExpectedRate = 0.0 ##This means we don't have a prediction for this trigger-- gets overwritten to "--" later
                PerDiff = 0.0
                SigmaDiff = 0.0
                if HeadUnprescaledRates[HeadName][1] != 0:
                    VC="No prediction"
                else:
                    VC="Path prescaled to 0"

            if ExpectedRate > 0:
                PerDiff = int(round( (TriggerRate-ExpectedRate)/ExpectedRate,2 )*100)
            else:
                PerDiff = 0.0

            if sigma > 0: 
                SigmaDiff = round( (TriggerRate - ExpectedRate)/sigma, 2)
            else:
                SigmaDiff = 0.0 #Zero sigma means that when there were no rates for this trigger when the fit was made

            if TriggerRate < IgnoreThreshold and (ExpectedRate < IgnoreThreshold and ExpectedRate!=0):
                continue

            
            Data.append([HeadName, TriggerRate, ExpectedRate, PerDiff, SigmaDiff, round(HeadUnprescaledRates[HeadName][1],0),VC])

        else:  ## Use a reference run
            RefInstLumi = 0
            RefIterator = 0
            RefStartIndex = ClosestIndex(HeadAvInstLumi,RefParser.GetAvLumiPerRange())
            RefLen = -10
            RefLSRange = RefParser.GetLSRange(RefStartIndex,RefLen)

            RefUnprescaledRates = RefParser.UpdateRun(RefLSRange)

            [RefAvInstLumi,RefAvLiveLumi,RefAvDeliveredLumi,RefAvDeadTime,RefPSCols] = RefParser.GetAvLumiInfo(RefLSRange)
            if Config.DoL1 and RefUnprescaledRates != {}:
                RefL1RatesALL = RefParser.GetL1RatesALL(RefLSRange)
                for L1seed in RefL1RatesALL.iterkeys():
                    RefUnprescaledRates[L1seed]=RefL1RatesALL[L1seed]

            if RefUnprescaledRates == {}:
                found_ref_rates = False
                for path in HeadUnprescaledRates.iterkeys():
                    RefUnprescaledRates[path] = [0.0,0.0,0.0,0.0]
                        
            RefRate = -1
            for k,v in RefUnprescaledRates.iteritems():
                if HeadName == StripVersion(k):
                    RefRate = RefUnprescaledRates[k][2]
                    
            try:
                ScaledRefRate = round( (RefRate*HeadAvLiveLumi/RefAvLiveLumi*(1-deadtimebeamactive)), 2  )
                
            except ZeroDivisionError:
                ScaledRefRate=0
                
            SigmaDiff = 0
            if ScaledRefRate == 0:
                PerDiff = -999
            else:
                PerDiff = int( round( (TriggerRate - ScaledRefRate)/ScaledRefRate , 2)*100)
                
            if TriggerRate < IgnoreThreshold and ScaledRefRate < IgnoreThreshold:
                continue

            VC = ""
            Data.append([HeadName,TriggerRate,ScaledRefRate,PerDiff,SigmaDiff,round((HeadUnprescaledRates[HeadName][1]),0),VC])

    if not found_ref_rates:
        print '\n*****************************************************************************************************************************************************'
        print 'COULD NOT PARSE REFERENCE RUN! MOST LIKELY THIS IS BECAUSE THE REFERENCE RUN DOES NOT PASS THE QUALITY CUTS (DEADTIME < 100%, PHYSICS DECALRED, ETC.)'
        print 'Setting all reference rates to zero...'
        print '*****************************************************************************************************************************************************'        
        
    SortedData = []
    if SortBy == "":
        SortedData=sorted(Data, key=lambda entry: abs(entry[3]),reverse=True) 
    elif SortBy == "name":
        SortedData=sorted(Data, key=lambda entry: entry[0])
    elif SortBy == "rate":
        SortedData=sorted(Data, key=lambda entry: entry[1],reverse=True)
    elif SortBy == "ratePercDiff":
        SortedData=sorted(Data, key=lambda entry: abs(entry[3]),reverse=True)
    elif SortBy == "rateSigmaDiff":
        SortedData=sorted(Data, key=lambda entry: abs(entry[4]),reverse=True)        
    else:
        print "Invalid sorting option %s\n"%SortBy
        SortedData = Data

    #check for triggers above the warning threshold
    Warn=[]
    core_data=[]
    core_l1_seeds=[]
    nBadRates = 0
    #Loop for HLT triggers
    for entry in SortedData:
        bad_seeds_string = ""
        if not entry[0].startswith('HLT'):
            continue
        bad_rate = (abs(entry[4]) > AllowedRateSigmaDiff and WarnOnSigmaDiff) or (abs(entry[3]) > AllowedRatePercDiff and not WarnOnSigmaDiff) or (abs(entry[3]) > AllowedRatePercDiff and RefParser.RunNumber > 0)
        if entry[0] in trig_list or AllTriggers or (bad_rate and ShowAllBadRates and nBadRates < MaxBadRates):
            core_data.append(entry)
            if bad_rate or (bad_rate and ShowAllBadRates and nBadRates < MaxBadRates):
                if Config.DoL1:
                    for seed in L1HLTseeds[entry[0]]:
                        if not seed in core_l1_seeds:
                            core_l1_seeds.append(seed)                        
                        seed_rate = [line[3] for line in SortedData if line[0] == seed]
                        if seed_rate:
                            bad_seed_rate = (abs(seed_rate[0]) > AllowedRatePercDiff)
                            if bad_seed_rate:
                                if bad_seeds_string != "":
                                    bad_seeds_string += ", "
                                bad_seeds_string += seed 
                    entry[6] = bad_seeds_string
                Warn.append(True)
                nBadRates += 1
            else:
                Warn.append(False)

    ##Loop for L1 seeds of HLT triggers with warnings
    if Config.DoL1:
        for entry in SortedData:
            if not entry[0] in core_l1_seeds:
                continue
            core_data.append(entry)
            bad_seed_rate = (abs(entry[3]) > AllowedRatePercDiff)
            if bad_seed_rate:
                Warn.append(True) #Currently, number of bad rates to show refers to bad HLT triggers (no limit on the number of bad L1 seeds to show)
            else:
                Warn.append(False)

    for index,entry in enumerate(core_data): 
        if entry[6] == "No prediction (fit missing)": #Dont show 0s if we don't actually have a prediction; it's confusing
            core_data[index] = [entry[0],entry[1],"--","--","--",entry[5],entry[6]]
        if entry[0].startswith('L1'): #Don't show sigma value for L1 since we don't trust them
            core_data[index] = [entry[0],entry[1],entry[2],entry[3],"--",entry[5],entry[6]]

    try:
        comment_width = max([30,max([len(col[6]) for col in core_data])+1])
    except:
        comment_width = 30
        
    if RefParser.RunNumber > 0:
        Header = ["Trigger Name", "Actual", "Ref Run", "% Diff", "Cur PS", "Comments"]
        table_data = [[col[0], col[1], col[2], col[3], col[5], col[6]] for col in core_data]
        PrettyPrintTable(Header,table_data,[80,10,10,10,10,comment_width],Warn)        
    elif ShowSigmaAndPercDiff == 1:
        Header = ["Trigger Name", "Actual", "Expected","% Diff","Deviation", "Cur PS", "Comments"]
        table_data=core_data
        PrettyPrintTable(Header,table_data,[80,10,10,10,11,10,comment_width],Warn)
        print 'Deviation is the difference between the actual and expected rates, in units of the expected standard deviation.'
    elif WarnOnSigmaDiff == 1:
        Header = ["Trigger Name", "Actual", "Expected","Deviation", "Cur PS", "Comments"]
        table_data = [[col[0], col[1], col[2], col[4], col[5], col[6]] for col in core_data]
        PrettyPrintTable(Header,table_data,[80,10,10,10,11,10,comment_width],Warn)
        print 'Deviation is the difference between the actual and expected rates, in units of the expected standard deviation.'
    else:
        Header = ["Trigger Name", "Actual", "Expected", "% Diff", "Cur PS", "Comments"]
        table_data = [[col[0], col[1], col[2], col[3], col[5], col[6]] for col in core_data]
        PrettyPrintTable(Header,table_data,[80,10,10,10,10,comment_width],Warn)

    if writeb:
        prettyCSVwriter("rateMon_newmenu.csv",[80,10,10,10,10,20,comment_width],Header,core_data,Warn)

    MoreTableInfo(HeadParser,HeadLumiRange,Config,True)
    if RefParser.RunNumber > 0 and RefAvInstLumi > 0:
        print "The average instantaneous lumi for the reference run is: %s e30\n" % (round(RefAvInstLumi,1))

    if nBadRates == MaxBadRates:
        write(bcolors.WARNING)
        print "The number of paths with rates outside limits exceeds the maximum number to display; only the first %i with the highest rate are shown above." % (MaxBadRates)
        write(bcolors.ENDC+"\n")                        

    for warning in Warn:
        if warning==True:
            write(bcolors.WARNING)
            print "If any trigger remains red for 5 minutes, Please consult the shift crew and if needed contact relevant experts"
            print "More instructions at https://twiki.cern.ch/twiki/bin/view/CMS/TriggerShiftHLTGuide"
            write(bcolors.ENDC+"\n")
            break
        
 
def CheckL1Zeros(HeadParser,RefRunNum,RefRates,RefLumis,LastSuccessfulIterator,ShowPSTriggers,AllowedPercRateDiff,IgnoreThreshold,Config):
    L1Zeros=[]
    IgnoreBits = ["L1_PreCollisions","L1_InterBunch_Bsc","L1_BeamHalo","L1_BeamGas_Hf"]
    for key in HeadParser.TriggerRates:
    ## Skip events in the skip list
        skipTrig=False
    ##for trig in Config.ExcludeList:
    ##if not trigN.find(trig) == -1:
    ##skipTrig=True
    ##break
        if skipTrig:
            continue
        ## if no events pass the L1, add it to the L1Zeros list if not already there
        if HeadParser.TriggerRates[key][1]==0 and not HeadParser.TriggerRates[key][4] in L1Zeros:
            if HeadParser.TriggerRates[key][4].find('L1_BeamHalo')==-1 and HeadParser.TriggerRates[key][4].find('L1_PreCollisions')==-1 and HeadParser.TriggerRates[key][4].find('L1_InterBunch_Bsc')==-1:
                
                L1Zeros.append(HeadParser.TriggerRates[key][4])
                print "L1Zeros=", L1Zeros
        
    if len(L1Zeros) == 0:
       #print "It looks like no masked L1 bits seed trigger paths"
        pass
    else:
        print "The following seeds are used to seed HLT bits but accept 0 events:"
    #print "The average lumi of this run is: "+str(round(HeadParser.LumiInfo[6],1))+"e30"
        for Seed in L1Zeros:
            print Seed

def isSequential(t):
    try:
        if len(t)<2:
            return True
    except:
        return True        
    for i,e in enumerate(t[1:]):
        if not abs(e-t[i])==1:
            return False
    return True

def getSequential(range):
    for i,j in zip(range[-2::-1],range[::-1]):
        if j-i != 1:
            range = range[range.index(j):]
            break
    return range


if __name__=='__main__':
    global thisyear
    main()
