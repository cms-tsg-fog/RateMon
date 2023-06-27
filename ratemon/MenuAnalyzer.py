import os
import sys
from DatabaseParser import ConnectDB
import re
import cx_Oracle
import eventContent
import pdb
import string

try:  ## set is builtin in python 2.6.4 and sets is deprecated
    set
except NameError:
    from sets import Set

class MenuAnalyzer:
    def __init__(self,name):
        ##default ranges
        self.maxModuleNameLength = 300
        self.maxModulesPerPath   = 50
        self.maxPaths = 1000
        self.maxEndPaths = 100 # arbitrary maximum number of EndPaths, increased to 100 end of Run 2 
        self.requiredContent = {}
 
        ##required streams
        self.requiredStreamsAndPDs = { 'Calibration' : ['TestEnablesEcalHcal'],
                                       'EcalCalibration' : ['EcalLaser'],
                                       'DQMCalibration' : ['TestEnablesEcalHcalDQM'],
                                       'DQM' : ['OnlineMonitor']}
        self.requiredEndPaths = ['DQMHistograms']

        self.useMenuName = True
        ##eventContent for different menus
        if ('physics' in name):
            self.requiredContent_collision()
            self.menuMode = 'collision'
        elif ('circulating' in name):
            self.requiredContent_circulating()
            self.menuMode = 'circulating'
        elif ('cosmic' in name):
            self.requiredContent_cosmic()
            self.menuMode = 'cosmic'
        else:
            self.requiredContent_collision()
            self.menuMode = 'collision'
            self.useMenuName = False

        ##express stream name for different menus
        if ('physics' in name):
            self.ExpressStreamName = 'Express'
        elif ('Protonion' in name):
            self.ExpressStreamName = 'ExpressPA'
        elif ('circulating' in name):
            self.ExpressStreamName = 'ExpressCosmics'
        elif ('cosmic' in name):
            self.ExpressStreamName = 'ExpressCosmics'
        else:
            self.ExpressStreamName = 'Express'

        self.expressPDs      = { 'ExpressPhysics' : 'Collisions',
                                 'ExpressCosmics' : 'Cosmics', 
                                 'ExpressPhysicsPA' : 'pPb Collisions' }

        self.expressType = ''

        self.menuName = name
        self.processName=''
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
            'reqEndPaths' : self.reqEndPaths,
            'checkExpress' : self.checkExpress,
            'checkNameFormats' :self.checkNameFormats,
            'checkReqEventContent':self.checkReqEventContent,
            'checkNotReqEventContent':self.checkNotReqEventContent,
            'checkL1Unmask':self.checkL1Unmask,
            'checkDQMStream':self.checkDQMStream,
            'checkProcessName':self.checkProcessName
            }

        self.ProblemDescriptions = {
            'moduleLength':'Modules too long',
            'numberOfPaths':'Too many paths',
            'numberOfEndPaths':'Too many endpaths',
            'reqStreamsAndPDs':'Missing required stream/PD',
            'reqEndPaths':'Missing required endpaths',
            'checkExpress' : 'Invalid or missing express stream/PD \n[Note: This check will fail if a cosmics menu does not contain "cosmic" in its name]',
            'checkNameFormats' : 'Invalid stream, PD or path name format',
            'checkReqEventContent' : 'Missing Event Content',
            'checkNotReqEventContent' : 'Extra Event Content',
            'checkL1Unmask' : 'L1 Unmask Module in Menu',
            'checkDQMStream' : 'Check that the DQM stream contains correct trigger',
            'checkProcessName' : 'Check that process name is "HLT"'
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
        for name in self.AnalysisMap.keys():
            self.AddAnalysis(name)

    def Analyze(self):
        cursor = ConnectDB('hlt')
        self.GetModules(cursor)
        self.GetESModules(cursor)
        self.GetStreamsPathsPDs(cursor)
        self.GetEventContent(cursor)
        self.GetProcessName(cursor)
        isError = False
        if len(self.perStreamPDList) == 0:
            print("FATAL ERROR: Cannot find any streams in this menu")
            isError=True
        if len(self.perPDPathList) == 0:
            print("FATAL ERROR: Cannot find any PDs in this menu")
            isError=True
        if isError:
            print("ABORTING")
            sys.exit()
        self.findParkingTriggers()
        for analysis in self.AnalysisList: 
            if analysis not in self.AnalysisMap:
                print("ERROR: Analysis %s not defined" % (analysis))
                continue
            self.AnalysisMap[analysis]()
            
    def checkModuleLength(self):
        self.Results['moduleLength'] = []
        for modName,type in self.perModuleTypeList.items():
            if len(modName) > self.maxModuleNameLength: self.Results['moduleLength'].append(modName)
        
    def checkNumPaths(self):
        if len(self.perPathModuleList) > self.maxPaths:
            self.Results['numberOfPaths'] = self.perPathModuleList
        else:
            self.Results['numberOfPaths'] = 0
    def checkNumEndPaths(self):
        if len(self.endPathList) > self.maxEndPaths:
            self.Results['numberOfEndPaths'] = self.endPathList
        else:
            self.Results['numberOfEndPaths'] = 0
    def reqStreamsAndPDs(self):
        self.Results['reqStreamsAndPDs'] = []
        for stream,PDList in self.requiredStreamsAndPDs.items():
            if stream not in self.perStreamPDList:
                self.Results['reqStreamsAndPDs'].append(stream)
                continue
            for PD in PDList:
                if not PD in self.perStreamPDList[stream]: self.Results['reqStreamsAndPDs'].append(stream+'::'+PD)
    
    def reqEndPaths(self):
        self.Results['reqEndPaths'] = []
        for endpath in self.requiredEndPaths:
            if not endpath in self.endPathList:
                self.Results['reqEndPaths'].append(endpath)

    def checkExpress(self):
        self.Results['checkExpress'] = []
        if self.ExpressStreamName not in self.perStreamPDList:
            self.Results['checkExpress'].append(self.ExpressStreamName)
            return

        if len(self.perStreamPDList[self.ExpressStreamName]) > 1:
            self.Results['checkExpress'].append("MULTIPLE_PDS")
        if len(self.perStreamPDList[self.ExpressStreamName]) < 1:
            self.Results['checkExpress'].append("NO_PDS")

        for PD in self.perStreamPDList[self.ExpressStreamName]:
            if PD not in self.expressPDs:
                self.Results['checkExpress'].append(self.ExpressStreamName+"::"+PD)
            else:
                self.expressType = self.expressPDs[PD]

    def checkNameFormats(self):
        self.Results['checkNameFormats']=[]
        for PD,path in self.perPDPathList.items():
            if not self.T0REGEXP['RXDATASET'].match(PD):
                for k,v in self.perStreamPDList.items():
                    if PD in v:
                        self.Results['checkNameFormats'].append(k+"::"+PD+"::"+str(path))
                        break
                self.Results['checkNameFormats'].append('NO STREAM::'+PD+"::"+str(path))
        for path in self.perPathModuleList.keys():
            if not self.T0REGEXP['RXSAFEPATH'].match(path):
                self.Results['checkNameFormats'].append(path)

        for stream in self.perStreamPDList:
            if 'stream' in str(stream).lower() or 'part' in str(stream).lower():
                self.Results['checkNameFormats'].append('WRONG STREAM NAME '+str(stream))
            for pd in self.perStreamPDList[stream]:
                    if 'part' in str(pd):
                        self.Results['checkNameFormats'].append('WRONG DATASET NAME '+str(pd)+' in stream ' + stream )

    def checkReqEventContent(self):
        self.Results['checkReqEventContent']=[]
        for stream,content in self.eventContent.items():
            #first check for a drop statement
            if not ('drop *' in content or 'drop *_hlt*_*_*' in content):
                self.Results['checkReqEventContent'].append(stream+'::drop *')
            if stream not in self.requiredContent:
                continue
            elif ('Protonion' in self.menuName) and stream == 'DQM':
                stream = 'DQM_PA'
            requiredContent = self.requiredContent[stream]
            #check to see if stream contains required content
            for entry in requiredContent:
                if not entry in content:
                    self.Results['checkReqEventContent'].append(stream+'::'+entry)
    
    def checkNotReqEventContent(self):
        self.Results['checkNotReqEventContent']=[]
        for stream,content in self.eventContent.items():
            #first check for a drop statement
            if not ('drop *' in content or 'drop *_hlt*_*_*' in content):
                self.Results['checkNotReqEventContent'].append(stream+'::drop *')
            if stream not in self.requiredContent:
                continue
            elif ('Protonion' in self.menuName) and stream == 'DQM':
                stream = 'DQM_PA'
            requiredContent = self.requiredContent[stream]
            #check to make sure there is no extra (not-required) content
            for entry in content:
                if (entry!='drop *' and entry!='drop *_hlt*_*_*'):
                    if not entry in requiredContent:
                        self.Results['checkNotReqEventContent'].append(stream+'::'+entry)

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
            if key.startswith("Physics"): # look at PDs only in streams that start with Physics
                for PD in self.perStreamPDList[key]:
                    if (PD.find("Parked") != -1 or PD.find("ParkingBPH") != -1 or PD.find("Ephemeral") != -1): # look for PDs with Parked in the name
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
        for trig in sorted(self.NotParkingTriggers):
            if trig.find("LogMonitor") != -1: continue
            if trig.startswith("DST_"): continue
            if trig.startswith("Dataset_"): continue
            if ('OnlineMonitor' not in self.perPDPathList) or (not trig in self.perPDPathList["OnlineMonitor"]):
               self.Results['checkDQMStream'].append("NotInDQM::%s"%trig)
        if 'OnlineMonitor' in self.perPDPathList:
           for trig in sorted(self.ParkingTriggers):
               if trig in self.perPDPathList["OnlineMonitor"]: self.Results['checkDQMStream'].append("ParkingTriggerInDQM::%s"%trig)

    def checkProcessName(self):
        self.Results['checkProcessName']=[]
        if self.processName != "HLT":
            if self.processName != None:
                self.Results['checkProcessName'].append('process name is "'+self.processName+'"')
            else:
                self.Results['checkProcessName'].append('process name is EMPTY')

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
        """ % (self.menuName)
        
        cursor.execute(sqlquery)
        for PathName,ModuleName,ModuleType,endPath in cursor.fetchall():
            if PathName not in self.perPathModuleList: self.perPathModuleList[PathName] = []
            self.perPathModuleList[PathName].append(ModuleName)
            self.perModuleTypeList[ModuleName] = ModuleType
            if not ModuleName in self.ModuleList: self.ModuleList.append(ModuleName)
            if endPath: self.endPathList.add(PathName)

    def GetStreamsPathsPDs(self,cursor):
        # sqlquery= """
        # SELECT distinct a.name AS stream,
        # b.name AS dataset,
        # c.name AS path
        # FROM
        # cms_hlt_gdr.u_streams a,
        # cms_hlt_gdr.u_datasets b,
        # cms_hlt_gdr.u_paths c,
        # cms_hlt_gdr.u_confversions d,
        # cms_hlt_gdr.u_pathid2strdst e,
        # cms_hlt_gdr.u_streamids f,
        # cms_hlt_gdr.u_datasetids g,
        # cms_hlt_gdr.u_pathids h,
        # cms_hlt_gdr.u_pathid2conf i
        # WHERE
        # d.name = '%s'
        # AND i.id_confver = d.id
        # AND h.id = i.id_pathid
        # AND c.id = h.id_path
        # AND e.id_pathid = h.id
        # AND f.id = e.id_streamid
        # AND a.id = f.id_stream
        # AND g.id = e.id_datasetid
        # AND b.id = g.id_dataset
        # ORDER BY path, dataset, stream
        # """ % (self.menuName)
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
        cms_hlt_gdr.u_pathid2conf i,
        cms_hlt_gdr.u_conf2strdst j
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
        AND j.id_confver=d.id
        AND j.id_streamid=e.id_streamid
        AND j.id_datasetid=e.id_datasetid
        ORDER BY path, dataset, stream
        """ % (self.menuName)
        
        cursor.execute(sqlquery)
        for StreamName,PDName,PathName in cursor.fetchall():
            if StreamName not in self.perStreamPDList: self.perStreamPDList[StreamName] = []
            if not PDName in self.perStreamPDList[StreamName]: self.perStreamPDList[StreamName].append(PDName)
            if PDName not in self.perPDPathList: self.perPDPathList[PDName] = []
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
        """ % (self.menuName)
        
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
        """ % (self.menuName)

        cursor.execute(sqlquery)
        for stream,keep,Class,module,extra,process in cursor.fetchall():
            if stream not in self.eventContent: self.eventContent[stream]=[]
            statement = "%s_%s_%s_%s" % (Class,module,extra,process)
            if statement == "*_*_*_*": statement = "*"
            if keep == 1: statement = "keep "+statement
            else: statement = "drop "+statement
            if not statement in self.eventContent[stream]:
                self.eventContent[stream].append( statement )

    def GetProcessName(self,cursor):
        sqlquery = """
        SELECT confver.ProcessName FROM  cms_hlt_gdr.u_confversions confver
        WHERE 
        confver.name = '%s'
        """  % (self.menuName)

        cursor.execute(sqlquery)
        # should be exactly 1 entry and that will have a tuple with one entry "processName"
        self.processName = cursor.fetchall()[0][0]

    def requiredContent_collision(self):
        self.requiredContent = eventContent.requiredEventContent_collision
        return self.requiredContent

    def requiredContent_circulating(self):
        self.requiredContent = eventContent.requiredEventContent_circulating
        return self.requiredContent

    def requiredContent_cosmic(self):
        self.requiredContent = eventContent.requiredEventContent_cosmic
        return self.requiredContent
