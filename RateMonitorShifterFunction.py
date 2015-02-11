#!/usr/bin/env python

from Page1Parser import Page1Parser
from GetRun import GetRun
import sys
import os
import cPickle as pickle
import getopt
import time
from ReadConfig import RateMonConfig
from colors import *

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMRunInfoPage = "https://cmswbm/cmsdb/runSummary/RunSummary_1.html"

RefRunNameTemplate = "RefRuns/Run_%s.pk"

def RateMon(InputRun,BeginningLS):

    Config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))

    Config.ReadCFG()
    
    IgnoreVersion     = False
    ZerosOnly         = False
    ListIgnoredPaths  = False
    AllowedRateDiff   = Config.DefAllowRateDiff
    IgnoreThreshold   = Config.DefAllowIgnoreThresh
    CompareRunNum     = InputRun
    FindL1Zeros       = Config.FindL1Zeros
    FirstLS           = BeginningLS
    EndEndLS          = 111111
    LastLS            = FirstLS+10
    RefRunNum      = int(Config.ReferenceRun)
    
    if Config.LSWindow > 0 and FirstLS == 999999:
        FirstLS = -1*Config.LSWindow

    FirstTime = 0
    try: 
        if FirstTime == 0:
            ### Get the most recent run
            SaveRun=False
            if CompareRunNum=="":  # if no run # specified on the CL, get the most recent run
                RunListParser = Page1Parser()

                RunListParser._Parse(WBMRunInfoPage)  # this is the page that lists all the runs in the last 24 hours with at least 1 trigger
                RunListPage = RunListParser.ParsePage1()
                if RunListPage == '':  # this will be '' if the mode of the most recent run is not l1_hlt_collisions/v*
                    print "Most Recent run is NOT collisions"
                    sys.exit(0) # maybe we should walk back and try to find a collisions run, but for now just exit
                CompareRunNum = RunListParser.RunNumber
                print "Most Recent run is "+CompareRunNum
            else:
                SaveRun=False
            HeadRunFile = RefRunNameTemplate % CompareRunNum
            RefRunFile  = RefRunNameTemplate % str(RefRunNum)

            if not os.path.exists(RefRunFile[:RefRunFile.rfind('/')]):  # folder for ref run file must exist
                print "Reference run folder does not exist, please create" # should probably create programmatically, but for now force user to create
                print RefRunFile[:RefRunFile.rfind('/')]
                sys.exit(0)

            if not os.path.exists(RefRunFile) and RefRunNum != 0:  # if the reference run is not saved, get it from wbm
                    print "Updated reference run file"
                    RefParser = GetRun(RefRunNum, RefRunFile, True)
            else: # otherwise load it from the file
                if RefRunNum != 0:
                    RefParser = pickle.load( open( RefRunFile ) )


            if os.path.exists(HeadRunFile):  # check if a run file for the run we want to compare already exists, it probably won't but just in case we don't have to interrogate WBM
                HeadParser = pickle.load( open( HeadRunFile ) )
            else:
                HeadParser = GetRun(CompareRunNum,HeadRunFile,SaveRun,FirstLS,EndEndLS)

            if HeadParser.FirstLS==-1:
                print bcolors.OKBLUE+">> Stable Beams NOT yet declared, be patient..."+bcolors.ENDC
                sys.exit(0)

            HeadRates = HeadParser.TriggerRates

            write=sys.stdout.write

            write ('\nCalculation using FirstLS = %s to LastLS = %s\n' % (HeadParser.FirstLS, HeadParser.LastLS))

            write("The average lumi of these lumi sections is: ")
            if HeadParser.AvLiveLumi==0:
                write(bcolors.FAIL)
            elif HeadParser.AvLiveLumi<100:
                write(bcolors.WARNING)
            else:
                write(bcolors.OKBLUE)
            write(str(round(HeadParser.AvLiveLumi,1))+"e30")
            write(bcolors.ENDC+"\n\n")

            #print "Printing all PS columns"
            #print HeadParser.PrescaleColumn
            print "Using prescale column %s" % HeadParser.PrescaleColumn[-2]
            
            #print HeadParser.PrescaleColumn
            if HeadParser.PrescaleColumn[-2]==0:
                write(bcolors.FAIL)
                write("WARNING:  You are using prescale column 0 in Lumi Section %s!  This is the emergency column and should only be used if there is no other way to take data\n" % (HeadParser.LastLS)  )
                write("If this is a mistake FIX IT NOW \nif not, the TFM and HLT DOC must be informed\n\n")

                write("\n\n")
                write(bcolors.ENDC)

            nameBufLen=60
            RateBuffLen=10
            write('*'*(nameBufLen+3*RateBuffLen+2)+'\n')
            write('* Trigger Name'+' '*(nameBufLen-17)+'* Actual   * Expected * % Diff    *\n')
            write('*'*(nameBufLen+3*RateBuffLen+2)+'\n')    

            IgnoredRates=[]
            LargeRateDifference=False
            for headTrigN,headTrigRate,headTrigPS,headL1 in HeadRates:
                headTrigNNoVersion = headTrigN[:headTrigN.rfind('_')]
                if not Config.AnalyzeTrigger(headTrigNNoVersion): ## SKIP triggers in the skip list
                    continue
                ExpectedRate = round(Config.GetExpectedRate(headTrigNNoVersion,HeadParser.AvLiveLumi),1)
                PerDiff=0
                if ExpectedRate>0:
                    PerDiff = int(round( (headTrigRate-ExpectedRate)/ExpectedRate,2 )*100)
                ##Write Line ##
                if headTrigRate==0:
                    write(bcolors.FAIL)
                elif abs(PerDiff) > AllowedRateDiff:
                    write(bcolors.FAIL)
                else:
                    write(bcolors.OKGREEN)
                write('* '+headTrigN+' '*(nameBufLen-len(headTrigN)-5)+'*')
                write(' '*(RateBuffLen-len(str(headTrigRate))-1)+str(headTrigRate)+' *')
                write(' '*(RateBuffLen-len(str(ExpectedRate))-1)+str(ExpectedRate)+' *')
                if ExpectedRate>0:
                    if abs(PerDiff) > AllowedRateDiff/2:
                        write(' '+' '*(RateBuffLen-len(str(PerDiff))-2)+str(PerDiff)+'%')
                    else:
                        write('  good    ')                
                else:
                    write('          ')
                write(' *')
                if headTrigRate==0:
                    write(" << TRIGGER RATE IS ZERO! check shift instructions")
                elif abs(PerDiff) > AllowedRateDiff:
                    write(" << LARGE RATE DIFFERENCE: check shift instructions")
                    LargeRateDifference=True # this means we automatically check the reference run
                write(bcolors.ENDC+'\n')

            CallDOC=False
            if ( LargeRateDifference or Config.CompareReference ) and RefRunNum != 0:
                if LargeRateDifference:
                    write(bcolors.WARNING)
                    print """
                    \n\n
                    ********************************************************************
                    A trigger in this run has a substantial difference from expectations.\n
                    Comparing the current run to a reference run
                    ********************************************************************
                    """
                    write(bcolors.ENDC)
                else:
                    print "\n\n Comparing to reference Run:\n\n"

                write('*'*(nameBufLen+3*RateBuffLen+2)+'\n')
                write('* Trigger Name'+' '*(nameBufLen-17)+'* Actual   * Expected * % Diff    *\n')
                write('*'*(nameBufLen+3*RateBuffLen+2)+'\n')    

                NotFound=[]
                for headTrigN,headTrigRate,headTrigPS,headL1 in HeadRates:
                    headTrigNNoVersion = headTrigN[:headTrigN.rfind('_')]
                    if not Config.AnalyzeTrigger(headTrigNNoVersion): ## SKIP triggers in the skip list
                        continue
                    ExpectedRate=-1
                    for refTrigN,refTrigRate,refTrigPS,refLa in RefParser.TriggerRates:
                        refTrigNNoVersion = refTrigN[:refTrigN.rfind('_')]
                        if refTrigNNoVersion == headTrigNNoVersion:
                            ExpectedRate = round(refTrigRate * HeadParser.AvLiveLumi/RefParser.AvLiveLumi,2)
                            break
                    if ExpectedRate==-1:
                        NotFound.append(headTrigNNoVersion)
                        continue
                    PerDiff=0
                    if ExpectedRate>0:
                        PerDiff = int(round( (headTrigRate-ExpectedRate)/ExpectedRate,2 )*100)
                    ##Write Line ##
                    if headTrigRate==0:
                        write(bcolors.FAIL)
                    elif abs(PerDiff) >AllowedRateDiff:
                        write(bcolors.FAIL)
                    else:
                        write(bcolors.OKGREEN)
                    write('* '+headTrigN+' '*(nameBufLen-len(headTrigN)-5)+'*')
                    write(' '*(RateBuffLen-len(str(headTrigRate))-1)+str(headTrigRate)+' *')
                    write(' '*(RateBuffLen-len(str(ExpectedRate))-1)+str(ExpectedRate)+' *')
                    if ExpectedRate>0:
                        if abs(PerDiff) > AllowedRateDiff/2:
                            write(' '+' '*(RateBuffLen-len(str(PerDiff))-2)+str(PerDiff)+'%')
                        else:
                            write('  good    ')                
                    else:
                        write('          ')
                    write(' *')
                    if headTrigRate==0:
                        write(" << TRIGGER RATE IS ZERO! CALL HLT DOC")
                        CallDOC=True
                    elif abs(PerDiff) > AllowedRateDiff:
                        write(" << LARGE RATE DIFFERENCE WITH REFERENCE RUN")
                        CallDOC=True
                    write(bcolors.ENDC+'\n')

            if CallDOC:
                write(bcolors.FAIL)
                print "\nSomething looks very wrong in this run"
                print "If there is no obvious reason for this (subdetector out, etc.): **inform the SHIFT LEADER and call the HLT DOC!**"
                raw_input("Press Enter to continue ... ")
                write(bcolors.ENDC)

            if FindL1Zeros:
                L1Zeros=[]
                IgnoreBits = ["L1_PreCollisions","L1_InterBunch_Bsc","L1_BeamHalo","L1_BeamGas_Hf"]
                for trigN,L1Pass,PSPass,PAccept,SeedName in HeadParser.Nevts:
                    ## Skip events in the skip list
                    trigNNoVersion = trigN[:trigN.rfind('_')]
                    if Config.AnalyzeTrigger(trigNNoVersion):
                        continue
                        ## if no events pass the L1, add it to the L1Zeros list if not already there
                    if SeedName in IgnoreBits:
                        continue
                    if L1Pass==0 and not SeedName in L1Zeros and SeedName.find("BeamGas")==-1 and SeedName.find('L1_SingleMuOpen')==-1:
                        L1Zeros.append(SeedName)
                if len(L1Zeros) == 0:
                    pass
                #print bcolors.OKGREEN+">>>  L1 Seeds are fine"+bcolors.ENDC

            # end if find l1 zeros

            FirstTime+=1
        # End of if FirstTime
    #end of try
    except KeyboardInterrupt:
        print "Quitting the program"
