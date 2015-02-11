#!/usr/bin/env python
import os
import cPickle as pickle
import math
from DatabaseParser import *

class RateMonConfig:
    
    def __init__(self,path='./'):
        self.CFGfile=path+"/defaults.cfg"
        self.BasePath=path
        self.ReferenceRun=""
        self.DefAllowRatePercDiff=0.0
        self.DefAllowRateSigmaDiff=0.0
        self.DefAllowIgnoreThresh=0.0
        self.ExcludeList=[]
        self.MonitorList=[]
        self.MonitorIntercept=[]
        self.MonitorSlope=[]
        self.MonitorQuad=[]
        self.L1Predictions=[]
        self.AllTriggers=0
        self.MonTargetLumi=0
        self.LSWindow=-1
        self.CompareReference=0
        self.ShifterMode=0
        self.NoVersion=0
        self.MaxExpressRate=999
        self.ForbiddenCols=[]
        self.CirculatingBeamsColumn=9
        self.MaxLogMonRate=10
        self.DefWarnOnSigmaDiff=1
        self.DefShowSigmaAndPercDiff=0
        self.DoL1=0
        self.DefaultMaxBadRatesToShow=500
        self.L1SeedChangeFit=0
        self.ShowAllBadRates=0
        
    def ReadList(self,filename):
        filename=self.BasePath+'/'+filename
        list = []
        if not os.path.exists(filename):
            return list
        f = open(filename)
        for line in f:
            if line.startswith('#'):
                continue
            if len(line)<3 or line=='\n':
                continue
            line = ((line.rstrip('\n')).rstrip(' '))
            if line.find(':')==-1: # exclude list, no rate estimates
                list.append( line )
            else:
                split = line.split(':')
                list.append(split[0])
                ##list.append([split[0],split[1],split[2],split[3]])
        f.close()
        return list

    def ReadCFG(self):
        f=open(self.CFGfile)
        for line in f:
            if line.startswith('#'):
                continue
            if len(line)<1:
                continue
            
            strippedLine = line.split('#')[0]
            strippedLine = strippedLine.rstrip('\n').rstrip(' ')
            if strippedLine=='':
                continue
            tok = strippedLine.split('=')
            par = tok[0].rstrip(' ').lstrip(' ')
            if len(tok)>=2:
                arg=tok[1].rstrip('\n').rstrip(' ').lstrip(' ')
            else:
                arg=''
                
            if par=="ReferenceRun":
                self.ReferenceRun=arg
            elif par=="ShowSigmaAndPercDiff":
                self.DefShowSigmaAndPercDiff=float(arg)
            elif par=="DefaultAllowedRatePercDiff":
                self.DefAllowRatePercDiff=float(arg)
            elif par=="DefaultAllowedRateSigmaDiff":
                self.DefAllowRateSigmaDiff=float(arg)                
            elif par=="DefaultIgnoreThreshold":
                self.DefAllowIgnoreThresh=float(arg)
            elif par=="ExcludeTriggerList":
                self.ExcludeList=self.ReadList(arg)
            elif par=="TriggerToMonitorList":
                tmp=self.ReadList(arg)
                for line in tmp:
                    self.MonitorList.append(line)
                    #self.MonitorIntercept.append(float(line[1]))
                    #self.MonitorSlope.append(float(line[2]))
                    #self.MonitorQuad.append(float(line[3]))
            elif par=="ForbiddenColumns":
                tmp=arg.split(',')
                for line in tmp:
                    try:
                        self.ForbiddenCols.append(int(line))
                    except:
                        print "Cannot parse Forbidden Cols parameter"
            elif par =="AllTriggers":
                self.AllTriggers=int(arg)
            elif par=="LSSlidingWindow":
                self.LSWindow=int(arg)
            elif par=="CompareReference":
                self.CompareReference=int(arg)
            elif par=="ShifterMode":
                self.ShifterMode=arg
            elif par=="MaxExpressRate":
                self.MaxExpressRate=float(arg)
            elif par=="MaxStreamARate":
                self.MaxStreamARate=float(arg)
            elif par=="FitFileName":
                self.FitFileName=arg
            elif par=="NoVersion":
                self.NoVersion=int(arg)
            elif par=="CirculatingBeamsColumn":
                self.CircBeamCol=int(arg)
            elif par=="MaxLogMonRate":
                self.MaxLogMonRate=float(arg)
            elif par=="WarnOnSigmaDiff":
                self.DefWarnOnSigmaDiff=float(arg)
            elif par=="DoL1":
                self.DoL1=int(arg)
            elif par=="DefaultMaxBadRatesToShow":
                self.DefaultMaxBadRatesToShow=int(arg)
            elif par=="L1SeedChangeFit":
                self.L1SeedChangeFit=int(arg)
            elif par=="ShowAllBadRates":
                self.ShowAllBadRates=int(arg)                
            else:
                print "Invalid Option : "+strippedLine

        f.close()
                
    def AnalyzeTrigger(self,TrigName): ## Have to pass this a version number stripped Trigger
        if TrigName in self.ExcludeList:
            return False
        if self.MonitorOnly and not TrigName in self.MonitorList:
            return False
        return True

    def GetExpectedRate(self,TrigName,Input,InputPS,live,delivered,deadtime,L1SeedChangeFit,HeadLumiRange,PSColumnByLS):
        #replaced live/delivered with deadtimebeamactive
        if self.NoVersion:
            TrigName=StripVersion(TrigName)
        if TrigName not in Input.keys():
            return [0.0,0.0,"No prediction (fit missing)"]

        if not L1SeedChangeFit:
            try:
                sigma = Input[TrigName][5]
            except:
                if Input[TrigName][0] == "fit failed":
                    return [0.0,0.0,"No prediction (fit missing)"]
                else:
                    return [0.0,0.0,"Exception error"]

            try:
                if Input[TrigName][0] == "line" or Input[TrigName][0] == "quad" or Input[TrigName][0] == "cube":
                    return [(1-deadtime)*(Input[TrigName][1]+Input[TrigName][2]*delivered+Input[TrigName][3]*delivered*delivered+Input[TrigName][4]*delivered*delivered*delivered), sigma,""]
                elif Input[TrigName][0] == "expo":
                    return [(1-deadtime)*(Input[TrigName][1]+Input[TrigName][2]*math.exp(Input[TrigName][3]+Input[TrigName][4]*delivered)), sigma,""]
            except:
                return [0.0,0.0,"Exception error"]

        ###L1SeedChangeFit    
        else:
            firstLS=min(HeadLumiRange)
            psi=PSColumnByLS[firstLS]

            try:
                sigma = InputPS[psi][TrigName][5]
            except:
                #print psi, TrigName
                
                #if InputPS[psi][TrigName][0] == "fit failed":
                #    return [0.0,0.0,"No prediction (fit missing)"]
                #else:
                return [0.0,0.0,"Exception error"]

            try:
                if InputPS[psi][TrigName][0] == "line" or InputPS[psi][TrigName][0] == "quad" or InputPS[psi][TrigName][0] == "cube":
                    return [(1-deadtime)*(InputPS[psi][TrigName][1]+InputPS[psi][TrigName][2]*delivered+InputPS[psi][TrigName][3]*delivered*delivered+InputPS[psi][TrigName][4]*delivered*delivered*delivered), sigma,""]
                elif InputPS[psi][TrigName][0] == "expo":
                    return [(1-deadtime)*(InputPS[psi][TrigName][1]+InputPS[psi][TrigName][2]*math.exp(InputPS[psi][TrigName][3]+InputPS[psi][TrigName][4]*delivered)), sigma,""]
            except:
                return [0.0,0.0,"Exception error"]

        return -1
                    
        
##     def GetExpectedL1Rates(self,lumi):
##         if not lumi:
##             return {}
##         expectedRates = {}
##         for col,inter,slope,quad in self.L1Predictions:
##             try:
##                 expectedRates[int(col)] = lumi*(float(inter)+float(slope)*lumi+float(quad)*lumi*lumi)
##             except:
##                 return {}
##         return expectedRates
       
    
