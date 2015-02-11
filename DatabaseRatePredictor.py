#!/usr/bin/env python

from DatabaseParser import *
from GetListOfRuns import *
import sys
import os
from numpy import *
import pickle
import getopt
from StreamMonitor import StreamMonitor
from itertools import groupby
from operator import itemgetter
from collections import deque

from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle
from ROOT import TFile, TPaveText, TBrowser
from ROOT import gBenchmark
import array
import math
from ReadConfig import RateMonConfig
from TablePrint import *
from selectionParser import selectionParser

def usage():
    print sys.argv[0]+" [options] <list of runs>"
    print "This script is used to generate fits and do secondary shifter validation"
    print "For more information, see https://twiki.cern.ch/twiki/bin/view/CMS/RateMonitoringScriptWithReferenceComparison"
    print "<list of runs>                       this is a list of the form: a b c-d e f-g, specifying individual runs and/or run ranges"
    print "                                     be careful with using ranges (c-d), it is highly recommended to use a JSON in this case"
    print "options: "
    print "--makeFits                           run in fit making mode"
    print "--secondary                          run in secondary shifter mode"
    print "--fitFile=<path>                     path to the fit file"
    print "--json=<path>                        path to the JSON file"
    print "--TriggerList=<path>                 path to the trigger list (without versions!)"
    print "--AllTriggers                        Run for all triggers instead of specifying a trigger list"    
    print "--maxdt=<max deadtime>               Mask LS above max deadtime threshold"
    print "--All                                Mask LS with any red LS on WBM LS page (not inc castor zdc etc)"
    print "--Mu                                 Mask LS with Mu (RPC, DT+, DT-, DT0, CSC+ and CSC-) off"
    print "--HCal                               Mask LS with HCal barrel off"
    print "--Tracker                            Mask LS with Tracker barrel off"
    print "--ECal                               Mask LS with ECal barrel off"
    print "--EndCap                             Mask LS with EndCap sys off, used in combination with other subsys"
    print "--Beam                               Mask LS with Beam off"
    print "--UseVersionNumbers                  Don't ignore path version numbers"
    print "--linear                             Force linear fits"
    print "--inst                               Make fits using instantaneous luminosity instead of delivered"
    print "--write                              Writes fit info into csv, for ranking nonlinear triggers"
    
class Modes:
    none,fits,secondary = range(3)

def pickYear():
    global thisyear
    thisyear="2012"
    print "Year set to ",thisyear

def main():
    gROOT.SetBatch(True)
    try:
        ##set year to 2012
        pickYear()
        
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["makeFits","secondary","fitFile=","json=","TriggerList=","maxdt=","All","Mu","HCal","Tracker","ECal","EndCap","Beam","UseVersionNumbers","linear","inst","write","AllTriggers","UsePSCol="])
            
        except getopt.GetoptError, err:
            print str(err)
            usage()
            sys.exit(2)
            
##### RUN LIST ########
        run_list=[]
    
        if len(args)<1:
            inputrunlist=[]
            print "No runs specified"
            runinput=raw_input("Enter run range in form <run1> <run2> <run3> or <run1>-<run2>:")
            inputrunlist.append(runinput)
            
            if runinput.find(' ')!=-1:
                args=runinput.split(' ')
            else:
                args.append(runinput)    
            
        for r in args:
            if r.find('-')!=-1:  # r is a run range
                rrange = r.split('-')
                if len(rrange)!=2:
                    print "Invalid run range %s" % (r,)
                    sys.exit(0)
                try:
                    for rr in range(int(rrange[0]),int(rrange[1])+1):
                        run_list.append(rr)
                except:
                    print "Invalid run range %s" % (r,)
                    sys.exit(0)
            else: # r is not a run range
                try:
                    run_list.append(int(r))
                except:
                    print "Invalid run %s" % (r,)
    
##### READ CMD LINE ARGS #########
        mode = Modes.none
        fitFile = ""
        jsonfile = ""
        trig_list = []
        max_dt=-1.0
        subsys=-1.0
        NoVersion=True
        linear=False
        do_inst=False
        wp_bool=False
        all_triggers=False
        DoL1=True
        UsePSCol=-1
        SubSystemOff={'All':False,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':False}
        for o,a in opt:
            if o == "--makeFits":
                mode = Modes.fits
            elif o == "--secondary":
                mode = Modes.secondary
            elif o == "--fitFile":
                fitFile = str(a)
            elif o == "--json":
                jsonfile = a
            elif o=="--maxdt":
                max_dt = float(a)               
            elif o=="--All":
                subsys=1
                SubSystemOff["All"]=True
            elif o=="--Mu":
                subsys=1
                SubSystemOff["Mu"]=True
            elif o=="--HCal":
                SubSystemOff["HCal"]=True
                subsys=1
            elif o=="--Tracker":
                SubSystemOff["Tracker"]=True
                subsys=1
            elif o=="--ECal":
                SubSystemOff["ECal"]=True
                subsys=1
            elif o=="--EndCap":
                SubSystemOff["EndCap"]=True
                subsys=1
            elif o=="--Beam":
                SubSystemOff["Beam"]=True
                subsys=1
            elif o=="--UseVersionNumbers":
                NoVersion=False
            elif o=="--linear":
                linear=True
            elif o=="--inst":
                do_inst=True
            elif o=="--write":
                wp_bool=True
            elif o=="--AllTriggers":
                all_triggers=True
            elif o=="--UsePSCol":
                UsePSCol=int(a)
            elif o == "--TriggerList":
                try:
                    f = open(a)
                    for entry in f:
                        if entry.startswith('#'):
                            continue
                        if entry.find(':')!=-1:
                            entry = entry[:entry.find(':')]   ## We can point this to the existing monitor list, just remove everything after ':'!
                            if entry.find('#')!=-1:
                                entry = entry[:entry.find('#')]   ## We can point this to the existing monitor list, just remove everything after ':'!                    
                        trig_list.append( entry.rstrip('\n'))
                except:
                    print "\nInvalid Trigger List\n"
                    sys.exit(0)
            else:
                print "\nInvalid Option %s\n" % (str(o),)
                usage()
                sys.exit(2)

        print "\n\n"
        
###### MODES #########
        if mode == Modes.none: ## no mode specified
            print "\nNo operation mode specified!\n"
            modeinput=raw_input("Enter mode, --makeFits or --secondary:")
            print "modeinput=",modeinput
            if not (modeinput=="--makeFits" or modeinput=="--secondary"):
                print "not either"
                usage()
                sys.exit(0)
            elif modeinput == "--makeFits":
                mode=Modes.fits
            elif modeinput == "--secondary":
                mode=Modes.secondary
            else:
                print "FATAL ERROR: No Mode specified"
                sys.exit(0)
        
        if mode == Modes.fits:
            print "Running in Fit Making mode\n\n"
        elif mode == Modes.secondary:
            print "Running in Secondary Shifter mode\n\n"
        else:  ## should never get here, but exit if we do
            print "FATAL ERROR: No Mode specified"
            sys.exit(0)

        if fitFile=="" and not mode==Modes.fits:
            print "\nPlease specify fit file. These are available:\n"
            path="Fits/%s/" % (thisyear)  # insert the path to the directory of interest
            dirList=os.listdir(path)
            for fname in dirList:
                print fname
            fitFile = path+raw_input("Enter fit file in format Fit_HLT_10LS_Run176023to180252.pkl: ")
            
        elif fitFile=="":
            NoVstr=""
            if NoVersion:
                NoVstr="NoV_"
            if not do_inst:
                fitFile="Fits/%s/Fit_HLT_%s10LS_Run%sto%s.pkl" % (thisyear,NoVstr,min(run_list),max(run_list))
            else:
                fitFile="Fits/%s/Fit_inst_HLT_%s10LS_Run%sto%s.pkl" % (thisyear,NoVstr,min(run_list),max(run_list))
            
        if "NoV" in fitFile:
            NoVersion=True

###### TRIGGER LIST #######        
        if trig_list == [] and not all_triggers:
            print "\nPlease specify list of triggers\n"
            print "Available lists are:"
            dirList=os.listdir(".")
            for fname in dirList:
                entry=fname
                if entry.find('.')!=-1:
                    extension = entry[entry.find('.'):]   ## We can point this to the existing monitor list, just remove everything after ':'!
                    if extension==".list":
                        print fname
            trig_input=raw_input("\nEnter triggers in format HLT_IsoMu30_eta2p1 or a .list file, or enter AllTriggers to run over all triggers in the menu: ")

            if trig_input.find('AllTriggers') != -1:
                all_triggers = True
            elif trig_input.find('.') != -1:
                extension = trig_input[trig_input.find('.'):]
                if extension==".list":
                    try:
                        fl=open(trig_input)
                    except:
                        print "Cannot open file"
                        usage()
                        sys.exit(0)
                    
                    for line in fl:
                        if line.startswith('#'):
                            continue
                        if len(line)<1:
                            continue                                        
                        if len(line)>=2:
                            arg=line.rstrip('\n').rstrip(' ').lstrip(' ')
                            trig_list.append(arg)
                        else:
                            arg=''
                else:
                    trig_list.append(trig_input)
        
        if jsonfile=="":
            JSON=[]
        else:
            print "Using JSON: %s" % (jsonfile,)
            JSON = GetJSON(jsonfile) ##Returns array JSON[runs][ls_list]

        ###### TO CREATE FITS #########
        if mode == Modes.fits:
            trig_name = "HLT"
            num_ls = 10
            physics_active_psi = True ##Requires that physics and active be on, and that the prescale column is not 0
            debug_print = False
            no_versions=False
            min_rate = 0.0
            print_table = False
            data_clean = True ##Gets rid of anomalous rate points, reqires physics_active_psi (PAP) and deadtime < 20%
            ##plot_properties = [varX, varY, do_fit, save_root, save_png, fit_file]
            if not do_inst:
                plot_properties = [["delivered", "rate", True, True, False, fitFile]]
#                plot_properties = [["delivered", "rawrate", True, True, False, fitFile]]                
            else:
                plot_properties = [["inst", "rate", True, True, False, fitFile]]
        
            masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_Zero", "HLT_BeamGas", "HLT_Activity", "L1_BeamGas", "L1_ZeroBias"]            
            save_fits = True
            if max_dt==-1.0:
                max_dt=0.08 ## no deadtime cutuse 2.0
            force_new=True
            print_info=True
            if subsys==-1.0: 
                SubSystemOff={'All':False,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':True}

        ###### TO SEE RATE VS PREDICTION ########
        if mode == Modes.secondary:
            trig_name = "HLT"
            num_ls = 1
            physics_active_psi = True
            debug_print = False
            no_versions=False
            min_rate = 0.0
            print_table = False
            data_clean = True
            ##plot_properties = [varX, varY, do_fit, save_root, save_png, fit_file]
            plot_properties = [["ls", "rawrate", False, True, False,fitFile]]            
            ## rate is calculated as: (measured rate, deadtime corrected) * prescale [prediction not dt corrected]
            ## rawrate is calculated as: measured rate [prediction is dt corrected]

            masked_triggers = ["AlCa_", "DST_", "HLT_L1", "HLT_Zero", "HLT_BeamGas", "HLT_Activity", "L1_BeamGas", "L1_ZeroBias"]
            save_fits = False
            if max_dt==-1.0:
                max_dt=2.0 ## no deadtime cut=2.0
            force_new=True
            print_info=True
            if subsys==-1.0:
                SubSystemOff={'All':True,'Mu':False,'HCal':False,'ECal':False,'Tracker':False,'EndCap':False,'Beam':True}
    
        for k in SubSystemOff.iterkeys():
            print k,"=",SubSystemOff[k],"   ",
        print " "
        L1SeedChangeFit=True
        ########  END PARAMETERS - CALL FUNCTIONS ##########
        #[Rates,LumiPageInfo, L1_trig_list,nps]= GetDBRates(run_list, trig_name, trig_list, num_ls, max_dt, physics_active_psi, JSON, debug_print, force_new, SubSystemOff,NoVersion,all_triggers, DoL1,UsePSCol,L1SeedChangeFit)
        [Rates, LumiPageInfo, L1_trig_list, nps]= GetDBRates(run_list, trig_name, trig_list, num_ls, max_dt, physics_active_psi, JSON, debug_print, force_new, SubSystemOff, NoVersion, all_triggers, DoL1,UsePSCol,L1SeedChangeFit, save_fits)
        if DoL1:
            trig_list=L1_trig_list
        
        MakePlots(Rates, LumiPageInfo, run_list, trig_name, trig_list, num_ls, min_rate, max_dt, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print,SubSystemOff, print_info,NoVersion, linear, do_inst,wp_bool,all_triggers,L1SeedChangeFit,nps)

    except KeyboardInterrupt:
        print "Wait... come back..."


#def GetDBRates(run_list,trig_name,trig_list, num_ls, max_dt, physics_active_psi,JSON,debug_print, force_new, SubSystemOff,NoVersion,all_triggers, DoL1,UsePSCol,L1SeedChangeFit):
def GetDBRates(run_list, trig_name, trig_list, num_ls, max_dt, physics_active_psi, JSON, debug_print, force_new, SubSystemOff, NoVersion, all_triggers, DoL1,UsePSCol, L1SeedChangeFit, save_fits):
    
    Rates = {}
    LumiPageInfo={}
    ## Save in RefRuns with name dependent on trig_name, num_ls, JSON, and physics_active_psi
    if JSON:
        #print "Using JSON file"
        if physics_active_psi:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS_JPAP.pkl" 
        else:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS_JSON.pkl" 
    else:
        print "Using Physics and Active ==1"
        if physics_active_psi:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS_PAP.pkl"
        else:
            RefRunNameTemplate = "RefRuns/%s/Rates_%s_%sLS.pkl"
    
    RefRunFile = RefRunNameTemplate % (thisyear,trig_name,num_ls)
    RefRunFileHLT = RefRunNameTemplate % (thisyear,"HLT",num_ls)

    print "RefRun=",RefRunFile
    print "RefRunFileHLT",RefRunFileHLT
    if not force_new:
        try: ##Open an existing RefRun file with the same parameters and trigger name
            pkl_file = open(RefRunFile, 'rb')
            Rates = pickle.load(pkl_file)
            pkl_file.close()
            os.remove(RefRunFile)
            print "using",RefRunFile
            
        except:
            try: ##Open an existing RefRun file with the same parameters and HLT for trigger name
                pkl_file = open(RefRunFileHLT)
                HLTRates = pickle.load(pkl_file)
                for key in HLTRates:
                    if trig_name in str(key):
                        Rates[key] = HLTRates[key]
                #print str(RefRunFile)+" does not exist. Creating ..."
            except:
                print str(RefRunFile)+" does not exist. Creating ..."
         
## try the lumis file
    RefLumiNameTemplate = "RefRuns/%s/Lumis_%s_%sLS.pkl"      
    RefLumiFile= RefLumiNameTemplate % (thisyear,"HLT",num_ls)
    if not force_new:
        try:
            pkl_lumi_file = open(RefLumiFile, 'rb')
            LumiPageInfo = pickle.load(pkl_lumi_file)
            pkl_lumi_file.close()
            os.remove(RefLumiFile)
            print "using",RefLumiFile
        except:
            print str(RefLumiFile)+" doesn't exist. Make it..."

    trig_list_noV=[]
    for trigs in trig_list:
        trig_list_noV.append(StripVersion(trigs))
    
    if NoVersion:
        trig_list=trig_list_noV
        
    for RefRunNum in run_list:
        if JSON:
            if not RefRunNum in JSON:
                continue
        try:            
            ExistsAlready = False
            for key in Rates:
                if RefRunNum in Rates[key]["run"]:
                    ExistsAlready = True
                    break
            
            LumiExistsLAready=False
            for v in LumiPageInfo.itervalues():
                if RefRunNum == v["Run"]:
                    LumiExistsAlready=True
                    break
            if ExistsAlready and LumiExistsAlready:
                continue
           
        except:
            print "Getting info for run "+str(RefRunNum)
        
        if RefRunNum < 1:
            continue
        ColRunNum,isCol,isGood = GetLatestRunNumber(RefRunNum)
        if not isGood:
            print "Run ",RefRunNum, " is not Collisions"
            
            continue
        
        if not isCol:
            print "Run ",RefRunNum, " is not Collisions"
            
            continue
        
        print "calculating rates and green lumis for run ",RefRunNum
        
        if True: ##Placeholder
            if True: #May replace with "try" - for now it's good to know when problems happen
                RefParser = DatabaseParser()
                RefParser.RunNumber = RefRunNum
                RefParser.ParseRunSetup()
                RefLumiRangePhysicsActive = RefParser.GetLSRange(1,9999) ##Gets array of all LS with physics and active on
                RefLumiArray = RefParser.GetLumiInfo() ##Gets array of all existing LS and their lumi info
                RefLumiRange = []
                RefMoreLumiArray = RefParser.GetMoreLumiInfo()#dict with keys as bits from lumisections WBM page and values are dicts with key=LS:value=bit
                L1HLTseeds=RefParser.GetL1HLTseeds()
                HLTL1PS=RefParser.GetL1PSbyseed()
                ###Add all triggers to list if all trigger
                try:
                    TriggerRatesCheck = RefParser.GetHLTRates([1])##just grab from 1st LS
                except:
                    print "ERROR: unable to get HLT triggers for this run"
                    exit(2)
                for HLTkey in TriggerRatesCheck:
                    if NoVersion:
                        name = StripVersion(HLTkey)
                    else:
                        name=HLTkey
                    if not name in trig_list:
                        if all_triggers:
                            trig_list.append(name)
                
                ###add L1 triggers to list if Do L1
                if DoL1:
                    for HLTkey in trig_list:
                        #print name
#                         if "L1" in HLTkey:
#                             continue
                        if not HLTkey.startswith('HLT'):
                            continue
                        else:
                            try:
                                for L1seed in L1HLTseeds[HLTkey]:
                                    if L1seed not in trig_list:
                                        trig_list.append(L1seed)
                            except:
                                print "Failed on trigger "+str(HLTkey)
                                pass
                for iterator in RefLumiArray[0]: ##Makes array of LS with proper PAP and JSON properties
                    ##cheap way of getting PSCol None-->0
                    if RefLumiArray[0][iterator] not in range(1,9):
                        RefLumiArray[0][iterator]=0
                        
                    if not UsePSCol==-1:
                        if not RefLumiArray[0][iterator]==UsePSCol:
                            print "skipping LS",iterator
                            continue

                    if not physics_active_psi or (RefLumiArray[5][iterator] == 1 and RefLumiArray[6][iterator] == 1 and RefMoreLumiArray["b1pres"][iterator]==1 and RefMoreLumiArray["b2pres"][iterator]==1 and RefMoreLumiArray["b1stab"][iterator] and RefMoreLumiArray["b2stab"][iterator]==1):
                        if not JSON or RefRunNum in JSON:
                            if not JSON or iterator in JSON[RefRunNum]:
                                RefLumiRange.append(iterator)
                    
                try:
                    nls = RefLumiRange[0]
                    LSRange = {}
                except:
                    print "Run "+str(RefRunNum)+" has no good LS"
                    continue
                if num_ls > len(RefLumiRange):
                    print "Run "+str(RefRunNum)+" is too short: from "+str(nls)+" to "+str(RefLumiRange[-1])+", while num_ls = "+str(num_ls)
                    continue
                while nls < RefLumiRange[-1]-num_ls:
                    LSRange[nls] = []
                    counter = 0
                    for iterator in RefLumiRange:
                        if iterator >= nls and counter < num_ls:
                            LSRange[nls].append(iterator)
                            counter += 1
                    nls = LSRange[nls][-1]+1
                [HLTL1_seedchanges,nps]=checkL1seedChangeALLPScols(trig_list,HLTL1PS) #for L1prescale changes
                    
                
                #print HLTL1_seedchanges
                #print "nps=",nps
                #print "Run "+str(RefRunNum)+" contains LS from "+str(min(LSRange))+" to "+str(max(LSRange))
                for nls in sorted(LSRange.iterkeys()):
                    TriggerRates = RefParser.GetHLTRates(LSRange[nls])
                    #L1Rate=RefParser.GetDeadTimeBeamActive(LSRange[nls])

                    ## Clumsy way to append Stream A. Should choose correct method for calculating stream a based on ps column used in data taking.

                    if ('HLT_Stream_A' in trig_list) or all_triggers:
                        config = RateMonConfig(os.path.abspath(os.path.dirname(sys.argv[0])))
                        config.ReadCFG()
                        stream_mon = StreamMonitor() 
                        core_a_rates = stream_mon.getStreamACoreRatesByLS(RefParser,LSRange[nls],config).values()
                        avg_core_a_rate = sum(core_a_rates)/len(LSRange[nls])
                        TriggerRates['HLT_Stream_A'] = [1,1,avg_core_a_rate,avg_core_a_rate]
                        HLTL1_seedchanges["HLT_Stream_A"] = [[ps_col] for ps_col in range(0,nps)]
#                         dummylist=[]
#                         for pscol in range(0,nps):
#                             doubledummylist=[]
#                             doubledummylist.append(pscol)
#                             dummylist.append(doubledummylist)
#                         HLTL1_seedchanges["HLT_Stream_A"]=dummylist
                    
                    if DoL1:
                        L1RatesALL=RefParser.GetL1RatesALL(LSRange[nls])
                        
                        for L1seed in L1RatesALL.iterkeys():
                            TriggerRates[L1seed]=L1RatesALL[L1seed]

                    [inst, live, delivered, dead, pscols] = RefParser.GetAvLumiInfo(LSRange[nls])
                    deadtimebeamactive=RefParser.GetDeadTimeBeamActive(LSRange[nls])
                    
                    physics = 1
                    active = 1
                    psi = 99
                    if save_fits and (max(pscols) != min(pscols)):#kick out points which average over two ps columns if doing running in fit making mode
                        continue
                    for iterator in LSRange[nls]: ##Gets lowest value of physics, active, and psi in the set of lumisections
                        if RefLumiArray[5][iterator] == 0:
                            physics = 0
                        if RefLumiArray[6][iterator] == 0:
                            active = 0
                        if RefLumiArray[0][iterator] < psi:
                            psi = RefLumiArray[0][iterator]

                    if inst < 0 or live < 0 or delivered < 0:
                        print "Run "+str(RefRunNum)+" LS "+str(nls)+" inst lumi = "+str(inst)+" live lumi = "+str(live)+", delivered = "+str(delivered)+", physics = "+str(physics)+", active = "+str(active)
                    
                    LumiPageInfo[nls] = LumiRangeGreens(RefMoreLumiArray,LSRange,nls,RefRunNum,deadtimebeamactive)

                    for key in TriggerRates:

                        if NoVersion:
                            name = StripVersion(key)
                        else:
                            name=key
                            
                        if not name in trig_list:
                            if all_triggers and name.startswith('HLT_Stream_A'):
                                trig_list.append(name) ##Only triggers in trig_list have HLTL1_seedchanges filled
                            else:    
                                continue
                        
                        if not Rates.has_key(name):
                            Rates[name] = {}
                            Rates[name]["run"] = []
                            Rates[name]["ls"] = []
                            Rates[name]["ps"] = []
                            Rates[name]["inst_lumi"] = []
                            Rates[name]["live_lumi"] = []
                            Rates[name]["delivered_lumi"] = []
                            Rates[name]["deadtime"] = []
                            Rates[name]["rawrate"] = []
                            Rates[name]["rate"] = []
                            Rates[name]["rawxsec"] = []
                            Rates[name]["xsec"] = []
                            Rates[name]["physics"] = []
                            Rates[name]["active"] = []
                            Rates[name]["psi"] = []
                            Rates[name]["L1seedchange"]=[]
                        [avps, ps, rate, psrate] = TriggerRates[key]
                        Rates[name]["run"].append(RefRunNum)
                        Rates[name]["ls"].append(nls)
                        Rates[name]["ps"].append(ps)
                        Rates[name]["inst_lumi"].append(inst)
                        Rates[name]["live_lumi"].append(live)
                        Rates[name]["delivered_lumi"].append(delivered)
                        Rates[name]["deadtime"].append(deadtimebeamactive)
                        Rates[name]["rawrate"].append(rate)
                        Rates[name]["L1seedchange"].append(HLTL1_seedchanges[name])
                        if live == 0:
                            Rates[name]["rate"].append(0.0)
                            Rates[name]["rawxsec"].append(0.0)
                            Rates[name]["xsec"].append(0.0)
                        else:
                            try:
                                Rates[name]["rate"].append(psrate/(1.0-deadtimebeamactive))
                            except:
                                Rates[name]["rate"].append(0.0)
                            Rates[name]["rawxsec"].append(rate/live)
                            Rates[name]["xsec"].append(psrate/live)
                        Rates[name]["physics"].append(physics)
                        Rates[name]["active"].append(active)
                        Rates[name]["psi"].append(psi)
                        
    RateOutput = open(RefRunFile, 'wb') ##Save new Rates[] to RefRuns
    pickle.dump(Rates, RateOutput, 2)
    RateOutput.close()
    LumiOutput = open(RefLumiFile,'wb')
    pickle.dump(LumiPageInfo,LumiOutput, 2)
    LumiOutput.close()
    
    return [Rates,LumiPageInfo,trig_list,nps]

def MakePlots(Rates, LumiPageInfo, run_list, trig_name, trig_list, num_ls, min_rate, max_dt, print_table, data_clean, plot_properties, masked_triggers, save_fits, debug_print, SubSystemOff, print_info,NoVersion, linear,do_inst,wp_bool,all_triggers,L1SeedChangeFit,nps):
    
    [min_run, max_run, priot, InputFit, OutputFit, OutputFitPS, failed_paths, first_trigger, varX, varY, do_fit, save_root, save_png, fit_file, RootNameTemplate, RootFile, InputFitPS]=InitMakePlots(run_list, trig_name, num_ls, plot_properties, nps, L1SeedChangeFit)
    ##modify for No Version and check the trigger list
    trig_list=InitTrigList(trig_list, save_fits, NoVersion, InputFit)

    for print_trigger in sorted(Rates):
        [trig_list, passchecktriglist, meanrawrate] = CheckTrigList(trig_list, print_trigger, all_triggers, masked_triggers, min_rate, Rates, run_list, trig_name, failed_paths)
        if not passchecktriglist: #failed_paths is modified by CheckTrigList to include output messages explaining why a trigger failed
            continue
        
        [meanrate, meanxsec, meanlumi, sloperate, slopexsec, nlow, nhigh, lowrate, lowxsec, lowlumi, highrate, highxsec, highlumi]=GetMeanRates(Rates, print_trigger, max_dt)
        chioffset=1.0 ##chioffset now a fraction; must be 10% better to use expo rather than quad, quad rather than line
        width = max([len(trigger_name) for trigger_name in trig_list])
        for psi in range(0,nps):
            OutputFitPS[psi][print_trigger]=[]##define empty list for each trigger
        
        ####START OF L1 SEED LOOP####
        #print "LIST L1 seed changes",Rates[print_trigger]["L1seedchange"][0]
        
        if L1SeedChangeFit and do_fit:
            dummyPSColslist=Rates[print_trigger]["L1seedchange"][0]
            #print print_trigger, dummyPSColslist
            if len(dummyPSColslist)!=1: 
                dummyPSColslist.append(range(0,nps))
        else:
            dummyPSColslist=[]
            dummyPSColslist.append(range(0,nps))


        if not do_fit:
            [fitparams, passedGetFit, failed_paths, fitparamsPS]=GetFit(do_fit, InputFit, failed_paths, print_trigger, num_ls,L1SeedChangeFit, InputFitPS,nps)
            if not passedGetFit:
                print str(print_trigger)+" did not passedGetFit"
                continue
        else:
            fitparams=["unset",0,0,0,0,0,0]
            fitparamsPS=["unset",{},{},{},{},{},{}]
            
        for PSColslist in dummyPSColslist:
            #print print_trigger, PSColslist
            passPSinCol=0
            for iterator in range (len(Rates[print_trigger]["run"])):
                if Rates[print_trigger]["psi"][iterator] in PSColslist:
                    passPSinCol=1
                    #print PSColslist, Rates[print_trigger]["run"][iterator], Rates[print_trigger]["psi"][iterator]
            if not passPSinCol:
                ##for when there are no LS in some PS col (pretty common!)
                #print print_trigger, "No data for",PSColslist
                continue
        
            
            AllPlotArrays=DoAllPlotArrays(Rates, print_trigger, run_list, data_clean, meanxsec, num_ls, LumiPageInfo, SubSystemOff, max_dt, print_info, trig_list, do_fit, do_inst, debug_print, fitparams, fitparamsPS, L1SeedChangeFit, PSColslist, first_trigger)
            [VX, VXE, x_label, VY, VYE, y_label, VF, VFE] = GetVXVY(plot_properties, fit_file, AllPlotArrays, L1SeedChangeFit)
        
        
            ####defines gr1 and failure if no graph in OutputFit ####
            defgrapass = False
            if len(VX) > 0:
                [OutputFit,gr1, gr3, failed_paths, defgrapass]=DefineGraphs(print_trigger,OutputFit,do_fit,varX,varY,x_label,y_label,VX,VY,VXE,VYE,VF,VFE,fit_file, failed_paths,PSColslist)
            if not defgrapass:
                continue
            if do_fit:
                [f1a,f1b,f1c,f1d,first_trigger]= Fitter(gr1,VX,VY,sloperate,nlow,Rates,print_trigger, first_trigger, varX, varY,lowrate)
                        
        
            if print_table or save_fits:
                ###aditional info from f1 params
                [f1a_Chi2, f1b_Chi2, f1c_Chi2,f1d_Chi2, f1a_BadMinimum, f1b_BadMinimum, f1c_BadMinimum, meanps, av_rte, passmorefitinfo]=more_fit_info(f1a,f1b,f1c,f1d,VX,VY,print_trigger,Rates)
                if not passmorefitinfo:
                    OutputFit[print_trigger] = ["fit failed","Zero NDF"]
                ###output fit params
                else:    
                    [OutputFit,first_trigger, failed_paths]=output_fit_info(do_fit,f1a,f1b,f1c,f1d,varX,varY,VX,VY,linear,print_trigger,first_trigger,Rates,width,chioffset,wp_bool,num_ls,meanrawrate,OutputFit, failed_paths, PSColslist, dummyPSColslist)
            if do_fit:        
                for PSI in PSColslist:
                    if not OutputFitPS[PSI][print_trigger]:
                        OutputFitPS[PSI][print_trigger]=OutputFit[print_trigger]
            
            PSlist=deque(PSColslist)
            PSmin=PSlist.popleft()
            if not PSlist:
                PSmax=PSmin
            else:
                PSmax=PSlist.pop()

            first_trigger=False        
            if save_root or save_png:
                c1 = TCanvas(str(varX),str(varY))
                c1.SetName(str(print_trigger)+"_ps"+str(PSmin)+"_"+str(PSmax)+"_"+str(varY)+"_vs_"+str(varX))
            gr1.Draw("APZ")    
            if not do_fit:
                gr3.Draw("P3")
                c1.Update()
            else:    
                c1=DrawFittedCurve(f1a, f1b,f1c, f1d, chioffset,do_fit,c1,VX ,VY,print_trigger,Rates)
            
            if save_root:
                myfile = TFile( RootFile, 'UPDATE' )
                c1.Write()

                
                myfile.Close()
            if save_png:
                c1.SaveAs(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX)+".png")
        

                
    EndMkrootfile(failed_paths, save_fits, save_root, fit_file, RootFile, OutputFit, OutputFitPS, L1SeedChangeFit)
    

    
    

  ############# SUPPORTING FUNCTIONS ################

def InitMakePlots(run_list, trig_name, num_ls, plot_properties, nps, L1SeedChangeFit):
    min_run = min(run_list)
    max_run = max(run_list)

    priot.has_been_called=False
    
    InputFit = {}
    InputFitPS = {}
    OutputFit = {}
    failed_paths = []
    first_trigger=True
    OutputFitPS={}
    for ii in range(0,nps):
        OutputFitPS[ii]={}
    
    [[varX, varY, do_fit, save_root, save_png, fit_file]] = plot_properties

    RootNameTemplate = "%s_%sLS_%s_vs_%s_Run%s-%s.root"
    RootFile = RootNameTemplate % (trig_name, num_ls, varX, varY, min_run, max_run)

    if not do_fit:
        try:
            pkl_file = open(fit_file, 'rb')
            InputFit = pickle.load(pkl_file)
            print "opening fit_file"
            pkl_file.close()
        except:
            print "ERROR: could not open fit file: %s" % (fit_file,)
            exit(2)
        if L1SeedChangeFit:
            try:
                PSfitfile=fit_file.replace("HLT_NoV","HLT_NoV_ByPS")
                print "opening",PSfitfile
                pklfilePS = open(PSfitfile, 'rb')
                InputFitPS = pickle.load(pklfilePS)
            except:
                print "ERROR: could not open fit file: %s" % (PSfitfile,)
                exit(2)
                           
    if save_root:
        try:
            os.remove(RootFile)
        except:
            pass
        

    return [min_run, max_run, priot, InputFit, OutputFit, OutputFitPS, failed_paths, first_trigger, varX, varY, do_fit, save_root, save_png, fit_file, RootNameTemplate, RootFile, InputFitPS]

def InitTrigList(trig_list, save_fits, NoVersion, InputFit):
    trig_list_noV=[]
    for trigs in trig_list:
        trig_list_noV.append(StripVersion(trigs))
    if NoVersion:
        trig_list=trig_list_noV
    
    ## check that all the triggers we ask to plot are in the input fit
    if not save_fits:
        goodtrig_list = []
        FitInputNoV={}
        for trig in trig_list:
            
            if NoVersion:
                for trigger in InputFit.iterkeys():
                    FitInputNoV[StripVersion(trigger)]=InputFit[trigger]
                InputFit=FitInputNoV
                                    
            else:
                if not InputFit.has_key(trig):
                    print "WARNING:  No Fit Prediction for Trigger %s, SKIPPING" % (trig,)
                else:
                    goodtrig_list.append(trig)
                trig_list = goodtrig_list
    return trig_list            

##Limits Rates[] to runs in run_list
def CheckTrigList(trig_list, print_trigger, all_triggers, masked_triggers, min_rate, Rates, run_list, trig_name, failed_paths):

    NewTrigger = {}
    passed = 1 ##to replace continue
    mean_raw_rate = 0
    if not print_trigger in trig_list:
        if all_triggers:
            trig_list.append(print_trigger)
        else:
            failed_paths.append([print_trigger,"The monitorlist did not include these paths"])
            passed = 0
            return [trig_list, passed, mean_raw_rate]
        
    for key in Rates[print_trigger]:
        NewTrigger[key] = []
        
    for iterator in range(len(Rates[print_trigger]["run"])):
        if Rates[print_trigger]["run"][iterator] in run_list:
            for key in Rates[print_trigger]:
                NewTrigger[key].append(Rates[print_trigger][key][iterator])

    Rates[print_trigger] = NewTrigger
    mean_raw_rate = sum(Rates[print_trigger]["rawrate"])/len(Rates[print_trigger]["rawrate"])
    if mean_raw_rate < min_rate:
        failed_paths.append([print_trigger,"The rate of these paths did not exceed the minimum"])        
        passed = 0

    masked_trig = False
    for mask in masked_triggers:
        if str(mask) in print_trigger:
            masked_trig = True
    if masked_trig:
        failed_paths.append([print_trigger,"These paths were masked"])        
        passed = 0
            
    return [trig_list, passed, mean_raw_rate]



def GetMeanRates(Rates, print_trigger, max_dt):
    lowlumi = 0
    meanlumi_init = median(Rates[print_trigger]["live_lumi"])
    meanlumi = 0
    highlumi = 0
    lowrate = 0
    meanrate = 0
    highrate = 0
    lowxsec = 0
    meanxsec = 0
    highxsec = 0
    nlow = 0
    nhigh = 0
        
    for iterator in range(len(Rates[print_trigger]["rate"])):
        if Rates[print_trigger]["live_lumi"][iterator] <= meanlumi_init:
            if ( Rates[print_trigger]["rawrate"][iterator] > 0.04 and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1 and Rates[print_trigger]["deadtime"][iterator] < max_dt and Rates[print_trigger]["psi"][iterator] > 0 and Rates[print_trigger]["live_lumi"] > 500):
                meanrate+=Rates[print_trigger]["rate"][iterator]
                lowrate+=Rates[print_trigger]["rate"][iterator]
                meanxsec+=Rates[print_trigger]["xsec"][iterator]
                lowxsec+=Rates[print_trigger]["xsec"][iterator]
                meanlumi+=Rates[print_trigger]["live_lumi"][iterator]
                lowlumi+=Rates[print_trigger]["live_lumi"][iterator]
                nlow+=1
        if Rates[print_trigger]["live_lumi"][iterator] > meanlumi_init:
            if ( Rates[print_trigger]["rawrate"][iterator] > 0.04 and Rates[print_trigger]["physics"][iterator] == 1 and Rates[print_trigger]["active"][iterator] == 1 and Rates[print_trigger]["deadtime"][iterator] < max_dt and Rates[print_trigger]["psi"][iterator] > 0 and Rates[print_trigger]["live_lumi"] > 500):
                meanrate+=Rates[print_trigger]["rate"][iterator]
                highrate+=Rates[print_trigger]["rate"][iterator]
                meanxsec+=Rates[print_trigger]["xsec"][iterator]
                highxsec+=Rates[print_trigger]["xsec"][iterator]
                meanlumi+=Rates[print_trigger]["live_lumi"][iterator]
                highlumi+=Rates[print_trigger]["live_lumi"][iterator]
                nhigh+=1
    try:
        meanrate = meanrate/(nlow+nhigh)
        meanxsec = meanxsec/(nlow+nhigh)
        meanlumi = meanlumi/(nlow+nhigh)
        if (nlow==0):
            sloperate = (highrate/nhigh) / (highlumi/nhigh) 
            slopexsec = (highxsec/nhigh) / (highlumi/nhigh)
        elif (nhigh==0):
            sloperate = (lowrate/nlow) / (lowlumi/nlow)
            slopexsec = (lowxsec/nlow) / (lowlumi/nlow)
        else:
            sloperate = ( (highrate/nhigh) - (lowrate/nlow) ) / ( (highlumi/nhigh) - (lowlumi/nlow) )
            slopexsec = ( (highxsec/nhigh) - (lowxsec/nlow) ) / ( (highlumi/nhigh) - (lowlumi/nlow) )
    except:
        #            print str(print_trigger)+" has no good datapoints - setting initial xsec slope estimate to 0"
        meanrate = median(Rates[print_trigger]["rate"])
        meanxsec = median(Rates[print_trigger]["xsec"])
        meanlumi = median(Rates[print_trigger]["live_lumi"])
        sloperate = meanxsec
        slopexsec = 0
    return [meanrate, meanxsec, meanlumi, sloperate, slopexsec, nlow, nhigh, lowrate, lowxsec, lowlumi, highrate, highxsec, highlumi]    
        

################
def GetFit(do_fit, InputFit, failed_paths, print_trigger, num_ls, L1SeedChangeFit, InputFitPS,nps):
        
    passed=1
    FitTypePS={}
    X0PS={}
    X1PS={}
    X2PS={}
    X3PS={}
    sigmaPS={}
    X0errPS={}

    try:
        FitType = InputFit[print_trigger][0]
    except:
        failed_paths.append([print_trigger,"These paths did not exist in the monitorlist used to create the fit"])
        FitType = "parse failed"
        passed=0
        fitparams=[FitType, 0, 0, 0, 0, 0, 0]
    if FitType == "fit failed":
        failure_comment = InputFit[print_trigger][1]
        failed_paths.append([print_trigger, failure_comment])
        passed=0
        fitparams=[FitType, 0, 0, 0, 0, 0, 0]
    elif FitType == "parse failed":
        failure_comment = "These paths did not exist in the monitorlist used to create the fit"
    else:
        X0 = InputFit[print_trigger][1]
        X1 = InputFit[print_trigger][2]
        X2 = InputFit[print_trigger][3]
        X3 = InputFit[print_trigger][4]
        sigma = InputFit[print_trigger][5]/math.sqrt(num_ls)*3#Display 3 sigma band to show outliers more clearly
        X0err= InputFit[print_trigger][7]
        fitparams=[FitType, X0, X1, X2, X3, sigma, X0err]

    
    if L1SeedChangeFit:
            
        for psi in range(0,nps):
            #print psi, print_trigger, InputFitPS[psi][print_trigger]
            try:
                FitTypePS[psi] = InputFitPS[psi][print_trigger][0]
            except:
                failed_paths.append([print_trigger+'_PS_'+str(psi),"These paths did not exist in the monitorlist used to create the fit"])
                FitTypePS[psi] = "parse failed"
                passed=0
                fitparamsPS=[FitTypePS, X0PS, X1PS, X2PS, X3PS, sigmaPS, X0errPS]
            if FitTypePS[psi] == "fit failed":
                failure_comment = InputFitPS[psi][print_trigger][1]
                failed_paths.append([print_trigger+str(psi), failure_comment])
                passed=0
                fitparamsPS=[FitTypePS, X0PS, X1PS, X2PS, X3PS, sigmaPS, X0errPS]
            else:
                try:
                    X0PS[psi] = InputFitPS[psi][print_trigger][1]
                    X1PS[psi] = InputFitPS[psi][print_trigger][2]
                    X2PS[psi] = InputFitPS[psi][print_trigger][3]
                    X3PS[psi] = InputFitPS[psi][print_trigger][4]
                    sigmaPS[psi] = InputFitPS[psi][print_trigger][5]/math.sqrt(num_ls)*3#Display 3 sigma band to show outliers more clearly
                    X0errPS[psi]= InputFitPS[psi][print_trigger][7]
                    fitparamsPS=[FitTypePS, X0PS, X1PS, X2PS, X3PS, sigmaPS, X0errPS]
                except:
                    #print "ERROR: unable to get fits by PS for",print_trigger," in col",psi, "skipping."
                    pass
        
        
        
    return [fitparams, passed, failed_paths, fitparamsPS]        

## we are 2 lumis off when we start! -gets worse when we skip lumis
def DoAllPlotArrays(Rates, print_trigger, run_list, data_clean, meanxsec, num_ls, LumiPageInfo, SubSystemOff, max_dt, print_info, trig_list, do_fit, do_inst, debug_print, fitparams, fitparamsPS, L1SeedChangeFit, PSColslist, first_trigger):

    ###init arrays ###
    [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t] = MakePlotArrays()
    
    
    
    it_offset=0
    ###loop over each LS ###
    for iterator in range(len(Rates[print_trigger]["rate"])):
        if not Rates[print_trigger]["run"][iterator] in run_list:
            continue
        if not Rates[print_trigger]["psi"][iterator] in PSColslist:
            continue
                
        #else:
            #print iterator, Rates[print_trigger]["psi"][iterator], PSColslist
        ##Old Spike-killer: used average-xsec method, too clumsy, esp. for nonlinear triggers
        #prediction = meanxsec + slopexsec * (Rates[print_trigger]["live_lumi"][iterator] - meanlumi)
        #realvalue = Rates[print_trigger]["xsec"][iterator]

        ##New Spike-killer: gets average of nearest 4 LS
        try:
            if (iterator > 2 and iterator+2 < len(Rates[print_trigger]["rate"])): ##2 LS before, 2 after
                prediction = (Rates[print_trigger]["rate"][iterator-2]+Rates[print_trigger]["rate"][iterator-1]+Rates[print_trigger]["rate"][iterator+1]+Rates[print_trigger]["rate"][iterator+2])/4.0
            elif (iterator > 2 and len(Rates[print_trigger]["rate"]) > 4 ): ##4 LS before
                prediction = (Rates[print_trigger]["rate"][iterator-4]+Rates[print_trigger]["rate"][iterator-3]+Rates[print_trigger]["rate"][iterator-2]+Rates[print_trigger]["rate"][iterator-1])/4.0
            elif (iterator+2 < len(Rates[print_trigger]["rate"]) and len(Rates[print_trigger]["rate"]) > 4 ): ##4 LS after
                prediction = (Rates[print_trigger]["rate"][iterator+1]+Rates[print_trigger]["rate"][iterator+2]+Rates[print_trigger]["rate"][iterator+3]+Rates[print_trigger]["rate"][iterator+4])/4.0
            else:
                prediction = Rates[print_trigger]["rate"][iterator]
            realvalue = Rates[print_trigger]["rate"][iterator]
        except:
            print "Error calculating prediction. Setting rates to defaults."
            prediction = Rates[print_trigger]["rate"][iterator]
            realvalue = Rates[print_trigger]["rate"][iterator]
            
        if pass_cuts(data_clean, realvalue, prediction, meanxsec, Rates, print_trigger, iterator, num_ls,LumiPageInfo,SubSystemOff,max_dt,print_info, trig_list, first_trigger):
            run_t.append(Rates[print_trigger]["run"][iterator])
            ls_t.append(Rates[print_trigger]["ls"][iterator])
            ps_t.append(Rates[print_trigger]["ps"][iterator])
            inst_t.append(Rates[print_trigger]["inst_lumi"][iterator])
            live_t.append(Rates[print_trigger]["live_lumi"][iterator])
            delivered_t.append(Rates[print_trigger]["delivered_lumi"][iterator])
            deadtime_t.append(Rates[print_trigger]["deadtime"][iterator])
            rawrate_t.append(Rates[print_trigger]["rawrate"][iterator])
            rate_t.append(Rates[print_trigger]["rate"][iterator])
            rawxsec_t.append(Rates[print_trigger]["rawxsec"][iterator])
            xsec_t.append(Rates[print_trigger]["xsec"][iterator])
            psi_t.append(Rates[print_trigger]["psi"][iterator])
            
            e_run_t.append(0.0)
            e_ls_t.append(0.0)
            e_ps_t.append(0.0)
            e_inst_t.append(14.14)
            e_live_t.append(14.14)
            e_delivered_t.append(14.14)
            e_deadtime_t.append(0.01)
            e_rawrate_t.append(math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3)))
            e_rate_t.append(Rates[print_trigger]["ps"][iterator]*math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3)))
            e_psi_t.append(0.0)

            if live_t[-1] == 0:
                e_rawxsec_t.append(0)
                e_xsec_t.append(0)
            else:
                try: 
                    e_rawxsec_t.append(math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3))/Rates[print_trigger]["live_lumi"][iterator])
                    e_xsec_t.append(Rates[print_trigger]["ps"][iterator]*math.sqrt(Rates[print_trigger]["rawrate"][iterator]/(num_ls*23.3))/Rates[print_trigger]["live_lumi"][iterator])
                except:
                    e_rawxsec_t.append(0.)
                    e_xsec_t.append(0.)
                    
            if not do_fit:
                [FitType, X0, X1, X2, X3, sigma, X0err] = GetCorrectFitParams(fitparams,fitparamsPS,Rates,L1SeedChangeFit,iterator,print_trigger)
                if not do_inst:
                    if FitType == "expo":
                        rate_prediction = X0 + X1*math.exp(X2+X3*delivered_t[-1])
                    else:
                        rate_prediction = X0 + X1*delivered_t[-1] + X2*delivered_t[-1]*delivered_t[-1] + X3*delivered_t[-1]*delivered_t[-1]*delivered_t[-1]
                        
                else:
                    if FitType == "expo":
                        rate_prediction = X0 + X1*math.exp(X2+X3*inst_t[-1])
                    else:
                        rate_prediction = X0 + X1*inst_t[-1] + X2*inst_t[-1]*inst_t[-1] + X3*inst_t[-1]*inst_t[-1]*inst_t[-1]

                if rate_prediction != abs(rate_prediction):
                    rate_prediction = 0
                    print 'Problem calculating rate prediction.  Setting to 0 for '+print_trigger+': lumisection '+ls_t[-1]
                    
                if live_t[-1] == 0:
                    rawrate_fit_t.append(0)
                    rate_fit_t.append(0)
                    rawxsec_fit_t.append(0)
                    xsec_fit_t.append(0)
                    e_rawrate_fit_t.append(0)
                    e_rate_fit_t.append(sigma)
                    e_rawxsec_fit_t.append(0)
                    e_xsec_fit_t.append(0)

                else:
                    if ps_t[-1]>0.0:
                        rawrate_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/(ps_t[-1]))
                    else:
                        rawrate_fit_t.append(0.0)
                        
                    rate_fit_t.append(rate_prediction)                        
                    e_rate_fit_t.append(sigma*math.sqrt(rate_prediction))
                    rawxsec_fit_t.append(rawrate_fit_t[-1]/live_t[-1])
                    xsec_fit_t.append(rate_prediction*(1.0-deadtime_t[-1])/live_t[-1])
                    try:
                        e_rawrate_fit_t.append(sigma*math.sqrt(rate_fit_t[-1])*rawrate_fit_t[-1]/rate_fit_t[-1])
                        e_rawxsec_fit_t.append(sigma*math.sqrt(rate_fit_t[-1])*rawxsec_fit_t[-1]/rate_fit_t[-1])
                        e_xsec_fit_t.append(sigma*math.sqrt(rate_fit_t[-1])*xsec_fit_t[-1]/rate_fit_t[-1])
                    except:
                        print print_trigger, "has no fitted rate for LS", Rates[print_trigger]["ls"][iterator]
                        e_rawrate_fit_t.append(sigma)
                        e_rawxsec_fit_t.append(sigma)
                        e_xsec_fit_t.append(sigma)

                
            if (print_info and num_ls==1 and (fabs(rawrate_fit_t[-1]-rawrate_t[-1])>2.5*sqrt(sum(Rates[print_trigger]["rawrate"])/len(Rates[print_trigger]["rawrate"])))):
                    pass

        else: ##If the data point does not pass the data_clean filter
            if debug_print:
                print str(print_trigger)+" has xsec "+str(round(Rates[print_trigger]["xsec"][iterator],6))+" at lumi "+str(round(Rates[print_trigger]["live_lumi"][iterator],2))+" where the expected value is "+str(prediction)

    ## End "for iterator in range(len(Rates[print_trigger]["rate"])):" loop
    return [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t]           

def GetCorrectFitParams(fitparams,fitparamsPS,Rates,L1SeedChangeFit,iterator,print_trigger):
    if not L1SeedChangeFit:
        return fitparams
    else:
        psi=Rates[print_trigger]["psi"][iterator]
        [FitTypePS, X0PS, X1PS, X2PS, X3PS, sigmaPS, X0errPS]=fitparamsPS
        return [FitTypePS[psi], X0PS[psi], X1PS[psi], X2PS[psi], X3PS[psi], sigmaPS[psi], X0errPS[psi]]
#[FitType, X0, X1, X2, X3, sigma, X0err]


def CalcSigma(var_x, var_y, func, do_high_lumi):
    residuals = []
    residuals_high_lumi = []
    res_frac = []
    res_frac_high_lumi = []
    for x, y in zip(var_x,var_y):
        y_predicted = func.Eval(x,0,0)
        residuals.append(y - y_predicted)
        res_frac.append((y - y_predicted)/math.sqrt(abs(y_predicted))) #QUICK FIX, WE NEED TO DECIDE HOW TO HANDLE NEGATIVE
        if x > 6000:
            residuals_high_lumi.append(y - y_predicted)
            res_frac_high_lumi.append((y - y_predicted)/math.sqrt(abs(y_predicted)))

    res_squared = [i*i for i in residuals]
    res_frac_squared = [i*i for i in res_frac]
    res_high_lumi_squared = [i*i for i in residuals_high_lumi]
    res_frac_high_lumi_squared = [i*i for i in res_frac_high_lumi]
    dev_high_lumi_squared = [i*fabs(i) for i in residuals_high_lumi]
    dev_frac_high_lumi_squared = [i*fabs(i) for i in res_frac_high_lumi]
    
    if len(res_squared) > 2:
        sigma = math.sqrt(sum(res_squared)/(1.0*len(res_squared)-2.0))
        sigma_frac = math.sqrt(sum(res_frac_squared)/(1.0*len(res_frac_squared)-2.0))
    else:
        sigma = 0
        sigma_frac = 0

    if len(res_high_lumi_squared) > 10 and do_high_lumi:
        high_lumi_sigma_frac = math.sqrt(sum(res_frac_high_lumi_squared)/(1.0*len(res_frac_high_lumi_squared))) ##Statistics limited, don't subtract 2
        high_lumi_dev_frac = math.sqrt( fabs( sum(dev_frac_high_lumi_squared)/(1.0*len(dev_frac_high_lumi_squared)) ) ) ##Statistics limited, don't subtract 2
        if high_lumi_sigma_frac > 1.25*sigma_frac: 
            #print "high_lumi_sigma_frac is higher by "+str(100*round((high_lumi_sigma_frac/sigma_frac)-1,2))+"% than sigma_frac ("+str(round(sigma_frac,2))+")"
            sigma = sigma*( 0.5 + 0.5*(high_lumi_sigma_frac/sigma_frac) )
            sigma_frac = sigma_frac*( 0.5 + 0.5*(high_lumi_sigma_frac/sigma_frac) )
        if high_lumi_dev_frac > 4.0*math.sqrt(1.0/(1.0*len(res_frac_high_lumi_squared)-2.0))*sigma_frac:
            #print "Total points: "+str(len(res_frac_squared))
            #print "High lumi points: "+str(len(res_frac_high_lumi_squared))
            #print "high_lumi_dev_frac is "+str(100*round(high_lumi_dev_frac/sigma_frac,2))+"% of sigma_frac ("+str(round(sigma_frac,2))+")"
            sigma = sigma*(1.0 + 0.5*(high_lumi_dev_frac/sigma_frac) )
            sigma_frac = sigma_frac*(1.0 + 0.5*(high_lumi_dev_frac/sigma_frac) )
        
    return sigma_frac

def GetJSON(json_file):

    input_file = open(json_file)
    file_content = input_file.read()
    inputRange = selectionParser(file_content)
    JSON = inputRange.runsandls()
    return JSON
    ##JSON is an array: JSON[run_number] = [1st ls, 2nd ls, 3rd ls ... nth ls]

def MakePlotArrays():
    run_t = array.array('f')
    ls_t = array.array('f')
    ps_t = array.array('f')
    inst_t = array.array('f')
    live_t = array.array('f')
    delivered_t = array.array('f')
    deadtime_t = array.array('f')
    rawrate_t = array.array('f')
    rate_t = array.array('f')
    rawxsec_t = array.array('f')
    xsec_t = array.array('f')
    psi_t = array.array('f')
    
    e_run_t = array.array('f')
    e_ls_t = array.array('f')
    e_ps_t = array.array('f')
    e_inst_t = array.array('f')
    e_live_t = array.array('f')
    e_delivered_t = array.array('f')
    e_deadtime_t = array.array('f')
    e_rawrate_t = array.array('f')
    e_rate_t = array.array('f')
    e_rawxsec_t = array.array('f')
    e_xsec_t = array.array('f')
    e_psi_t = array.array('f')
    
    rawrate_fit_t = array.array('f')
    rate_fit_t = array.array('f')
    rawxsec_fit_t = array.array('f')
    xsec_fit_t = array.array('f')
    e_rawrate_fit_t = array.array('f')
    e_rate_fit_t = array.array('f')
    e_rawxsec_fit_t = array.array('f')
    e_xsec_fit_t = array.array('f')
    
    return [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t]


def GetVXVY(plot_properties, fit_file, AllPlotArrays, L1SeedChangeFit):

    VF = "0"
    VFE = "0"

    [run_t,ls_t,ps_t,inst_t,live_t,delivered_t,deadtime_t,rawrate_t,rate_t,rawxsec_t,xsec_t,psi_t,e_run_t,e_ls_t,e_ps_t,e_inst_t,e_live_t,e_delivered_t,e_deadtime_t,e_rawrate_t,e_rate_t,e_rawxsec_t,e_xsec_t,e_psi_t,rawrate_fit_t,rate_fit_t,rawxsec_fit_t,xsec_fit_t,e_rawrate_fit_t,e_rate_fit_t,e_rawxsec_fit_t,e_xsec_fit_t] = AllPlotArrays
    for varX, varY, do_fit, save_root, save_png, fit_file in plot_properties:
        if varX == "run":
            VX = run_t
            VXE = run_t_e
            x_label = "Run Number"
        elif varX == "ls":
            VX = ls_t
            VXE = e_ls_t
            x_label = "Lumisection"
        elif varX == "ps":
            VX = ps_t
            VXE = e_ps_t
            x_label = "Prescale"
        elif varX == "inst":
            VX = inst_t
            VXE = e_inst_t
            x_label = "Instantaneous Luminosity [10^{30} Hz/cm^{2}]"

        elif varX == "live":
            VX = live_t
            VXE = e_live_t
            x_label = "Instantaneous Luminosity [10^{30} Hz/cm^{2}]"            

        elif varX == "delivered":
            VX = delivered_t
            VXE = e_delivered_t
            x_label = "Instantaneous Luminosity [10^{30} Hz/cm^{2}]"                        

        elif varX == "deadtime":
            VX = deadtime_t
            VXE = e_deadtime_t
            x_label = "Deadtime"
        elif varX == "rawrate":
            VX = rawrate_t
            VXE = e_rawrate_t
            x_label = "Raw Rate [Hz]"
        elif varX == "rate":
            VX = rate_t
            VXE = e_rate_t
            x_label = "Rate [Hz]"
        elif varX == "rawxsec":
            VX = rawxsec_t
            VXE = e_rawxsec_t
            x_label = "Cross Section"
        elif varX == "xsec":
            VX = xsec_t
            VXE = e_xsec_t
            x_label = "Cross Section"            
        elif varX == "psi":
            VX = psi_t
            VXE = e_psi_t
            x_label = "Prescale Index"
        else:
            print "No valid variable entered for X"
            continue
        if varY == "run":
            VY = run_t
            VYE = run_t_e
            y_label = "Run Number"
        elif varY == "ls":
            VY = ls_t
            VYE = e_ls_t
            y_label = "Lumisection"
        elif varY == "ps":
            VY = ps_t
            VYE = e_ps_t
            y_label = "Prescale"
        elif varY == "inst":
            VY = inst_t
            VYE = e_inst_t
            y_label = "Instantaneous Luminosity"            
        elif varY == "live":
            VY = live_t
            VYE = e_live_t
            y_label = "Instantaneous Luminosity"                        
        elif varY == "delivered":
            VY = delivered_t
            VYE = e_delivered_t
            y_label = "Instantaneous Luminosity"                        
        elif varY == "deadtime":
            VY = deadtime_t
            VYE = e_deadtime_t
            y_label = "Deadtime"
        elif varY == "rawrate":
            VY = rawrate_t
            VYE = e_rawrate_t
            y_label = "Raw Rate [Hz]"
            if fit_file:
                VF = rawrate_fit_t
                VFE = e_rawrate_fit_t
        elif varY == "rate":
            VY = rate_t
            VYE = e_rate_t
            y_label = "Rate [Hz]"            
            if fit_file:
                VF = rate_fit_t
                VFE = e_rate_fit_t
        elif varY == "rawxsec":
            VY = rawxsec_t
            VYE = e_rawxsec_t
            y_label = "Cross Section"
            if fit_file:
                VF = rawxsec_fit_t
                VFE = e_rawxsec_fit_t
        elif varY == "xsec":
            VY = xsec_t
            VYE = e_xsec_t
            y_label = "Cross Section"            
            if fit_file:
                VF = xsec_fit_t
                VFE = e_xsec_fit_t
        elif varY == "psi":
            VY = psi_t
            VYE = e_psi_t
            y_label = "Prescale Index"
        else:
            print "No valid variable entered for Y"
            continue

    return [VX, VXE, x_label, VY, VYE, y_label, VF, VFE]

def pass_cuts(data_clean, realvalue, prediction, meanxsec, Rates, print_trigger, iterator, num_ls,LumiPageInfo,SubSystemOff, max_dt, print_info, trig_list, first_trigger):
    it_offset=0
    Passed=True
    subsystemfailed=[]
    
    if num_ls==1:
        ##fit is 2 ls ahead of real rate
        LS=Rates[print_trigger]["ls"][iterator]
        LSRange=LumiPageInfo[LS]["LSRange"]
        LS2=LSRange[-1]
        lumidict={}
        lumidict=LumiPageInfo[LS]
            
        if print_info:
            if (iterator==0 and print_trigger==trig_list[0] and first_trigger):
                print '%10s%10s%10s%10s%10s%10s%10s%15s%20s%15s' % ("Status", "Run", "LS", "Physics", "Active", "Deadtime", " MaxDeadTime", " Passed all subsystems?", " List of Subsystems", " Spike killing")
            
        ## if SubSystemOff["All"]:
##             for keys in LumiPageInfo[LS]:
##                 #print LS, keys, LumiPageInfo[LS][keys]
##                 if not LumiPageInfo[LS][keys]:
##                     Passed=False
##                     subsystemfailed.append(keys)
##                     break
##         else:
        if SubSystemOff["Mu"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["rpc"] and LumiPageInfo[LS]["dt0"] and LumiPageInfo[LS]["dtp"] and LumiPageInfo[LS]["dtm"] and LumiPageInfo[LS]["cscp"] and LumiPageInfo[LS]["cscm"]):
                Passed=False
                subsystemfailed.append("Mu")
        if SubSystemOff["HCal"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["hbhea"] and LumiPageInfo[LS]["hbheb"] and LumiPageInfo[LS]["hbhec"]):
                Passed=False
                subsystemfailed.append("HCal")
            if (SubSystemOff["EndCap"]  or SubSystemOff["All"]) and not (LumiPageInfo[LS]["hf"]):
                Passed=False
                subsystemfailed.append("HCal-EndCap")
        if SubSystemOff["ECal"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["ebp"] and LumiPageInfo[LS]["ebm"]):
                Passed=False
                subsystemfailed.append("ECal")
            if (SubSystemOff["EndCap"] or SubSystemOff["All"]) and not (LumiPageInfo[LS]["eep"] and LumiPageInfo[LS]["eem"] and LumiPageInfo[LS]["esp"] or LumiPageInfo[LS]["esm"]):
                Passed=False
                subsystemfailed.append("ECal-EndCap")
        if SubSystemOff["Tracker"] or SubSystemOff["All"]:
            if not (LumiPageInfo[LS]["tob"] and LumiPageInfo[LS]["tibtid"] and LumiPageInfo[LS]["bpix"] and LumiPageInfo[LS]["fpix"]):
                Passed=False
                subsystemfailed.append("Tracker")
            if (SubSystemOff["EndCap"] or SubSystemOff["All"]) and not (LumiPageInfo[LS]["tecp"] and LumiPageInfo[LS]["tecm"]):
                Passed=False
                subsystemfailed.append("Tracker-EndCap")
        if SubSystemOff["Beam"] or SubSystemOff["All"]:
            if not(LumiPageInfo[LS]["b1pres"] and LumiPageInfo[LS]["b2pres"] and LumiPageInfo[LS]["b1stab"] and LumiPageInfo[LS]["b2stab"]):
                Passed=False
                subsystemfailed.append("Beam")
    else:
        Passed=True
        
    if not data_clean or (        
        Rates[print_trigger]["physics"][iterator] == 1
        and Rates[print_trigger]["active"][iterator] == 1
        and Rates[print_trigger]["deadtime"][iterator] < max_dt
        #and Rates[print_trigger]["psi"][iterator] > 0
        and Passed
        and (realvalue >0.6*prediction and realvalue<1.5*prediction)
        and Rates[print_trigger]["rawrate"][iterator] > 0.04
        ):
        if (print_info and num_ls==1 and (realvalue <0.4*prediction or realvalue>2.5*prediction)):
            pass
            ##print '%-50s%10s%10s%10s%10s%10s%10s%10s%15s%20s' % (print_trigger,"Passed", Rates[print_trigger]["run"][iterator], LS, Rates[print_trigger]["physics"][iterator], Rates[print_trigger]["active"][iterator], round(Rates[print_trigger]["deadtime"][iterator],2), max_dt, Passed, subsystemfailed)
        return True
    else:
        if (print_info and print_trigger==trig_list[0] and num_ls==1 and first_trigger):
            prediction_match=True
            if (realvalue >0.6*prediction and realvalue<1.5*prediction):
                prediction_match=False
            print '%10s%10s%10s%10s%10s%10s%10s%15s%20s%15s' % ("Failed", Rates[print_trigger]["run"][iterator], LS, Rates[print_trigger]["physics"][iterator], Rates[print_trigger]["active"][iterator], round(Rates[print_trigger]["deadtime"][iterator],2), max_dt, Passed, subsystemfailed, prediction_match )
        
        return False


#### LumiRangeGreens ####    
####inputs: RefMoreLumiArray --dict with lumi page info in LS by LS blocks,
####        LRange           --list range over lumis,
####        nls              --number of lumisections
####        RefRunNum        --run number
####
####outputs RangeMoreLumi    --lumi page info in dict LSRange blocks with lumi, added items Run and LSRange
def LumiRangeGreens(RefMoreLumiArray,LSRange,nls,RefRunNum,deadtimebeamactive):
  
    RangeMoreLumi={}
    for keys,values in RefMoreLumiArray.iteritems():
        RangeMoreLumi[keys]=1
  
    for iterator in LSRange[nls]:
        for keys, values in RefMoreLumiArray.iteritems():
            if RefMoreLumiArray[keys][iterator]==0:
                RangeMoreLumi[keys]=0
    RangeMoreLumi['LSRange']=LSRange[nls]
    RangeMoreLumi['Run']=RefRunNum
    RangeMoreLumi['DeadTimeBeamActive']=deadtimebeamactive
    return RangeMoreLumi
                        
#### CheckLumis ####
####inputs: 
####        PageLumiInfo      --dict of LS with dict of some lumipage info
####        Rates            --dict of triggernames with dict of info
def checkLS(Rates, PageLumiInfo,trig_list):
    rateslumis=Rates[trig_list[-1]]["ls"]
    keys=PageLumiInfo.keys()
    print "lumi run=",PageLumiInfo[keys[-1]]["Run"]
    ll=0
    for ls in keys:
        print ls,rateslumis[ll]
        ll=ll+1
    return False


def checkL1seedChangeALLPScols(trig_list,HLTL1PS):
    
    nps=0
    HLTL1_seedchanges={}
    
    for HLTkey in trig_list:
        if HLTkey=='HLT_Stream_A':
            continue
        #print HLTkey
        if not HLTkey.startswith('HLT'):
            nps=9
            HLTL1_seedchanges[HLTkey]=[[0, 1, 2, 3, 4, 5, 6, 7, 8]]
            continue

        try:
            dict=HLTL1PS[StripVersion(HLTkey)]
            #print "dict=",dict
        except:
            print "%s appears in the trigger list but does not exist in the HLT menu and is being skipped." % (StripVersion(HLTkey),)
            continue
            
        HLTL1dummy={}
        for L1seed in dict.iterkeys():
            #print L1seed
            dummyL1seedlist=[]
            #print dict[L1seed]
            dummy=dict[L1seed]
            L1seedchangedummy=[]
            L1fulldummy=[]
            nps=len(dict[L1seed])
            #print "nps=",nps
            for PScol in range(0,len(dict[L1seed])):
                PScoldummy=PScol+1
                #print "PScoldummy=",PScoldummy
                if PScoldummy>(len(dict[L1seed])-1):
                    PScoldummy=len(dict[L1seed])-1
                    #print "changed PScoldummy=",PScoldummy
                #print PScol, PScoldummy, dummy[PScol]    
                
                if dummy[PScol]==dummy[PScoldummy]:
                    #print PScol, "same"
                    L1seedchangedummy.append(PScol)
                else:
                    #print PScol, PScoldummy, "diff", dummy[PScol], dummy[PScoldummy]
                    L1seedchangedummy.append(PScol)
                    for ps in L1seedchangedummy:
                        L1fulldummy.append(L1seedchangedummy)
                    #print "L1seed change ", L1seedchangedummy, "full=",L1fulldummy
                    L1seedchangedummy=[]
            for ps in L1seedchangedummy:        
                L1fulldummy.append(L1seedchangedummy)        
            #print "L1full=",L1fulldummy
            HLTL1dummy[L1seed]=L1fulldummy
        #print HLTL1dummy
        HLTL1_seedchanges[HLTkey]=commonL1PS(HLTL1dummy,nps)
        #print HLTkey, HLTL1_seedchanges[HLTkey]
    return HLTL1_seedchanges,nps
        
        
def commonL1PS(HLTL1dummy, nps):
### find commmon elements in L1 seeds
    HLTL1_seedchanges=[]
    for PScol in range(0,nps):
        
        L1seedslist=HLTL1dummy.keys()
        L1tupletmp=set(tuple(HLTL1dummy[L1seedslist.pop()][PScol]))        
        while len(L1seedslist)>0:
            L1tupletmp2=set(tuple(HLTL1dummy[L1seedslist.pop()][PScol]))
            L1tupletmp=L1tupletmp & L1tupletmp2
        if sorted(list(tuple(L1tupletmp))) not in HLTL1_seedchanges:       
            HLTL1_seedchanges.append(sorted(list(tuple(L1tupletmp))))    
        #print HLTL1_seedchanges
    return HLTL1_seedchanges

def Fitter(gr1, VX, VY, sloperate, nlow, Rates, print_trigger, first_trigger, varX, varY, lowrate):

    f1a = 0
    f1b = 0
    f1c = 0
    f1d = 0
    if "rate" in varY:
        f1d = TF1("f1d","pol1",0,8000)#linear
        f1d.SetParameters(0.01,min(sum(VY)/sum(VX),sloperate)) ##Set Y-intercept near 0, slope either mean_rate/mean_lumi or est. slope (may be negative)
        f1d.SetLineColor(4)
        f1d.SetLineWidth(2)
        if nlow>0:
            f1d.SetParLimits(0,0,1.5*lowrate/nlow) ##Keep Y-intercept in range of low-lumi rate points
        else:
            f1d.SetParLimits(0,0,1.5*sum(VY)/len(VY))
        if (sloperate > 0):
            if (sloperate > 0.5*sum(VY)/sum(VX)): ##Slope is substantially positive
                f1d.SetParLimits(1,min(0.5*sloperate,0.5*sum(VY)/sum(VX)),1.5*sum(VY)/sum(VX)) 
            else: ##Slope is somewhat positive or flat
                f1d.SetParLimits(1,-0.1*sloperate,1.5*sum(VY)/sum(VX))
        else: ##Slope is negative or flat 
            f1d.SetParLimits(1,1.5*sloperate,-0.1*sloperate)

        gr1.Fit("f1d","QN","rob=0.90")
        
        f1a = TF1("f1a","pol2",0,8000)#quadratic
        f1a.SetParameters(f1d.GetParameter(0),f1d.GetParameter(1),0) ##Initial values from linear fit
        f1a.SetLineColor(6)
        f1a.SetLineWidth(2)
        if nlow>0 and sloperate < 0.5*sum(VY)/sum(VX): ##Slope is not substantially positive
            f1a.SetParLimits(0,0,1.5*lowrate/nlow) ##Keep Y-intercept in range of low-lumi rate points
        else:
            f1a.SetParLimits(0,0,max(min(VY),0.3*sum(VY)/len(VY))) ##Keep Y-intercept reasonably low
        f1a.SetParLimits(1,-2.0*(max(VY)-min(VY))/(max(VX)-min(VX)),2.0*(max(VY)-min(VY))/(max(VX)-min(VX))) ##Reasonable bounds
        f1a.SetParLimits(2,-2.0*max(VY)/(max(VX)*max(VX)),2.0*max(VY)/(max(VX)*max(VX))) ##Reasonable bounds
        gr1.Fit("f1a","QN","rob=0.90")
        
        if True:
            f1b = TF1("f1b","pol3",0,8000)#cubic
            f1b.SetParameters(f1a.GetParameter(0),f1a.GetParameter(1),f1a.GetParameter(2),0) ##Initial values from quadratic fit
            f1b.SetLineColor(2)
            f1b.SetLineWidth(2)
            f1b.SetParLimits(0,0,max(min(VY),0.3*sum(VY)/len(VY))) ##Keep Y-intercept reasonably low
            f1b.SetParLimits(1,-2.0*(max(VY)-min(VY))/(max(VX)-min(VX)),2.0*(max(VY)-min(VY))/(max(VX)-min(VX))) ##Reasonable bounds
            f1b.SetParLimits(2,-2.0*max(VY)/(max(VX)*max(VX)),2.0*max(VY)/(max(VX)*max(VX))) ##Reasonable bounds
            f1b.SetParLimits(3,0,2.0*max(VY)/(max(VX)*max(VX)*max(VX))) ##Reasonable bounds
            gr1.Fit("f1b","QN","rob=0.90")
            
            f1c = TF1("f1c","[0]+[1]*expo(2)",0,8000)
            f1c.SetLineColor(3)
            f1c.SetLineWidth(2)
            #f1c.SetParLimits(0,0,max(min(VY),0.3*sum(VY)/len(VY)))
            f1c.SetParLimits(0,0,max(min(VY),0.01*sum(VY)/len(VY))) ##Exponential fits should start low
            f1c.SetParLimits(1,max(VY)/math.exp(15.0),max(VY)/math.exp(2.0))
            f1c.SetParLimits(2,0.0,0.0000000001)
            f1c.SetParLimits(3,2.0/max(VX),15.0/max(VX))
            gr1.Fit("f1c","QN","rob=0.90")
            ##Some fits are so exponential, the graph ends early and returns a false low Chi2 value

        else: ##If this is not a rate plot
            f1a = TF1("f1a","pol1",0,8000)
            f1a.SetLineColor(4)
            f1a.SetLineWidth(2)
            if "xsec" in varY:
                f1a.SetParLimits(0,0,meanxsec*1.5)
                if slopexsec > 0:
                    f1a.SetParLimits(1,0,max(VY)/max(VX))
                else:
                    f1a.SetParLimits(1,2*slopexsec,-2*slopexsec)
            else:
                f1a.SetParLimits(0,-1000,1000)
            gr1.Fit("f1a","Q","rob=0.80")

            if (first_trigger):
                print '%-50s %4s  x0             x1                    x2                    x3                   chi2     ndf chi2/ndf' % ('trigger', 'type')
                first_trigger=False
            try:
                print '%-50s | line | % .2f | +/-%.2f |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   % .2e | +/-%.1e |   %7.0f |   %4.0f |   %5.2f | ' % (print_trigger, f1a.GetParameter(0), f1a.GetParError(0), f1a.GetParameter(1), f1a.GetParError(1), 0                  , 0                 , 0                  , 0                 , f1a.GetChisquare(), f1a.GetNDF(), f1a_GetChisquare()/f1a.GetNDF())
            except:
                pass

    return [f1a,f1b,f1c,f1d,first_trigger]

def more_fit_info(f1a,f1b,f1c,f1d,VX,VY,print_trigger,Rates):

    meanps = median(Rates[print_trigger]["ps"])
    av_rte = mean(VY)
    passed=1
    #except ZeroDivisionError:
    try:
        f1a_Chi2 = f1a.GetChisquare()/f1a.GetNDF()
        f1b_Chi2 = f1b.GetChisquare()/f1b.GetNDF()
        f1c_Chi2 = f1c.GetChisquare()/f1c.GetNDF()
        f1d_Chi2 = f1d.GetChisquare()/f1d.GetNDF()
    except ZeroDivisionError:
        print "Zero DOF for", print_trigger
        passed=0
    f1a_BadMinimum = (f1a.GetMinimumX(5,7905,10)>2000 and f1a.GetMinimumX(5,7905,10)<7000) ##Don't allow minimum between 2000 and 7000
    f1b_BadMinimum = (f1b.GetMinimumX(5,7905,10)>2000 and f1b.GetMinimumX(5,7905,10)<7000)                
    f1c_BadMinimum = ((f1c.GetMinimumX(5,7905,10)>2000 and f1c.GetMinimumX(5,7905,10)<7000)) or f1c.GetMaximum(min(VX),max(VX),10)/max(VY) > 2.0

    return [f1a_Chi2, f1b_Chi2, f1c_Chi2,f1d_Chi2, f1a_BadMinimum, f1b_BadMinimum, f1c_BadMinimum, meanps, av_rte, passed]
    
def output_fit_info(do_fit,f1a,f1b,f1c,f1d,varX,varY,VX,VY,linear,print_trigger,first_trigger,Rates,width,chioffset,wp_bool,num_ls,meanrawrate,OutputFit, failed_paths, PSColslist, dummyPSColslist):
    [f1a_Chi2, f1b_Chi2, f1c_Chi2,f1d_Chi2, f1a_BadMinimum, f1b_BadMinimum, f1c_BadMinimum, meanps, av_rte,passed]=more_fit_info(f1a,f1b,f1c,f1d,VX,VY,print_trigger,Rates)
    OutputFit[print_trigger] = {}

    if not do_fit:
        failure_comment= "Can't have save_fits = True and do_fit = False"
        [OutputFit,first_trigger]
        failed_paths.append([print_trigger+str(PSColslist),failure_comment])
        OutputFit[print_trigger] = ["fit failed",failure_comment]
        return [OutputFit,first_trigger]
    if min([f1a_Chi2,f1b_Chi2,f1c_Chi2,f1d_Chi2]) > 500:#require a minimum chi^2/nDOF of 500
        failure_comment = "There were events for these paths in the runs specified during the creation of the fit file, but the fit failed to converge"
        failed_paths.append([print_trigger+str(PSColslist),failure_comment])
        OutputFit[print_trigger] = ["fit failed",failure_comment]
        return [OutputFit,first_trigger]
    if "rate" in varY and not linear:
        if first_trigger:
            print '\n%-*s | TYPE | %-8s | %-11s |  %-7s | %-10s |  %-7s | %-10s | %-8s | %-10s | %-6s | %-4s |%-7s| %-6s |' % (width,"TRIGGER", "X0","X0 ERROR","X1","X1 ERROR","X2","X2 ERROR","X3","X3 ERROR","CHI^2","DOF","CHI2/DOF","PScols")
            first_trigger = False
        if ((f1c_Chi2 < (f1a_Chi2*chioffset) or f1a_BadMinimum) and ((f1c_Chi2 < f1b_Chi2) or f1b_BadMinimum) and f1c_Chi2 < (f1d_Chi2*chioffset) and not f1c_BadMinimum and len(VX)>1):
            graph_fit_type="expo"
            [f1c,OutputFit]=graph_output_info(f1c,graph_fit_type,print_trigger,width,num_ls,VX,VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist)
            priot(wp_bool,print_trigger,meanps,f1d,f1c,graph_fit_type,av_rte)
        elif ((f1b_Chi2 < (f1a_Chi2*chioffset) or f1a_BadMinimum) and f1b_Chi2 < (f1d_Chi2*chioffset) and not f1b_BadMinimum and len(VX)>1):
            graph_fit_type="cube"
            [f1b,OutputFit]=graph_output_info(f1b,graph_fit_type,print_trigger,width,num_ls,VX,VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist)
            priot(wp_bool,print_trigger,meanps,f1d,f1b,graph_fit_type,av_rte)
        elif (f1a_Chi2 < (f1d_Chi2*chioffset)):
            graph_fit_type="quad"
            [f1a,OutputFit]=graph_output_info(f1a,graph_fit_type,print_trigger,width,num_ls,VX,VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist)
            priot(wp_bool,print_trigger,meanps,f1d,f1a,graph_fit_type,av_rte)
        else:
            graph_fit_type="line"
            [f1d,OutputFit]=graph_output_info(f1d,graph_fit_type,print_trigger,width,num_ls,VX,VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist)
            priot(wp_bool,print_trigger,meanps,f1d,f1d,graph_fit_type,av_rte)
    elif "rate" in varY and linear:
        if first_trigger:
            print '\n%-*s | TYPE | %-8s | %-11s |  %-7s | %-10s |  %-7s | %-10s | %-8s | %-10s | %-6s | %-4s |%-7s| %-6s |' % (width,"TRIGGER", "X0","X0 ERROR","X1","X1 ERROR","X2","X2 ERROR","X3","X3 ERROR","CHI^2","DOF","CHI2/DOF","PScols")
            first_trigger = False        
        graph_fit_type="line"
        [f1d,OutputFit]=graph_output_info(f1d,graph_fit_type,print_trigger,width,num_ls,VX,VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist)
        priot(wp_bool,print_trigger,meanps,f1d,f1d,graph_fit_type,av_rte)            
    else:
        graph_fit_type="quad"
        [f1a,OutputFit]=graph_output_info(f1a,graph_fit_type,print_trigger,width,num_ls,VX,VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist)
        #priot(wp_bool,print_trigger,meanps,f1d,f1a,"quad",av_rte)
        
    return [OutputFit,first_trigger, failed_paths]

def graph_output_info(graph1,graph_fit_type,print_trigger,width,num_ls,VX, VY,meanrawrate,OutputFit,PSColslist,dummyPSColslist):
    PSlist=deque(PSColslist)
    PSmin=PSlist.popleft()
    if not PSlist:
        PSmax=PSmin
    else:
        PSmax=PSlist.pop()
    
    print '%-*s | %s | %-8.1f | +/-%-8.1f | %8.1e | +/-%.1e | %8.1e | +/-%.1e | %-8.1e | +/-%.1e | %6.0f | %4.0f | %5.2f | %d-%d' % (width,print_trigger, graph_fit_type,graph1.GetParameter(0) , graph1.GetParError(0) , graph1.GetParameter(1) , graph1.GetParError(1) , graph1.GetParameter(2), graph1.GetParError(2) ,graph1.GetParameter(3), graph1.GetParError(3) ,graph1.GetChisquare() , graph1.GetNDF() , graph1.GetChisquare()/graph1.GetNDF(), PSmin, PSmax)
    graph1.SetLineColor(1)                    
    #priot(wp_bool,print_trigger,meanps,f1d,f1c,"expo",av_rte)
    do_high_lumi = print_trigger.startswith('HLT_') and ((len(dummyPSColslist)==1 or ( max(PSColslist)>=5 and min(PSColslist)==3) ))
    sigma = CalcSigma(VX, VY, graph1, do_high_lumi)*math.sqrt(num_ls)
    OutputFit[print_trigger] = [graph_fit_type, graph1.GetParameter(0) , graph1.GetParameter(1) , graph1.GetParameter(2) ,graph1.GetParameter(3) , sigma , meanrawrate, graph1.GetParError(0) , graph1.GetParError(1) , graph1.GetParError(2) , graph1.GetParError(3)]
        
    return [graph1,OutputFit]

def DrawFittedCurve(f1a, f1b,f1c, f1d, chioffset,do_fit,c1,VX,VY,print_trigger,Rates):
    [f1a_Chi2, f1b_Chi2, f1c_Chi2,f1d_Chi2, f1a_BadMinimum, f1b_BadMinimum, f1c_BadMinimum, meanps, av_rte, passed]=more_fit_info(f1a,f1b,f1c,f1d,VX,VY,print_trigger,Rates)
    
                    
    if do_fit:
        try:
            if ((f1c_Chi2 < (f1a_Chi2*chioffset) or f1a_BadMinimum ) and (f1c_Chi2 < f1b_Chi2 or f1b_BadMinimum ) and not f1c_BadMinimum ):
                f1c.Draw("same")
            elif ( (f1b_Chi2 < (f1a_Chi2*chioffset) or f1a_BadMinimum) and not f1b_BadMinimum):
                f1b.Draw("same")
            else:
                f1a.Draw("same")
                
                f1d.Draw("same")
        except:
            True

    c1.Update()
    
    return c1    

def EndMkrootfile(failed_paths, save_fits, save_root, fit_file, RootFile, OutputFit,OutputFitPS,L1SeedChangeFit):
             
    if len(failed_paths) > 0:
        if save_fits:
            print "\n***************NO FIT RECORDED FOR THE FOLLOWING PATHS***************"
        else:
            print "\n***************THE FOLLOWING PATHS HAVE BEEN SKIPPED BECAUSE THE FIT WAS MISSING***************"        
        sorted_failed_paths = sorted(failed_paths, key=itemgetter(1))
        for error_comment, entries in groupby(sorted_failed_paths, key=itemgetter(1)):
            print '\n'+error_comment+':'
            if 'not enough datapoints' in error_comment:
                print "(For a given trigger, if a group of PS columns has been skipped, the fit to all PS columns will be used in that region.)"
            for entry in entries:
                print entry[0]

    if save_root:
        print "\nOutput root file is "+str(RootFile)
    #print "DONE:",OutputFit    
    if save_fits:
        if os.path.exists(fit_file):
            os.remove(fit_file)
        FitOutputFile = open(fit_file, 'wb')
        pickle.dump(OutputFit, FitOutputFile, 2)
        FitOutputFile.close()
        print "Output fit file is "+str(fit_file)
    if save_fits and L1SeedChangeFit:
        PSfitfile=fit_file.replace("HLT_NoV","HLT_NoV_ByPS")
        print "A corresponding PS fit file has been saved."
        if os.path.exists(PSfitfile):
            os.remove(PSfitfile)
        FitOutputFilePS= open(PSfitfile, 'wb')
        pickle.dump(OutputFitPS,FitOutputFilePS,2)
        FitOutputFilePS.close()

##### NEED BETTER gr1 def for failure#####
def DefineGraphs(print_trigger,OutputFit,do_fit,varX,varY,x_label,y_label,VX,VY,VXE,VYE,VF,VFE,fit_file, failed_paths,PSColslist):
    passed=1
    try:
        gr1 = TGraphErrors(len(VX), VX, VY, VXE, VYE)
        
    except:
        failure_comment = "In runs specified during creation of the fit file, there were no events for this path: probably due to high deadtime or low raw (prescaled) rate"
        failed_paths.append([print_trigger,failure_comment])
        if do_fit:
            OutputFit[print_trigger] = ["fit failed",failure_comment]
            #gr1 = TGraphErrors(1, VX, VY, VXE, VYE)
            #gr3 = TGraphErrors(1, VX, VF, VXE, VFE)
            ###replaces continue in main fucntion
            passed=0
            return [OutputFit,0, 0, failed_paths, passed]
    try:
        if not do_fit:
            gr3 = TGraphErrors(len(VX), VX, VF, VXE, VFE)
        else:
            ##fake defn (will not be used)
            gr3 =TGraphErrors(len(VX), VX, VY, VXE, VYE)
    except:
        print "gr3 failed to define!"
        
        exit(2)
        
    
    if not do_fit:    
        gr3.SetMarkerStyle(8)
        gr3.SetMarkerSize(0.4)
        gr3.SetMarkerColor(4)
        gr3.SetFillColor(4)
        gr3.SetFillStyle(3003)
    
        
    if (len(VX)<10 and do_fit):
        failure_comment = "In runs specified during creation of the fit file, there were not enough datapoints for these paths (probably due to high deadtime or low raw (prescaled) rate)"
        failed_paths.append([print_trigger+" PS columns: "+str(PSColslist),failure_comment])
        OutputFit[print_trigger] = ["fit failed",failure_comment]
        gr1 = TGraphErrors(1, VX, VY, VXE, VYE)
        ###replaces continue in main fucntion
        passed=0
        return [OutputFit,gr1, gr3,failed_paths, passed]
        
    gr1.SetName("Graph_"+str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX))
    gr1.GetXaxis().SetTitle(x_label)
    gr1.GetYaxis().SetTitle(y_label)
    gr1.SetTitle(str(print_trigger))
    gr1.SetMinimum(0)
    gr1.SetMaximum(1.2*max(VY))
    #gr1.GetXaxis().SetLimits(min(VX)-0.2*max(VX),1.2*max(VX))
    gr1.GetXaxis().SetLimits(0,1.2*max(VX))
    gr1.SetMarkerStyle(8)
    
    if fit_file:
        gr1.SetMarkerSize(0.8)
    else:
        gr1.SetMarkerSize(0.5)
    gr1.SetMarkerColor(2)
    

    return [OutputFit,gr1, gr3, failed_paths, passed]

def DrawSave(save_root, save_png, var, varY, print_trigger, do_fit, gr1, gr3, chioffset, f1a, f1b, f1c, f1d, RootFile):    
    if save_root or save_png:
        c1 = TCanvas(str(varX),str(varY))
        c1.SetName(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX))
    gr1.Draw("APZ")    
    if not do_fit:
        gr3.Draw("P3")
        c1.Update()
    else:    
        c1=DrawFittedCurve(f1a, f1b, f1c, f1d, chioffset,do_fit,c1)
        
    if save_root:
        myfile = TFile( RootFile, 'UPDATE' )
        c1.Write()
        myfile.Close()
    if save_png:
        c1.SaveAs(str(print_trigger)+"_"+str(varY)+"_vs_"+str(varX)+".png")
            
    
if __name__=='__main__':
    global thisyear
    main()
