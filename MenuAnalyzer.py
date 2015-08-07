#!/usr/bin/env python

import os
import sys
from DatabaseParser import ConnectDB
import re
import cx_Oracle
import eventContent

try:  ## set is builtin in python 2.6.4 and sets is deprecated
    set
except NameError:
    from sets import Set

class MenuAnalyzer:
    def __init__(self,name):
        ##default ranges
        self.maxModuleNameLength = 300
        self.maxModulesPerPath   = 50
        self.maxPaths = 500
        self.maxEndPaths = 30

        ##required streams
        self.requiredStreamsAndPDs = { 'Calibration' : ['TestEnablesEcalHcalDT'],'EcalCalibration' : ['EcalLaser'],
                                       'DQM' : 'OnlineMonitor'}
        self.ExpressStreamName = 'Express'
        self.expressPDs      = { 'ExpressPhysics' : 'Collisions',
                                 'ExpressCosmics' : 'Cosmics' }

        self.expressType = ''

        self.menuName = name
        self.endPathList = set()
        self.perPathModuleList={}
        self.perModuleTypeList={}
        self.perStreamPDList={}
        self.perPDPathList={}
        self.Results={}
        self.ModuleList=[]
        self.ESModuleList=[]
        self.eventContent={}
        self.ParkingTriggers=[]
        self.NotParkingTriggers=[]

        self.AnalysisList=[]
        

        ## statically define the analysis map: new analyses must be registered here
        self.AnalysisMap = {
            'moduleLength' : self.checkModuleLength,
            'numberOfPaths' : self.checkNumPaths,
            'numberOfEndPaths' : self.checkNumEndPaths,
            'reqStreamsAndPDs' : self.reqStreamsAndPDs,
            'checkExpress' : self.checkExpress,
            'checkNameFormats' :self.checkNameFormats,
            'checkEventContent':self.checkEventContent,
            'checkL1Unmask':self.checkL1Unmask,
            'checkDQMStream':self.checkDQMStream,
            'checkStreamB':self.checkStreamB
            }
        self.ProblemDescriptions = {
            'moduleLength':'Modules too long',
            'numberOfPaths':'Too many paths',
            'numberOfEndPaths':'Too many endpaths',
            'reqStreamsAndPDs':'Missing required stream/PD',
            'checkExpress' : 'Invalid or missing express stream/PD',
            'checkNameFormats' : 'Invalid PD or path name format',
            'checkEventContent' : 'Invalid Event Content',
            'checkL1Unmask' : 'L1 Unmask Module in Menu',
            'checkDQMStream' : 'Check that the DQM stream contains correct trigger',
            'checkStreamB' : 'Check all parking triggers in stream B'
            }

        self.T0REGEXP = { ## These are the regexps that T0 uses to access things
            # Regexp for save file name paths. We don't process anything else.
            'RXSAFEPATH' : re.compile("^[-A-Za-z0-9_]+$"),
            # Regexp for valid dataset names.
            'RXDATASET' : re.compile("^[-A-Za-z0-9_]+$"),
            # Regexp for valid RelVal dataset names.
            'RXRELVALMC' : re.compile("^/RelVal[^/]+/(CMSSW(?:_[0-9]+)+(?:_pre[0-9]+)?)[-_].*$"),
            'RXRELVALDATA' : re.compile("^/[^/]+/(CMSSW(?:_[0-9]+)+(?:_pre[0-9]+)?)[-_].*$"),
            # Regexp for online DQM files.
            'RXONLINE' : re.compile("^(?:.*/)?DQM_V(\d+)(_[A-Za-z0-9]+)?_R(\d+)\.root$"),
            # Regexp for offline DQM files.
            'RXOFFLINE' : re.compile("^(?:.*/)?DQM_V(\d+)_R(\d+)((?:__[-A-Za-z0-9_]+){3})\.root$"),
            # Regexp for acquisition era part of the processed dataset name.
            'RXERA' : re.compile("^([A-Za-z]+\d+|CMSSW(?:_[0-9]+)+(?:_pre[0-9]+)?)")
            }

    def AddAnalysis(self,name): 
        self.AnalysisList.append(name)

    def AddAllAnalyses(self):
        for name in self.AnalysisMap.iterkeys():
            self.AddAnalysis(name)

    def Analyze(self):
        cursor = ConnectDB('hlt')
        self.GetModules(cursor)
        self.GetESModules(cursor)
        self.GetStreamsPathsPDs(cursor)
        self.GetEventContent(cursor)
        isError = False
        if len(self.perStreamPDList) == 0:
            print "FATAL ERROR: Cannot find any streams in this menu"
            isError=True
        if len(self.perPDPathList) ==0:
            print "FATAL ERROR: Cannot find any PDs in this menu"
            isError=True
        if isError:
            print "ABORTING"
            sys.exit()
        self.findParkingTriggers()
        for analysis in self.AnalysisList: 
            if not self.AnalysisMap.has_key(analysis):
                print "ERROR: Analysis %s not defined" % (analysis,)
                continue
            print "analysis = ", analysis
            self.AnalysisMap[analysis]()
            

    def checkModuleLength(self):
        self.Results['moduleLength'] = []
        for modName,type in self.perModuleTypeList.iteritems():
            if len(modName) > self.maxModuleNameLength: self.Results['moduleLength'].append(modName)
        
    def checkNumPaths(self):
        if len(self.perPathModuleList) > self.maxPaths:
            self.Results['numberOfPaths'] = len(self.perPathModuleList) 
        else:
            self.Results['numberOfPaths'] = 0
    def checkNumEndPaths(self):
        if len(self.endPathList) > self.maxEndPaths:
            self.Results['numberOfEndPaths'] = len(self.endPathList)
        else:
            self.Results['numberOfEndPaths'] = 0
    def reqStreamsAndPDs(self):
        self.Results['reqStreamsAndPDs'] = []
        for stream,PDList in self.requiredStreamsAndPDs.iteritems():
            if not self.perStreamPDList.has_key(stream): self.Results['reqStreamsAndPDs'].append(stream)
            for PD in PDList:
                if not PD in self.requiredStreamsAndPDs[stream]: self.Results['reqStreamsAndPDs'].append(stream+'::'+PD)
    
    def checkExpress(self):
        self.Results['checkExpress'] = []
        if not self.perStreamPDList.has_key(self.ExpressStreamName):
            self.Results['checkExpress'].append(self.ExpressStreamName)
            return

        if len(self.perStreamPDList[self.ExpressStreamName]) >1:
            self.Results['checkExpress'].append("MULTIPLE_PDS")
        if len(self.perStreamPDList[self.ExpressStreamName]) <1:
            self.Results['checkExpress'].append("NO_PDS")

        for PD in self.perStreamPDList[self.ExpressStreamName]:
            if not self.expressPDs.has_key(PD):
                self.Results['checkExpress'].append(self.ExpressStreamName+"::"+PD)
            else:
                self.expressType = self.expressPDs[PD]
                
        

    def checkNameFormats(self):
        self.Results['checkNameFormats']=[]
        for PD,path in self.perPDPathList.iteritems():
            if not self.T0REGEXP['RXDATASET'].match(PD):
                for k,v in self.perStreamPDList.iteritems():
                    if PD in v:
                        self.Results['checkNameFormats'].append(k+"::"+PD+"::"+str(path))
                        break
                self.Results['checkNameFormats'].append('NO STREAM::'+PD+"::"+str(path))
        for path in self.perPathModuleList.iterkeys():
            if not self.T0REGEXP['RXSAFEPATH'].match(path):
                self.Results['checkNameFormats'].append(path)

    def checkEventContent(self):
        self.Results['checkEventContent']=[]
        for stream,content in self.eventContent.iteritems():
            #first check for a drop statement
            if not ('drop *' in content or 'drop *_hlt*_*_*' in content):
                self.Results['checkEventContent'].append(stream+'::drop *')
            if not eventContent.requiredEventContent.has_key(stream): continue
            requiredContent = eventContent.requiredEventContent[stream]
            for entry in requiredContent:
                if not entry in content:
                    self.Results['checkEventContent'].append(stream+'::'+entry)

    def checkL1Unmask(self):
        self.Results['checkL1Unmask']=[]
        if 'L1GtTriggerMaskAlgoTrigTrivialProducer' in self.ESModuleList:
            self.Results['checkL1Unmask'].append('L1GtTriggerMaskAlgoTrigTrivialProducer')
        if 'L1GtTriggerMaskTechTrigTrivialProducer' in self.ESModuleList:
            self.Results['checkL1Unmask'].append('L1GtTriggerMaskTechTrigTrivialProducer')


    def findParkingPDs(self):
        ParkingPDs=[]
        NotParkingPDs=[]
        for key in self.perStreamPDList:
            if key.startswith("Physics"):             # look at PDs only in streams that start with Physics
                for PD in self.perStreamPDList[key]:         
                    if PD.find("Parked")!=-1:         # look for PDs with Parked in the name
                        ParkingPDs.append(PD)
                    else:
                        NotParkingPDs.append(PD)
        return (ParkingPDs,NotParkingPDs)

    def findParkingTriggers(self):
        ParkingPDs,NotParkingPDs = self.findParkingPDs()
        for PD in NotParkingPDs:
            for trig in self.perPDPathList[PD]: self.NotParkingTriggers.append(trig) # first append ALL triggers from the not in parking PDs
        for PD in ParkingPDs:
            for trig in self.perPDPathList[PD]:
                if not trig in self.NotParkingTriggers: self.ParkingTriggers.append(trig) # get triggers that don't show up in the non-parking PDs
                

    def checkDQMStream(self):
        self.Results['checkDQMStream']=[]
        for trig in self.NotParkingTriggers:
            if trig.find("LogMonitor")!=-1: continue
            if not trig in self.perPDPathList["OnlineMonitor"]: self.Results['checkDQMStream'].append("NotInDQM::%s"%trig)
        for trig in self.ParkingTriggers:
            if trig in self.perPDPathList["OnlineMonitor"]: self.Results['checkDQMStream'].append("ParkingTriggerInDQM::%s"%trig)

    def checkStreamB(self):
        self.Results['checkStreamB']=[]
        for trig in self.ParkingTriggers:
            if not trig in self.perPDPathList["ParkingMonitor"]: self.Results['checkStreamB'].append("ParkingTriggerNotInStreamB::%s" %trig)
            
    def GetModules(self,cursor):
        sqlquery ="""  
        SELECT cms_hlt_gdr.u_paths.name path, cms_hlt_gdr.u_paelements.name  module, cms_hlt_gdr.u_moduletemplates.name template, cms_hlt_gdr.u_pathids.isendpath
        FROM
        cms_hlt_gdr.u_pathid2pae,cms_hlt_gdr.u_paelements, cms_hlt_gdr.u_pathid2conf,cms_hlt_gdr.u_confversions, cms_hlt_gdr.u_pathids,cms_hlt_gdr.u_paths, cms_hlt_gdr.u_mod2templ,cms_hlt_gdr.u_moduletemplates
        WHERE
        cms_hlt_gdr.u_pathid2conf.id_pathid=cms_hlt_gdr.u_pathid2pae.id_pathid and
        cms_hlt_gdr.u_pathids.id=cms_hlt_gdr.u_pathid2conf.id_pathid and
        cms_hlt_gdr.u_paths.id=cms_hlt_gdr.u_pathids.id_path and
        cms_hlt_gdr.u_pathid2pae.id_pae=cms_hlt_gdr.u_paelements.id and
        cms_hlt_gdr.u_mod2templ.id_pae=cms_hlt_gdr.u_paelements.id and
        cms_hlt_gdr.u_moduletemplates.id=cms_hlt_gdr.u_mod2templ.id_templ and
        cms_hlt_gdr.u_paelements.paetype=1 and
        cms_hlt_gdr.u_pathid2conf.id_confver = cms_hlt_gdr.u_confversions.id and
        cms_hlt_gdr.u_confversions.name='%s'
        """ % (self.menuName,)
        
        cursor.execute(sqlquery)
        for PathName,ModuleName,ModuleType,endPath in cursor.fetchall():
            if not self.perPathModuleList.has_key(PathName): self.perPathModuleList[PathName] = []
            self.perPathModuleList[PathName].append(ModuleName)
            self.perModuleTypeList[ModuleName] = ModuleType
            if not ModuleName in self.ModuleList: self.ModuleList.append(ModuleName)
            if endPath: self.endPathList.add(PathName)

    def GetStreamsPathsPDs(self,cursor):
        sqlquery= """
        SELECT distinct a.name AS stream,
        b.name AS dataset,
        c.name AS path
        FROM
        cms_hlt_gdr.u_streams a,
        cms_hlt_gdr.u_datasets b,
        cms_hlt_gdr.u_paths c,
        cms_hlt_gdr.u_confversions d,
        cms_hlt_gdr.u_pathid2strdst e,
        cms_hlt_gdr.u_streamids f,
        cms_hlt_gdr.u_datasetids g,
        cms_hlt_gdr.u_pathids h,
        cms_hlt_gdr.u_pathid2conf i
        WHERE
        d.name = '%s'
        AND i.id_confver = d.id
        AND h.id = i.id_pathid
        AND c.id = h.id_path
        AND e.id_pathid = h.id
        AND f.id = e.id_streamid
        AND a.id = f.id_stream
        AND g.id = e.id_datasetid
        AND b.id = g.id_dataset
        ORDER BY path, dataset, stream
        """ % (self.menuName,)
        
        cursor.execute(sqlquery)
        for StreamName,PDName,PathName in cursor.fetchall():
            if not self.perStreamPDList.has_key(StreamName): self.perStreamPDList[StreamName] = []
            if not PDName in self.perStreamPDList[StreamName]: self.perStreamPDList[StreamName].append(PDName)
            if not self.perPDPathList.has_key(PDName): self.perPDPathList[PDName] = []
            self.perPDPathList[PDName].append(PathName)

    def GetESModules(self,cursor):
        sqlquery = """
        SELECT unique a.name
        FROM cms_hlt_gdr.u_esmodules a,
        cms_hlt_gdr.u_confversions d,
        cms_hlt_gdr.u_conf2esm i
        WHERE d.name = '%s'
        AND i.id_confver = d.id
        AND i.id_esmodule=a.id
        ORDER by name
        """ % (self.menuName,)
        
        cursor.execute(sqlquery)
        for ModuleName, in cursor.fetchall():
            if not ModuleName in self.ESModuleList: self.ESModuleList.append(ModuleName)

    def GetEventContent(self,cursor):
        sqlquery = """
        SELECT n.name streamlabel, s.statementtype, s.classn, s.modulel,s.extran,s.processn
        FROM
        cms_hlt_gdr.u_evcostatements s,
        cms_hlt_gdr.u_eventcontents u,
        cms_hlt_gdr.u_eventcontentids i,
        cms_hlt_gdr.u_conf2evco c,
        cms_hlt_gdr.u_evco2stat e,
        cms_hlt_gdr.u_confversions  d,
        cms_hlt_gdr.u_evco2stream t,
        cms_hlt_gdr.u_streamids l,
        cms_hlt_gdr.u_streams n
        WHERE
        d.name = '%s' and
        i.id=c.id_evcoid and u.id=i.id_evco and c.id_confver=d.id and e.id_evcoid=i.id and
        s.id=e.id_stat and t.id_evcoid=i.id and l.id=t.id_streamid and n.id=l.id_stream
        ORDER BY streamlabel
        """ % (self.menuName,)

        cursor.execute(sqlquery)
        for stream,keep,Class,module,extra,process in cursor.fetchall():
            if not self.eventContent.has_key(stream): self.eventContent[stream]=[]
            statement = "%s_%s_%s_%s" % (Class,module,extra,process,)
            if statement == "*_*_*_*": statement = "*"
            if keep == 1: statement = "keep "+statement
            else: statement = "drop "+statement
            if not statement in self.eventContent[stream]:
                self.eventContent[stream].append( statement )
