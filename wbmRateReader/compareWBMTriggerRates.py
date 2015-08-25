import os
import argparse

from cernSSOWebParser import parseURLTables

def getPSAndInstLumis(runnr):
    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/LumiSections?RUN=%s" % runnr 
    tables=parseURLTables(url)

    psAndInstLumis={}
    
    for line in tables[0]:
        offset=0
        if line[0]=="L S": offset=41
        
        lumiSec=int(line[0+offset])
        preScaleColumn=int(line[1+offset])
        instLumi=float(line[3+offset])
        psAndInstLumis[lumiSec]=(preScaleColumn,instLumi)
    return psAndInstLumis


def getAveInstLumi(psAndInstLumis,minLS,maxLS):
    lumiSum=0.;
    nrLumis=0;
    if maxLS==-1: maxLS=max(psAndInstLumis.keys())
    for lumi in range(minLS,maxLS+1):
        if lumi in psAndInstLumis:
            nrLumis+=1
            lumiSum+=psAndInstLumis[lumi][1]
    if nrLumis!=0: return lumiSum/nrLumis
    else: return 0


def getTriggerRates(runnr,minLS,maxLS):
    url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/HLTSummary?fromLS=%s&toLS=%s&RUN=%s" % (minLS,maxLS,runnr)
    tables=parseURLTables(url)


    hltRates={}
    for line in tables[1][2:]:
        rates=[]
#        print line
        for entry in line[3:7]:
            rates.append(float(entry.replace(",","")))
                        
        hltRates[line[1].split("_v")[0]]=rates
        
    return hltRates

def getSteamRates(steamFile):
    data={}
    import csv
    with open(steamFile) as csvfile:
        steamReader=csv.reader(csvfile)
        for line in steamReader:
            path = line[0].split("_v")[0]

            if path.find("HLT_")!=-1:
                try:
                    rate = float(line[51])
                    rateErr = float(line[53])
                except:
                    #print path,line[51],line[53]
                    rate -1
                    rateErr = -1

                data[path]=(rate,rateErr)
    return data
           
                        
         

parser = argparse.ArgumentParser(description='compare hlt reports')

parser.add_argument('runnr',help='runnr')
parser.add_argument('--minLS',help='minimum LS (inclusive)',default=1,type=int)
parser.add_argument('--maxLS',help='maximum LS (inclusive)',default=-1,type=int)
parser.add_argument('--targetLumi',help='lumi to scale to (units of 1E30, so 7E33 is 7000)',default=-1.0,type=float)
parser.add_argument('--steamRates',help='csv steam rate google doc',default="")
args = parser.parse_args()

steamRates=getSteamRates(args.steamRates)


psAndInstLumis=getPSAndInstLumis(args.runnr)
aveLumi=getAveInstLumi(psAndInstLumis,args.minLS,args.maxLS)
#print aveLumi

lumiScale=1.
if args.targetLumi!=-1: lumiScale=args.targetLumi/float(aveLumi)

#print aveLumi,lumiScale

hltRates=getTriggerRates(args.runnr,args.minLS,args.maxLS)

spreadSheetHeader="Path,,Data Rate (Hz),,,Data Rate scaled (Hz),,,Steam Rate (Hz),,,Data - Steam (Hz),,,(Data - Steam)/Steam"
spreadSheetStr="%s,%f,+/-,%f,%f,+/-,%f,%f,+/-,%f,%f,+/-,%f,%f,+/-,%f" 

print spreadSheetHeader
for path in hltRates:
    rates=hltRates[path]
   # print rates
    import math
    rate =rates[3]
    rateErr=0
    if rates[2]!=0: rateErr=math.sqrt(rates[2])/rates[2]*rate
    rateScaled=rates[3]*lumiScale
    rateScaledErr=rateErr*lumiScale
    rateUnprescaledScaled=0
    rateUnprescaledScaledErr=0
    if rates[1]!=0:
        rateUnprescaledScaled=rates[3]*rates[0]/rates[1]*lumiScale
        rateUnprescaledScaledErr=rateErr*rates[0]/rates[1]*lumiScale

    prescaledPath=False
    if rates[1]!=0 and rates[1]!=rates[0]: prescaledPath=True

    steamRate=0
    steamRateErr=0
    if path in steamRates:
        steamRate=steamRates[path][0]
        steamRateErr=steamRates[path][1]

    rateDiff = rateScaled-steamRate
    rateDiffErr = math.sqrt(rateScaledErr**2 + steamRateErr**2)

    relDiff = 999
    relDiffErr = 0
    if steamRate!=0:
        relDiff = rateDiff/steamRate
        relDiffErr = rateScaledErr**2/steamRate**2 + rateScaled**2*steamRateErr**2/steamRate**4
    
   # print "%s : rate %f rate unprescaled %f steam rate %f +/- %f" % (path,rateScaled,rateUnprescaledScaled,steamRate,steamRateErr)


    if not prescaledPath:
        print spreadSheetStr %(path,rate,rateErr,rateScaled,rateScaledErr,steamRate,steamRateErr,rateDiff,rateDiffErr,relDiff,relDiffErr)
    
