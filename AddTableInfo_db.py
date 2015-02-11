import sys
from colors import *
from DatabaseParser import *
from termcolor import colored, cprint
from StreamMonitor import *
import time


write = sys.stdout.write

NHighStreamA = 0
NHighExpress = 0

def MoreTableInfo(parser,LumiRange,config,isCol=True):
    global NHighStreamA
    global NHighExpress
    print "Monitoring Run %d" % (parser.RunNumber,)
    localtime = time.asctime( time.localtime(time.time()) )
    print "Local current time :", localtime
    #print "Lumisections used=", LumiRange
    if len(LumiRange)>0:
        
        [AvInstLumi, AvLiveLumi, AvDeliveredLumi, AvDeadTime,PSCols] = parser.GetAvLumiInfo(LumiRange)
        deadtimebeamactive=parser.GetDeadTimeBeamActive(LumiRange)*100
        
        ##print "dtba=",deadtimebeamactive
    else:
        print "no lumisections to monitor"
        return
  ## check if lumi is being filled
    if parser.LastLSParsed > 4 and isCol:
        if set(parser.InstLumiByLS.values()) == set([None]):
            write(colored("\n\nLUMI INFORMATION NOT BEING SENT!\n",'red',attrs=['reverse']))
            write(colored("Check with Shift Leader if this is expected\n",'red',attrs=['reverse']))
            write(colored("If not, HFLUMI needs to be red-recycled\n\n\n",'red',attrs=['reverse']))
            write(colored("If in doubt, call Lumi DOC\n\n\n",'red',attrs=['reverse']))
                                                                                                                                                                                                                                                                    
    try:
        lograte=parser.GetTriggerRatesByLS("HLT_LogMonitor_v3")
        if not len(lograte):
            lograte=parser.GetTriggerRatesByLS("HLT_LogMonitor_v4")

        for ls in LumiRange: 
            current_lograte = lograte.get(ls,0)
            lograte_sum =+ current_lograte

        lograte_average = lograte_sum/len(LumiRange)
        if lograte_average > config.MaxLogMonRate:
            write(bcolors.WARNING)
            print "Post to elog. LogMonitor rate is high: %.2f" % (lograte_average)
            write(bcolors.ENDC+"\n")              

    except:
        write(bcolors.WARNING)
        print "problem getting log monitor rates"
        write(bcolors.ENDC+"\n")

    try:
        LastPSCol = PSCols[-1]
    except:
        LastPSCol = -1
    
    expressRates = {}
    if isCol:
        expressRates = parser.GetTriggerRatesByLS("ExpressOutput")
    else:
        if len(parser.GetTriggerRatesByLS("ExpressOutput"))>0:
            expressRates=parser.GetTriggerRatesByLS("ExpressOutput")
        else:
            expressRates = parser.GetTriggerRatesByLS("ExpressForCosmicsOutput")

    ExpRate=0
    PeakRate=0
    AvgExpRate=0
    
    if len(expressRates.values()) > 20:
        AvgExpRate = sum(expressRates.values())/len(expressRates.values())
    counter=0    

    for ls in LumiRange:  ## Find the sum and peak express stream rates
        thisR = expressRates.get(ls,0)
        ExpRate+=thisR
        if thisR>PeakRate:
            PeakRate=thisR


    ## Print Stream A Rate --moved see below
    ##print "Current Steam A Rate is: %0.1f Hz" % (ARate/len(LumiRange),)

    Warn = False

    ##########################################
    ## Check if the express stream is too high or low
    ##########################################
    badExpress = ((ExpRate/len(LumiRange) > config.MaxExpressRate) or (ExpRate/len(LumiRange)<0.1 and isCol)) ## avg express stream rate too high?
    baseText = "\nCurrent Express Stream rate is: %0.1f Hz" % (ExpRate/len(LumiRange),) ## text to display
    if badExpress:
        text = colored(baseText,'red',attrs=['reverse'])  ## bad, make the text white on red
        NHighExpress+=1  ## increment the bad express counter
    else:
        text = baseText 
        NHighExpress=0
        
    write(text)
    if badExpress:
        if len(LumiRange)>1:
            if (ExpRate-PeakRate)/(len(LumiRange)-1) <=config.MaxExpressRate: ## one lumisection causes this
                write("  <<  This appears to be due to a 1 lumisection spike, please monitor\n")
            else:
                if NHighExpress > 1:  # big problem, call HLT DOC
                    write(colored("  <<  WARNING: Current Express rate is too high!",'red',attrs=['reverse']) )
                    Warn = True

                #    if AvgExpRate > config.MaxExpressRate:
                #        write( colored("\n\nWARNING: Average Express Stream Rate is too high (%0.1f Hz)  << CALL HLT DOC" % AvgExpRate,'red',attrs=['reverse']) )
                #        Warn = True
        
            


    #########################################
    ##Check if Stream A is too high
    #########################################
    global NHighStreamA
    stream_mon = StreamMonitor()
    core_a_rates = stream_mon.getStreamACoreRatesByLS(parser,LumiRange,config,isCol).values()
    a_rates = stream_mon.getStreamARatesByLS(parser,LumiRange).values()
    peak_core_a_rate = max(core_a_rates)

    if len(LumiRange) > 0:
        avg_core_a_rate = sum(core_a_rates)/len(LumiRange)
        avg_a_rate = sum(a_rates)/len(LumiRange)
        badStreamA = stream_mon.compareStreamARate(config, avg_core_a_rate, LumiRange,AvInstLumi,isCol)

        baseTextA= "\nCurrent Stream A Rate is: %0.1f Hz" % (avg_a_rate)
        baseTextRealA= "\nCurrent PROMPT Stream A Rate is: %0.1f Hz" % (avg_core_a_rate)

        if badStreamA:
            textA=colored(baseTextA,'red',attrs=['reverse'])  ## bad, make the text white on red
            textRealA=colored(baseTextRealA,'red',attrs=['reverse'])  ## bad, make the text white on red
            NHighStreamA+=1
        else:
            textA=baseTextA
            textRealA=baseTextRealA

        write(textA)
        write(textRealA)
    
        if badStreamA and len(LumiRange) > 1:
            trimmed_core_a_rates = core_a_rates
            trimmed_core_a_rates.remove(peak_core_a_rate)
            if sum(trimmed_core_a_rates)/(len(LumiRange)-1) <= config.MaxStreamARate: ## one lumisection causes this
                write("  <<  This appears to be due to a 1 lumisection spike, please monitor\n")
            else:
                if NHighStreamA > 1: ##Call HLT doc!
                    write(colored("  <<  WARNING: Current Stream A rate is too high!",'red',attrs=['reverse']) )
                    Warn = True
    write("\n\n")
            
    ######################################
    ##Warning for HLT doc
    ######################################
    if Warn:  ## WARNING
        rows, columns = os.popen('stty size', 'r').read().split()  ## Get the terminal size
        cols = int(columns)
        write( colored("*"*cols+"\n",'red',attrs=['reverse','blink']) )
        line = "*" + " "*int((cols-22)/2)+"CALL HLT DOC (165575)"+" "*int((cols-23)/2)+"*\n"

        write( colored(line,'red',attrs=['reverse','blink']) )
        write( colored("*"*cols+"\n",'red',attrs=['reverse','blink']) )
        
    
    PrescaleColumnString=''
    PSCols = list(set(PSCols))
    for c in PSCols:
        PrescaleColumnString = PrescaleColumnString + str(c) + ","

    if isCol:
        write("The average instantaneous lumi of these lumisections is: ")
        write(str(round(AvInstLumi,1))+"e30\n")
        write("The delivered lumi of these lumi sections is:            ")
        write(str(round(len(LumiRange)*AvDeliveredLumi,1))+"e30"+"\n")
        write("The live (recorded) lumi of these lumi sections is:      ")
        write(str(round(len(LumiRange)*AvLiveLumi,1))+"e30\n\n")
        write("The average deadtime of these lumi sections is:          ")
        if deadtimebeamactive > 5:
            write(bcolors.FAIL)
        elif deadtimebeamactive > 10:
            write(bcolors.WARNING)
        else:
            write(bcolors.OKBLUE)
        write(str(round(deadtimebeamactive,2))+"%")
        write(bcolors.ENDC+"\n")
    write("Used prescale column(s): %s  " % (str(PrescaleColumnString),) )
    if LastPSCol in config.ForbiddenCols and isCol:
        write( colored("<< Using column %d! Please check in the documentation that this is the correct column" % (LastPSCol),'red',attrs=['reverse']) )
    write("\nLumisections: ")
    if not isSequential(LumiRange):
        write(str(LumiRange)+"   Lumisections are not sequential (bad LS skipped)\n")
    else:
        write("%d - %d\n" % (min(LumiRange),max(LumiRange),))
    ##print "\nLast Lumisection of the run is:        "+str(parser.GetLastLS())
    write(  "\nLast Lumisection good where DAQ is active is:  "+str(parser.GetLastLS(isCol)) )
    ##write(  "Last Lumisection where DAQ is active is:  "+str(parser.GetLastLS(True)) )
    write("\n\n\n")

    ## if isCol:
##         L1RatePredictions = config.GetExpectedL1Rates(AvInstLumi)
##         if len(L1RatePredictions):
##             print "Expected Level 1 Rates:"
##         for key,val in L1RatePredictions.iteritems():
##             write("Prescale Column "+str(key)+":  "+str(round(val/1000,1))+" kHz")
##             if key == LastPSCol:
##                 write(' << taking data in this column')
##             write('\n')
        
    

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
