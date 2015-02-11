#!/usr/bin/python
import cx_Oracle
import cPickle as pickle
import os
import sys
import time
import re
from colors import *

try:  ## set is builtin in python 2.6.4 and sets is deprecated
    set
except NameError:
    from sets import Set


class DatabaseParser:
    
    def __init__(self):
        
        self.curs = ConnectDB()
        ##-- Defined in ParsePage1 --##
        self.RunNumber = 0

        ##-- Defined in ParseRunPage --##
        self.Date=''
        self.L1_HLT_Key=''
        self.HLT_Key=''
        self.GTRS_Key=''
        self.TSC_Key=''
        self.GT_Key=''
        self.ConfigId=0

        ##-- Defined in ParseHLTSummaryPage --##
        self.HLTRatesByLS = {}
        self.HLTPSByLS = {}

        self.nAlgoBits=0
        self.L1PrescaleTable=[]
        self.AvgL1Prescales=[] ## contains the average L1 prescales for the current LS range range
        self.HLTList=[]
        self.AvgTotalPrescales={}
        self.HLTPrescaleTable=[] ## can't fill this yet
        self.UnprescaledRates={}
        self.PrescaledRates={}
        ##-- Defined in ParseLumiPage --##
        self.LastLSParsed=-1
        self.InstLumiByLS = {}
        self.DeliveredLumiByLS = {}
        self.LiveLumiByLS = {}
        self.PSColumnByLS = {}
        self.AvInstLumi = 0
        self.AvDeliveredLumi = 0
        self.AvLiveLumi = 0
        self.AvDeadTime = 0
        self.LumiInfo = {}  ##Returns
        self.DeadTime = {}
        self.Physics = {}
        self.Active = {}

        
        self.B1Pres = {}
        self.B2Pres = {}
        self.B1Stab = {}
        self.B2Stab = {}
        self.EBP = {}
        self.EBM = {}
        self.EEP = {}
        self.EEM = {}
        self.HBHEA = {}
        self.HBHEB = {}
        self.HBHEC = {}
        self.HF = {}
        self.RPC = {}
        self.DT0 = {}
        self.DTP = {}
        self.DTM = {}
        self.CSCP = {}
        self.CSCM = {}
        self.TOB = {}
        self.TIBTID= {}
        self.TECP = {}
        self.TECM = {}
        self.BPIX = {}
        self.FPIX = {}
        self.ESP = {}
        self.ESM = {}

        self.DeadTimeBeamActive = {}
       
        
        ##-- Defined in ParsePSColumnPage (not currently used) --##
        self.PSColumnChanges=[]  ##Returns

        ##-- Defined in ParseTriggerModePage --##
        self.L1TriggerMode={}  ## 
        self.HLTTriggerMode={} ## 
        self.HLTSeed={}
        self.HLTSequenceMap=[]
        self.TriggerInfo = []  ##Returns

        ##-- Defined in AssemblePrescaleValues --##
        self.L1Prescale={}
        self.L1IndexNameMap={}
        self.HLTPrescale=[]
        self.MissingPrescale=[]
        self.PrescaleValues=[]  ##Returns

        ##-- Defined in ComputeTotalPrescales --##
        self.TotalPSInfo = []  ##Returns # #collection 

        ##-- Defined in CorrectForPrescaleChange --##
        self.CorrectedPSInfo = []  ##Returns
        self.HLTPrescaleTable={}
        
        ##-- In the current Parser.py philosophy, only RunNumber is set globally
        ##    - LS range is set from the outside for each individual function
        #self.FirstLS = -1
        #self.LastLS = -1
        
    def GetRunInfo(self):
        ## This query gets the L1_HLT Key (A), the associated HLT Key (B) and the Config number for that key (C)
        KeyQuery = """
        SELECT A.TRIGGERMODE, B.HLT_KEY, B.GT_RS_KEY, B.TSC_KEY, C.CONFIGID, D.GT_KEY FROM
        CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF B, CMS_HLT.CONFIGURATIONS C, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
        B.ID = A.TRIGGERMODE AND C.CONFIGDESCRIPTOR = B.HLT_KEY AND D.TS_Key = B.TSC_Key AND A.RUNNUMBER=%d
        """ % (self.RunNumber,)
        try:
            self.curs.execute(KeyQuery)
            self.L1_HLT_Key,self.HLT_Key,self.GTRS_Key,self.TSC_Key,self.ConfigId,self.GT_Key = self.curs.fetchone()
        except:
            ##print "Unable to get L1 and HLT keys for this run"
            pass
        
        
    def UpdateRateTable(self):  # lets not rebuild the rate table every time, rather just append new LSs
        pass

    def GetHLTRates(self,LSRange):
        self.GetHLTPrescaleMatrix()
        
        sqlquery = """SELECT SUM(A.L1PASS),SUM(A.PSPASS),SUM(A.PACCEPT)
        ,SUM(A.PEXCEPT), A.LSNUMBER, (SELECT L.NAME FROM CMS_HLT.PATHS L WHERE L.PATHID=A.PATHID) PATHNAME 
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A WHERE RUNNUMBER=%s AND A.LSNUMBER IN %s
        GROUP BY A.LSNUMBER,A.PATHID"""

        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")
                           
        StartLS = LSRange[0]
        EndLS   = LSRange[-1]
        LSUsed={}
        for lumisection in LSRange:
            LSUsed[lumisection]=False
        
        AvgL1Prescales = [0]*self.nAlgoBits
        
        #print "Getting HLT Rates for LS from %d to %d" % (LSRange[0],LSRange[-1],)

        query = sqlquery % (self.RunNumber,LSRangeSTR)
        self.curs.execute(query)

        TriggerRates = {}
        for L1Pass,PSPass,HLTPass,HLTExcept,LS ,name in self.curs.fetchall():
            if not self.HLTSeed.has_key(name):
                continue 
            
            rate = HLTPass/23.3
            hltps = 0

            if not TriggerRates.has_key(name):                
                try:
                    psi = self.PSColumnByLS[LS]
                except:
                    print "HLT in: Cannot figure out PSI for LS "+str(StartLS)+"  setting to 0"
                    print "The value of LSRange[0] is:"
                    print str(LS)
                    psi = 0
                if psi is None:
                    psi=0
                if self.HLTPrescaleTable.has_key(name):
                    hltps = self.HLTPrescaleTable[name][psi]
                else:
                    if PSPass:
                        hltps = float(L1Pass)/PSPass
                if self.L1IndexNameMap.has_key(self.HLTSeed[name]):
                    l1ps = self.L1PrescaleTable[self.L1IndexNameMap[self.HLTSeed[name]]][psi]
                else:
                    AvL1Prescales = self.CalculateAvL1Prescales([LS])
                    l1ps = self.UnwindORSeed(self.HLTSeed[name],AvL1Prescales)

                ps = l1ps*hltps
                
                ###if ps < 1: ### want PS=0 too! 
                    #print "Oops! somehow ps for "+str(name)+" = "+str(ps)+", where L1 PS = "+str(l1ps)+" and HLT PS = "+str(hltps)
                #    ps = 1
                psrate = ps*rate
                TriggerRates[name]= [ps,rate,psrate,1]
                LSUsed[LS]=True
                
            else:                
                [ops,orate,opsrate,on] = TriggerRates[name]
                try:
                    psi = self.PSColumnByLS[LSRange[on]]
                except:
                    print "HLT out: Cannot figure out PSI for index "+str(on)+" setting to 0"
                    print "The value of LSRange[on] is:"
                    print str(LS)
                    psi = 0
                if psi is None:
                    psi=3
                if self.HLTPrescaleTable.has_key(name):
                    hltps = self.HLTPrescaleTable[name][psi]
                else:
                    if PSPass:
                        hltps = float(L1Pass)/PSPass
                if self.L1IndexNameMap.has_key(self.HLTSeed[name]):
                    l1ps = self.L1PrescaleTable[self.L1IndexNameMap[self.HLTSeed[name]]][psi]
                else:
                    AvL1Prescales = self.CalculateAvL1Prescales([LS])
                    l1ps = self.UnwindORSeed(self.HLTSeed[name],AvL1Prescales)

                ps = l1ps*hltps
                #if ps < 1: ###want PS=0 too!
                    ##print "Oops! somehow ps for "+str(name)+" = "+str(ps)+", where L1 PS = "+str(l1ps)+" and HLT PS = "+str(hltps)
                #    ps = 1
                psrate = ps*rate
                TriggerRates[name]= [ops+ps,orate+rate,opsrate+psrate,on+1]
                LSUsed[LS]=True
                
                    
        
        
        ###check if LS is used above, if not and deadtime is 100% add extra lumi for calculation
        lumirange_one=[]
        for key in LSUsed.iterkeys():
            lumirange_one=[key]##set LSRange equal to one LS so can get deadtime
            if LSUsed[key]:
                continue
            if self.GetDeadTimeBeamActive(lumirange_one)<=0.9999:
                ##print "LS",key,"gottcha", LSUsed[key]
                LSUsed[key]=True
                print "Some strange error LS",key, "has deadtime ", self.GetDeadTimeBeamActive(lumirange_one)
            else:
                print "increasing # LS by one, LS", key, "has 100% deadtime"
                for name,val in TriggerRates.iteritems():
                    [ops,orate,opsrate,on] = TriggerRates[name]
                    TriggerRates[name]= [ops,orate,opsrate,on+1]
                    
        for name,val in TriggerRates.iteritems():
            [ps,rate,psrate,n] = val
            avps = ps/n
            try:
                ps = psrate/rate
            except:
                #print "Rate = 0 for "+str(name)+", setting ps to 1"
                ps = avps
                
            TriggerRates[name] = [avps,ps,rate/n,psrate/n]
                    
        return TriggerRates

    def GetAvgTrigRateInLSRange(self,triggerName,LSRange):
        sqlquery = """SELECT A.PACCEPT
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A, CMS_HLT.PATHS B
        WHERE RUNNUMBER=%s AND B.NAME = \'%s\' AND A.PATHID = B.PATHID AND A.LSNUMBER IN %s
        """

        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")

        query = sqlquery % (self.RunNumber,triggerName,LSRangeSTR)
        self.curs.execute(query)
        avg_rate = sum([counts[0] for counts in self.curs.fetchall()])/ (23.3 * len(LSRange))

        return avg_rate

    def GetTrigRatesInLSRange(self,triggerName,LSRange):
        sqlquery = """SELECT A.LSNUMBER, A.PACCEPT
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A, CMS_HLT.PATHS B
        WHERE RUNNUMBER=%s AND B.NAME = \'%s\' AND A.PATHID = B.PATHID AND A.LSNUMBER IN %s
        ORDER BY A.LSNUMBER
        """

        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")

        query = sqlquery % (self.RunNumber,triggerName,LSRangeSTR)
        self.curs.execute(query)
        r={}
        for ls,accept in  self.curs.fetchall():
            r[ls] = accept/23.3
        return r
    
    def GetTriggerRatesByLS(self,triggerName):
        sqlquery = """SELECT A.LSNUMBER, A.PACCEPT
        FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A, CMS_HLT.PATHS B
        WHERE RUNNUMBER=%s AND B.NAME = \'%s\' AND A.PATHID = B.PATHID
        """ % (self.RunNumber,triggerName,)

        self.curs.execute(sqlquery)
        r={}
        for ls,accept in  self.curs.fetchall():
            r[ls] = accept/23.3
        return r
    
    def GetAllTriggerRatesByLS(self):
        for hltName in self.HLTSeed:
            self.HLTRatesByLS[hltName] = self.GetTriggerRatesByLS(hltName)

    def GetPSColumnsInLSRange(self,LSRange):
        sqlquery="""SELECT LUMI_SECTION,PRESCALE_INDEX FROM
        CMS_GT_MON.LUMI_SECTIONS B WHERE B.RUN_NUMBER=%s AND B.LUMI_SECTION IN %s"""        

        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")
        query = sqlquery % (self.RunNumber,LSRangeSTR)
        self.curs.execute(query)

        ps_columns={}
        for ls, ps_index in self.curs.fetchall():
            ps_columns[ls] = ps_index

        return ps_columns

    def GetAvDeliveredLumi(self,LSRange):
        sqlquery="""SELECT DELIVLUMI FROM
        CMS_RUNTIME_LOGGER.LUMI_SECTIONS A WHERE A.RUNNUMBER=%s AND A.LUMISECTION IN %s"""        

        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")
        query = sqlquery % (self.RunNumber,LSRangeSTR)
        self.curs.execute(query)

        delivered = [val[0] for val in self.curs.fetchall()]
        avg_delivered = sum(delivered)/len(LSRange)

        return avg_delivered

    def GetLumiInfo(self):
        
        sqlquery="""SELECT RUNNUMBER,LUMISECTION,PRESCALE_INDEX,INSTLUMI,LIVELUMI,DELIVLUMI,DEADTIME
        ,DCSSTATUS,PHYSICS_FLAG,CMS_ACTIVE
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_GT_MON.LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
        AND B.RUN_NUMBER(+)=A.RUNNUMBER AND B.LUMI_SECTION(+)=A.LUMISECTION AND A.LUMISECTION > %d
        ORDER BY A.RUNNUMBER,A.LUMISECTION"""

        ## Get the lumi information for the run, just update the table, don't rebuild it every time
        query = sqlquery % (self.RunNumber,self.LastLSParsed)
        self.curs.execute(query)
        
        pastLSCol=-1
        for run,ls,psi,inst,live,dlive,dt,dcs,phys,active in self.curs.fetchall():
            if psi is None:
                psi = GetLastKnownPSIndex(self.PSColumnByLS)

            self.PSColumnByLS[ls]=psi
            self.InstLumiByLS[ls]=inst
            self.LiveLumiByLS[ls]=live
            self.DeliveredLumiByLS[ls]=dlive
            self.DeadTime[ls]=dt
            self.Physics[ls]=phys
            self.Active[ls]=active
            
            if pastLSCol!=-1 and ls!=pastLSCol:
                self.PSColumnChanges.append([ls,psi])
            pastLSCol=ls
            if ls>self.LastLSParsed:
                self.LastLSParsed=ls
                
        self.LumiInfo = [self.PSColumnByLS, self.InstLumiByLS, self.DeliveredLumiByLS, self.LiveLumiByLS, self.DeadTime, self.Physics, self.Active]

        return self.LumiInfo

    def GetMoreLumiInfo(self):
        sqlquery="""SELECT RUNNUMBER,LUMISECTION,BEAM1_PRESENT, BEAM2_PRESENT, BEAM1_STABLE, BEAM2_STABLE, EBP_READY,EBM_READY,EEP_READY,EEM_READY,HBHEA_READY,HBHEB_READY,HBHEC_READY,HF_READY,RPC_READY,DT0_READY,DTP_READY,DTM_READY,CSCP_READY,CSCM_READY,TOB_READY,TIBTID_READY,TECP_READY,TECM_READY,BPIX_READY,FPIX_READY,ESP_READY,ESM_READY
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_GT_MON.LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
        AND B.RUN_NUMBER(+)=A.RUNNUMBER AND B.LUMI_SECTION(+)=A.LUMISECTION AND A.LUMISECTION > %d
        ORDER BY A.RUNNUMBER,A.LUMISECTION"""

        ## Get the lumi information for the run, just update the table, don't rebuild it every time
        query = sqlquery % (self.RunNumber,self.LastLSParsed)
        self.curs.execute(query)
        pastLSCol=-1
        for run,ls,b1pres,b2pres,b1stab,b2stab,ebp,ebm,eep,eem,hbhea,hbheb,hbhec,hf,rpc,dt0,dtp,dtm,cscp,cscm,tob,tibtid,tecp,tecm,bpix,fpix,esp,esm in self.curs.fetchall():

            self.B1Pres[ls]=b1pres
            self.B2Pres[ls]=b2pres
            self.B1Stab[ls]=b1stab
            self.B2Stab[ls]=b2stab
            self.EBP[ls]= ebp
            self.EBM[ls] = ebm
            self.EEP[ls] = eep
            self.EEM[ls] = eem
            self.HBHEA[ls] = hbhea
            self.HBHEB[ls] = hbheb
            self.HBHEC[ls] = hbhec
            self.HF[ls] = hf
            self.RPC[ls] = rpc
            self.DT0[ls] = dt0
            self.DTP[ls] = dtp
            self.DTM[ls] = dtm
            self.CSCP[ls] = cscp
            self.CSCM[ls] = cscm
            self.TOB[ls] = tob
            self.TIBTID[ls]= tibtid
            self.TECP[ls] = tecp
            self.TECM[ls] = tecm
            self.BPIX[ls] = bpix
            self.FPIX[ls] = fpix
            self.ESP[ls] = esp
            self.ESM[ls] = esm

                  
            pastLSCol=ls
            if ls>self.LastLSParsed:
                self.LastLSParsed=ls

        
        
        self.MoreLumiInfo ={'b1pres':self.B1Pres,'b2pres':self.B2Pres,'b1stab':self.B1Stab,'b2stab':self.B2Stab,'ebp':self.EBP,'ebm':self.EBM,'eep':self.EEP,'eem':self.EEM,'hbhea':self.HBHEA,'hbheb':self.HBHEB,'hbhec':self.HBHEC,'hf':self.HF,'rpc':self.RPC,'dt0':self.DT0,'dtp':self.DTP,'dtm':self.DTM,'cscp':self.CSCP,'cscm':self.CSCM,'tob':self.TOB,'tibtid':self.TIBTID,'tecp':self.TECP,'tecm':self.TECM,'bpix':self.BPIX,'fpix':self.FPIX,'esp':self.ESP,'esm':self.ESM}
                
        return self.MoreLumiInfo


    def GetL1HLTseeds(self):
        #print self.HLTSeed
        L1HLTseeds={}
        for HLTkey in self.HLTSeed.iterkeys():
            #print HLTkey, self.HLTSeed[HLTkey]
            
            dummy=str(self.HLTSeed[HLTkey])
            
            if dummy.find(" OR ") == -1:
                dummylist=[]
                dummylist.append(dummy)
                L1HLTseeds[StripVersion(HLTkey)]=dummylist
                continue  # Not an OR of seeds
            seedList = dummy.split(" OR ")
            #print seedList
            L1HLTseeds[StripVersion(HLTkey)]=seedList
            if len(seedList)==1:
                print "error: zero length L1 seed"
                continue #shouldn't get here
        #print L1HLTseeds
        
        return L1HLTseeds
        
    def GetDeadTimeBeamActive(self,LSRange):
        sqlquery=""" select FRACTION
        from
        CMS_GT_MON.V_SCALERS_TCS_DEADTIME
        where
        RUN_NUMBER=%s and
        LUMI_SECTION in %s and
        SCALER_NAME='DeadtimeBeamActive'"""

        
        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")
                           
        query=sqlquery %(self.RunNumber,LSRangeSTR)
        #print query
        self.curs.execute(query)

        deadtimeba_sum=0
        ii=0
        for deadtimebeamactive in self.curs.fetchall():
            try:
                deadtimeba_sum=deadtimeba_sum+deadtimebeamactive[0]
            except:
                ##print "no dtba for run ",self.RunNumber, ", ls ",LSRange[ii], "using dt"
                deadtimeba_sum=deadtimeba_sum+self.GetDeadTime(LSRange[ii])
            ii=ii+1
        deadtimeba_av=deadtimeba_sum/len(LSRange)
        
        return deadtimeba_av


            
    def GetDeadTime(self,LS):
        sqlquery=""" select FRACTION
        from
        CMS_GT_MON.V_SCALERS_TCS_DEADTIME
        where
        RUN_NUMBER=%s and
        LUMI_SECTION=%s and
        SCALER_NAME='Deadtime'"""
                           
        query=sqlquery %(self.RunNumber,LS)
        #print query
        self.curs.execute(query)
        dt=1.0
        for deadtime in self.curs.fetchall():
            try:
                dt=deadtime[0]
                #print "dt=",dt
            except:
                print "no dt for run ",self.RunNumber, ", ls ",LS
                dt=1.0
        
        
        return dt

    def GetAvLumiInfo(self,LSRange):
        nLS=0;
        AvInstLumi=0
        try:
            StartLS = LSRange[0]
            EndLS   = LSRange[-1]
            
            #print "startls=",StartLS, "endls=",EndLS
            try: ## Cosmics won't have lumi info
                maxlive = self.LiveLumiByLS[EndLS]
                maxdelivered = self.DeliveredLumiByLS[EndLS]
                for iterator in LSRange:
                    if self.LiveLumiByLS[iterator] > maxlive:
                        maxlive = self.LiveLumiByLS[iterator]
                    if self.DeliveredLumiByLS[iterator] > maxdelivered:
                        maxdelivered = self.DeliveredLumiByLS[iterator]
                AvLiveLumi=maxlive-self.LiveLumiByLS[StartLS]
                AvDeliveredLumi=maxdelivered-self.DeliveredLumiByLS[StartLS]
            except:
                AvLiveLumi=0
                AvDeliveredLumi=0

            if AvDeliveredLumi > 0:
                AvDeadTime = 1 - AvLiveLumi/AvDeliveredLumi
            else:
                if AvLiveLumi > 0:
                    print "Live Lumi > 0 but Delivered <= 0: problem"
                AvDeadTime = 0.0
            PSCols=[]
            for ls in LSRange:
                try:
                    try:
                        AvInstLumi+=self.InstLumiByLS[ls]
                    except:
                        pass
                    PSCols.append(self.PSColumnByLS[ls])
                    nLS+=1
                except:
                    print "ERROR: Lumi section "+str(ls)+" not in bounds"
                    return [0.,0.,0.,0.,[]]
            return [AvInstLumi/nLS,(1000.0/23.3)*AvLiveLumi/(EndLS-StartLS),(1000.0/23.3)*AvDeliveredLumi/(EndLS-StartLS), AvDeadTime,PSCols]
        except:
            if LSRange[0] == LSRange[-1]:
                AvInstLumi = self.InstLumiByLS[StartLS]
                try:
                    AvLiveLumi = self.LiveLumiByLS[StartLS]-self.LiveLumiByLS[StartLS-1]
                    AvDeliveredLumi = self.DeliveredLumiByLS[StartLS]-self.DeliveredLumiByLS[StartLS-1]
                    
                except:
                    try:
                        AvLiveLumi = self.LiveLumiByLS[StartLS+1]-self.LiveLumiByLS[StartLS]
                        AvDeliveredLumi = self.DeliveredLumiByLS[StartLS+1]-self.DeliveredLumiByLS[StartLS]
                    except:
                        print "missing live/delivered run ",self.RunNumber, "ls ",LSRange
                        AvLiveLumi = 0
                        AvDeliveredLumi = 0
                if AvDeliveredLumi > 0:
                    AvDeadTime = 1 - AvLiveLumi/AvDeliveredLumi
                  
                elif AvLiveLumi > 0:
                    print "Live Lumi > 0 but Delivered <= 0: problem run ",self.RunNumber, " ls ",LSRange 
                    AvDeadTime = 1.0
                else:
                    AvDeadTime=1.0
                PSCols = [self.PSColumnByLS[StartLS]]
                return [AvInstLumi,(1000.0/23.3)*AvLiveLumi,(1000.0/23.3)*AvDeliveredLumi,AvDeadTime,PSCols]
            else:
                return [0.,0.,0.,0.,[]]

    def ParsePSColumnPage(self): ## this is now done automatically when we read the db
        pass

    def GetL1NameIndexAssoc(self):
        ## get the L1 algo names associated with each algo bit
        AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
        WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
        ORDER BY ALGO_INDEX""" % (self.GT_Key,)
        self.curs.execute(AlgoNameQuery)
        for index,name in self.curs.fetchall():
            self.L1IndexNameMap[name] = index
            
    def GetL1AlgoPrescales(self):
        L1PrescalesQuery= """
        SELECT
        PRESCALE_FACTOR_ALGO_000,PRESCALE_FACTOR_ALGO_001,PRESCALE_FACTOR_ALGO_002,PRESCALE_FACTOR_ALGO_003,PRESCALE_FACTOR_ALGO_004,PRESCALE_FACTOR_ALGO_005,
        PRESCALE_FACTOR_ALGO_006,PRESCALE_FACTOR_ALGO_007,PRESCALE_FACTOR_ALGO_008,PRESCALE_FACTOR_ALGO_009,PRESCALE_FACTOR_ALGO_010,PRESCALE_FACTOR_ALGO_011,
        PRESCALE_FACTOR_ALGO_012,PRESCALE_FACTOR_ALGO_013,PRESCALE_FACTOR_ALGO_014,PRESCALE_FACTOR_ALGO_015,PRESCALE_FACTOR_ALGO_016,PRESCALE_FACTOR_ALGO_017,
        PRESCALE_FACTOR_ALGO_018,PRESCALE_FACTOR_ALGO_019,PRESCALE_FACTOR_ALGO_020,PRESCALE_FACTOR_ALGO_021,PRESCALE_FACTOR_ALGO_022,PRESCALE_FACTOR_ALGO_023,
        PRESCALE_FACTOR_ALGO_024,PRESCALE_FACTOR_ALGO_025,PRESCALE_FACTOR_ALGO_026,PRESCALE_FACTOR_ALGO_027,PRESCALE_FACTOR_ALGO_028,PRESCALE_FACTOR_ALGO_029,
        PRESCALE_FACTOR_ALGO_030,PRESCALE_FACTOR_ALGO_031,PRESCALE_FACTOR_ALGO_032,PRESCALE_FACTOR_ALGO_033,PRESCALE_FACTOR_ALGO_034,PRESCALE_FACTOR_ALGO_035,
        PRESCALE_FACTOR_ALGO_036,PRESCALE_FACTOR_ALGO_037,PRESCALE_FACTOR_ALGO_038,PRESCALE_FACTOR_ALGO_039,PRESCALE_FACTOR_ALGO_040,PRESCALE_FACTOR_ALGO_041,
        PRESCALE_FACTOR_ALGO_042,PRESCALE_FACTOR_ALGO_043,PRESCALE_FACTOR_ALGO_044,PRESCALE_FACTOR_ALGO_045,PRESCALE_FACTOR_ALGO_046,PRESCALE_FACTOR_ALGO_047,
        PRESCALE_FACTOR_ALGO_048,PRESCALE_FACTOR_ALGO_049,PRESCALE_FACTOR_ALGO_050,PRESCALE_FACTOR_ALGO_051,PRESCALE_FACTOR_ALGO_052,PRESCALE_FACTOR_ALGO_053,
        PRESCALE_FACTOR_ALGO_054,PRESCALE_FACTOR_ALGO_055,PRESCALE_FACTOR_ALGO_056,PRESCALE_FACTOR_ALGO_057,PRESCALE_FACTOR_ALGO_058,PRESCALE_FACTOR_ALGO_059,
        PRESCALE_FACTOR_ALGO_060,PRESCALE_FACTOR_ALGO_061,PRESCALE_FACTOR_ALGO_062,PRESCALE_FACTOR_ALGO_063,PRESCALE_FACTOR_ALGO_064,PRESCALE_FACTOR_ALGO_065,
        PRESCALE_FACTOR_ALGO_066,PRESCALE_FACTOR_ALGO_067,PRESCALE_FACTOR_ALGO_068,PRESCALE_FACTOR_ALGO_069,PRESCALE_FACTOR_ALGO_070,PRESCALE_FACTOR_ALGO_071,
        PRESCALE_FACTOR_ALGO_072,PRESCALE_FACTOR_ALGO_073,PRESCALE_FACTOR_ALGO_074,PRESCALE_FACTOR_ALGO_075,PRESCALE_FACTOR_ALGO_076,PRESCALE_FACTOR_ALGO_077,
        PRESCALE_FACTOR_ALGO_078,PRESCALE_FACTOR_ALGO_079,PRESCALE_FACTOR_ALGO_080,PRESCALE_FACTOR_ALGO_081,PRESCALE_FACTOR_ALGO_082,PRESCALE_FACTOR_ALGO_083,
        PRESCALE_FACTOR_ALGO_084,PRESCALE_FACTOR_ALGO_085,PRESCALE_FACTOR_ALGO_086,PRESCALE_FACTOR_ALGO_087,PRESCALE_FACTOR_ALGO_088,PRESCALE_FACTOR_ALGO_089,
        PRESCALE_FACTOR_ALGO_090,PRESCALE_FACTOR_ALGO_091,PRESCALE_FACTOR_ALGO_092,PRESCALE_FACTOR_ALGO_093,PRESCALE_FACTOR_ALGO_094,PRESCALE_FACTOR_ALGO_095,
        PRESCALE_FACTOR_ALGO_096,PRESCALE_FACTOR_ALGO_097,PRESCALE_FACTOR_ALGO_098,PRESCALE_FACTOR_ALGO_099,PRESCALE_FACTOR_ALGO_100,PRESCALE_FACTOR_ALGO_101,
        PRESCALE_FACTOR_ALGO_102,PRESCALE_FACTOR_ALGO_103,PRESCALE_FACTOR_ALGO_104,PRESCALE_FACTOR_ALGO_105,PRESCALE_FACTOR_ALGO_106,PRESCALE_FACTOR_ALGO_107,
        PRESCALE_FACTOR_ALGO_108,PRESCALE_FACTOR_ALGO_109,PRESCALE_FACTOR_ALGO_110,PRESCALE_FACTOR_ALGO_111,PRESCALE_FACTOR_ALGO_112,PRESCALE_FACTOR_ALGO_113,
        PRESCALE_FACTOR_ALGO_114,PRESCALE_FACTOR_ALGO_115,PRESCALE_FACTOR_ALGO_116,PRESCALE_FACTOR_ALGO_117,PRESCALE_FACTOR_ALGO_118,PRESCALE_FACTOR_ALGO_119,
        PRESCALE_FACTOR_ALGO_120,PRESCALE_FACTOR_ALGO_121,PRESCALE_FACTOR_ALGO_122,PRESCALE_FACTOR_ALGO_123,PRESCALE_FACTOR_ALGO_124,PRESCALE_FACTOR_ALGO_125,
        PRESCALE_FACTOR_ALGO_126,PRESCALE_FACTOR_ALGO_127
        FROM CMS_GT.GT_FDL_PRESCALE_FACTORS_ALGO A, CMS_GT.GT_RUN_SETTINGS_PRESC_VIEW B
        WHERE A.ID=B.PRESCALE_FACTORS_ALGO_FK AND B.ID='%s'
        """ % (self.GTRS_Key,)
        self.curs.execute(L1PrescalesQuery)
        ## This is pretty horrible, but this how you get them!!
        tmp = self.curs.fetchall()
        self.L1PrescaleTable = []
        for ps in tmp[0]: #build the prescale table initially
            self.L1PrescaleTable.append([ps])
        for line in tmp[1:]: # now fill it
            for ps,index in zip(line,range(len(line))):
                self.L1PrescaleTable[index].append(ps)
        self.nAlgoBits=128

    def GetHLTIndex(self,name):
        for i,n in enumerate(self.HLTList):
            if n.find(name)!=-1:
                return i
        #print name
        return -1

    def GetHLTPrescaleMatrix(self):
        tmp_curs = ConnectDB('hlt')
        configIDQuery = "SELECT CONFIGID FROM CMS_HLT.CONFIGURATIONS WHERE CONFIGDESCRIPTOR='%s'" % (self.HLT_Key)
        tmp_curs.execute(configIDQuery)                                                                                                                                                
        ConfigId, = tmp_curs.fetchone()

        SequencePathQuery ="""                                                                                                                                                       
        SELECT F.SEQUENCENB,J.VALUE TRIGGERNAME                                                                                                                                      
        FROM CMS_HLT.CONFIGURATIONSERVICEASSOC A                                                                                                                                     
        , CMS_HLT.SERVICES B                                                                                                                                                         
        , CMS_HLT.SERVICETEMPLATES C                                                                                                                                                 
        , CMS_HLT.SUPERIDVECPARAMSETASSOC D                                                                                                                                          
        , CMS_HLT.VECPARAMETERSETS E                                                                                                                                                 
        , CMS_HLT.SUPERIDPARAMSETASSOC F                                                                                                                                             
        , CMS_HLT.PARAMETERSETS G                                                                                                                                                    
        , CMS_HLT.SUPERIDPARAMETERASSOC H                                                                                                                                            
        , CMS_HLT.PARAMETERS I                                                                                                                                                       
        , CMS_HLT.STRINGPARAMVALUES J                                                                                                                                                
        WHERE A.CONFIGID=%d                                                                                                                                                         
        AND A.SERVICEID=B.SUPERID                                                                                                                                                    
        AND B.TEMPLATEID=C.SUPERID                                                                                                                                                   
        AND C.NAME='PrescaleService'                                                                                                                                                 
        AND B.SUPERID=D.SUPERID                                                                                                                                                      
        AND D.VPSETID=E.SUPERID                                                                                                                                                      
        AND E.NAME='prescaleTable'                                                                                                                                                   
        AND D.VPSETID=F.SUPERID                                                                                                                                                      
        AND F.PSETID=G.SUPERID                                                                                                                                                       
        AND G.SUPERID=H.SUPERID                                                                                                                                                      
        AND I.PARAMID=H.PARAMID                                                                                                                                                      
        AND I.NAME='pathName'                                                                                                                                                        
        AND J.PARAMID=H.PARAMID
        ORDER BY F.SEQUENCENB                                                                                                                                                        
        """ % (ConfigId,)

        tmp_curs.execute(SequencePathQuery)                                                                                                                                            
        HLTSequenceMap = {}                                                                                                                                                          
        for seq,name in tmp_curs.fetchall():                                                                                                                                           
            name = name.lstrip('"').rstrip('"')                                                                                                                                      
            HLTSequenceMap[seq]=name                                                                                                                                                 

        SequencePrescaleQuery="""                                                                                                                                                    
        SELECT F.SEQUENCENB,J.SEQUENCENB,J.VALUE                                                                                                                                     
        FROM CMS_HLT.CONFIGURATIONSERVICEASSOC A                                                                                                                                     
        , CMS_HLT.SERVICES B                                                                                                                                                         
        , CMS_HLT.SERVICETEMPLATES C                                                                                                                                                 
        , CMS_HLT.SUPERIDVECPARAMSETASSOC D                                                                                                                                          
        , CMS_HLT.VECPARAMETERSETS E                                                                                                                                                 
        , CMS_HLT.SUPERIDPARAMSETASSOC F                                                                                                                                             
        , CMS_HLT.PARAMETERSETS G                                                                                                                                                    
        , CMS_HLT.SUPERIDPARAMETERASSOC H                                                                                                                                            
        , CMS_HLT.PARAMETERS I                                                                                                                                                       
        , CMS_HLT.VUINT32PARAMVALUES J                                                                                                                                               
        WHERE A.CONFIGID=%d                                                                                                                                                          
        AND A.SERVICEID=B.SUPERID                                                                                                                                                    
        AND B.TEMPLATEID=C.SUPERID                                                                                                                                                   
        AND C.NAME='PrescaleService'
        AND B.SUPERID=D.SUPERID                                                                                                                                                       
        AND D.VPSETID=E.SUPERID                                                                                                                                                       
        AND E.NAME='prescaleTable'                                                                                                                                                    
        AND D.VPSETID=F.SUPERID                                                                                                                                                       
        AND F.PSETID=G.SUPERID                                                                                                                                                        
        AND G.SUPERID=H.SUPERID                                                                                                                                                       
        AND I.PARAMID=H.PARAMID                                                                                                                                                       
        AND I.NAME='prescales'                                                                                                                                                        
        AND J.PARAMID=H.PARAMID                                                                                                                                                       
        ORDER BY F.SEQUENCENB,J.SEQUENCENB                                                                                                                                            
        """ % (ConfigId,)                                                                                                                                                             

        tmp_curs.execute(SequencePrescaleQuery)                                                                                                                                         
        lastIndex=-1                                                                                                                                                                  
        lastSeq=-1                                                                                                                                                                    
        row = []                                                                                                                                                                      
        for seq,index,val in tmp_curs.fetchall():                                                                                                                                       
            if lastIndex!=index-1:                                                                                                                                                    
                self.HLTPrescaleTable[HLTSequenceMap[seq-1]] = row                                                                                                                         
                row=[]                                                                                                                                                                
            lastSeq=seq                                                                                                                                                               
            lastIndex=index                                                                                                                                                           
            row.append(val)
            

    def GetHLTSeeds(self):
        ## This is a rather delicate query, but it works!
        ## Essentially get a list of paths associated with the config, then find the module of type HLTLevel1GTSeed associated with the path
        ## Then find the parameter with field name L1SeedsLogicalExpression and look at the value
        ##
        ## NEED TO BE LOGGED IN AS CMS_HLT_R
        tmpcurs = ConnectDB('hlt')
        sqlquery ="""  
        SELECT I.NAME,A.VALUE
        FROM
        CMS_HLT.STRINGPARAMVALUES A,
        CMS_HLT.PARAMETERS B,
        CMS_HLT.SUPERIDPARAMETERASSOC C,
        CMS_HLT.MODULETEMPLATES D,
        CMS_HLT.MODULES E,
        CMS_HLT.PATHMODULEASSOC F,
        CMS_HLT.CONFIGURATIONPATHASSOC G,
        CMS_HLT.CONFIGURATIONS H,
        CMS_HLT.PATHS I
        WHERE
        A.PARAMID = C.PARAMID AND
        B.PARAMID = C.PARAMID AND
        B.NAME = 'L1SeedsLogicalExpression' AND
        C.SUPERID = F.MODULEID AND
        D.NAME = 'HLTLevel1GTSeed' AND
        E.TEMPLATEID = D.SUPERID AND
        F.MODULEID = E.SUPERID AND
        F.PATHID=G.PATHID AND
        I.PATHID=G.PATHID AND
        G.CONFIGID=H.CONFIGID AND
        H.CONFIGDESCRIPTOR='%s' 
        ORDER BY A.VALUE
        """ % (self.HLT_Key,)
        tmpcurs.execute(sqlquery)
        for HLTPath,L1Seed in tmpcurs.fetchall():
            if not self.HLTSeed.has_key(HLTPath): ## this should protect us from L1_SingleMuOpen
                self.HLTSeed[HLTPath] = L1Seed.lstrip('"').rstrip('"') 
        #self.GetHLTPrescaleMatrix(tmpcurs)

    def ParseRunSetup(self):
        #queries that need to be run only once per run
        self.GetRunInfo()
        self.GetL1NameIndexAssoc()
        self.GetL1AlgoPrescales()
        self.GetHLTSeeds()
        self.GetLumiInfo()
        self.LastLSParsed=-1
        self.GetMoreLumiInfo()
        self.LastLsParsed=-1
        #self.GetDeadTimeBeamActive()

    def UpdateRun(self,LSRange):
        self.GetLumiInfo()
        TriggerRates     = self.GetHLTRates(LSRange)
        #L1Prescales      = self.CalculateAvL1Prescales(LSRange)
        #TotalPrescales   = self.CalculateTotalPrescales(TriggerRates,L1Prescales)
        #UnprescaledRates = self.UnprescaleRates(TriggerRates,TotalPrescales)

        #return [UnprescaledRates, TotalPrescales, L1Prescales, TriggerRates]
        return TriggerRates
    
    def GetLSRange(self,StartLS, NLS,reqPhysics=True):
        """
        returns an array of valid LumiSections
        if NLS < 0, count backwards from StartLS
        """
        self.GetLumiInfo()
        LS=[]
        curLS=StartLS
        step = NLS/abs(NLS)
        NLS=abs(NLS)
        
        while len(LS)<NLS:
            if (curLS<0 and step<0) or (curLS>=self.LastLSParsed and step>0):
                break
            if curLS>=0 and curLS<self.LastLSParsed-1:
                if (not self.Physics.has_key(curLS) or not self.Active.has_key(curLS)) and reqPhysics:
                    break
                
                if not reqPhysics or (self.Physics[curLS] and self.Active[curLS]):
                    if step>0:
                        LS.append(curLS)
                    else:
                        LS.insert(0,curLS)
            curLS += step
        return LS

    def GetLastLS(self,phys=False):
        self.GetLumiInfo()
        
        try:
            if not phys:
                maxLS=-1
                for ls, active in self.Active.iteritems():
                    if active and ls>maxLS:
                        maxLS=ls
                if maxLS==-1:
                    return 0
                else:
                    return maxLS                             
                
            else:
                maxLS=-1
                for ls,phys in self.Physics.iteritems():
                    if phys and self.Active[ls] and ls > maxLS:
                        maxLS=ls
                if maxLS==-1:
                    return 0
                else:
                    return maxLS                             
        except:
            return 0

    def CalculateAvL1Prescales(self,LSRange):
        AvgL1Prescales = [0]*self.nAlgoBits
        for index in LSRange:
            psi = self.PSColumnByLS[index]
            if not psi:
                #print "L1: Cannot figure out PSI for LS "+str(index)+"  setting to 0"
                psi = 0
            for algo in range(self.nAlgoBits):
                AvgL1Prescales[algo]+=self.L1PrescaleTable[algo][psi]
        for i in range(len(AvgL1Prescales)):
            try:
                AvgL1Prescales[i] = AvgL1Prescales[i]/len(LSRange)
            except:
                AvgL1Prescales[i] = AvgL1Prescales[i]
        return AvgL1Prescales
    
    def CalculateTotalPrescales(self,TriggerRates, L1Prescales):
        AvgTotalPrescales={}
        for hltName,v in TriggerRates.iteritems():
            if not self.HLTSeed.has_key(hltName):
                continue 
            hltPS=0
            if len(v)>0:
                hltPS = v[0]
            l1Index=-1
            if self.L1IndexNameMap.has_key(self.HLTSeed[hltName]):
                l1Index = self.L1IndexNameMap[self.HLTSeed[hltName]]

            l1PS=0
            if l1Index==-1:
                l1PS = self.UnwindORSeed(self.HLTSeed[hltName],L1Prescales)
            else:
                l1PS = L1Prescales[l1Index]
            AvgTotalPrescales[hltName]=l1PS*hltPS
        return AvgTotalPrescales

    def UnwindORSeed(self,expression,L1Prescales):
        """
        Figures out the effective prescale for the OR of several seeds
        we take this to be the *LOWEST* prescale of the included seeds
        """
        if expression.find(" OR ") == -1:
            return -1  # Not an OR of seeds
        seedList = expression.split(" OR ")
        if len(seedList)==1:
            return -1 # Not an OR of seeds, really shouldn't get here...
        minPS = 99999999999
        for seed in seedList:
            if not self.L1IndexNameMap.has_key(seed):
                continue
            ps = L1Prescales[self.L1IndexNameMap[seed]]
            if ps:
                minPS = min(ps,minPS)
        if minPS==99999999999:
            return 0
        else:
            return minPS
    
    def UnprescaleRates(self,TriggerRates,TotalPrescales):
        UnprescaledRates = {}
        for hltName,v in TriggerRates.iteritems():
            if TotalPrescales.has_key(hltName):
                ps = TotalPrescales[hltName]
                if ps:                    
                    UnprescaledRates[hltName] = v[1]*ps
                else:
                    UnprescaledRates[hltName] = v[1]
            else:
                UnprescaledRates[hltName] = v[1]
        return UnprescaledRates

    def GetTotalL1Rates(self):
        query = "SELECT RUNNUMBER, LUMISEGMENTNR, L1ASPHYSICS/23.3 FROM CMS_WBM.LEVEL1_TRIGGER_CONDITIONS WHERE RUNNUMBER=%s" % self.RunNumber
        self.curs.execute(query)
        L1Rate = {}
        for LS,rate in self.curs.fetchall():
            psi = self.PSColumnByLS.get(LS,0)
            lumi = self.InstLumiByLS.get(LS,0)
            L1Rate[LS] = [rate,psi,lumi]
        return L1Rate

    def GetL1RatesALL(self,LSRange):
        ##ANCIENT COMMANDS THAT DO WHO KNOWS WHAT
        ##sqlquery = "SELECT RUN_NUMBER, LUMI_SECTION, RATE_HZ, SCALER_INDEX FROM CMS_GT_MON.V_SCALERS_TCS_TRIGGER WHERE RUN_NUMBER=%s AND LUMI_SECTION IN %s and SCALER_INDEX=9"
        ##sqlquery = "SELECT RUN_NUMBER, LUMI_SECTION, RATE_HZ, SCALER_INDEX FROM CMS_GT_MON.V_SCALERS_FDL_ALGO WHERE RUN_NUMBER=%s AND LUMI_SECTION IN %s and SCALER_INDEX IN (9,13, 71)"
        ##OLD VERSION THAT GETS PRE-DT RATE (used before 16/11/2012)
        ##sqlquery = "SELECT RUN_NUMBER, LUMI_SECTION, RATE_HZ, SCALER_INDEX FROM CMS_GT_MON.V_SCALERS_FDL_ALGO WHERE RUN_NUMBER=%s AND LUMI_SECTION IN %s"

        ##NEW VERSION THAT GETS POST-DT RATE (implemented 16/11/2012)
        sqlquery = "SELECT RUN_NUMBER, LUMI_SECTION, COUNT/23.3, BIT FROM (SELECT MOD(ROWNUM - 1, 128) BIT , TO_CHAR(A.MODIFICATIONTIME, 'YYYY.MM.DD HH24:MI:SS') TIME, C.COLUMN_VALUE COUNT, A.RUNNUMBER RUN_NUMBER, A.LSNUMBER LUMI_SECTION FROM CMS_RUNINFO.HLT_SUPERVISOR_L1_SCALARS A ,TABLE(A.DECISION_ARRAY) C WHERE A.RUNNUMBER = %s AND A.LSNUMBER IN %s )"
        
        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")
        
        query= sqlquery %(self.RunNumber,LSRangeSTR)
        self.curs.execute(query)
        L1RateAll=self.curs.fetchall()
        L1RatesBits={}
        ###initialize dict of L1 bits
        for L1seed in sorted(self.L1IndexNameMap.iterkeys()):
            L1RatesBits[self.L1IndexNameMap[L1seed]]=0
            
        ###sum dict of L1 bits 
        for line in L1RateAll:
            #if line[3] in self.L1IndexNameMap: ##do not fill if empty L1 key
            try:
                L1RatesBits[line[3]]=line[2]+L1RatesBits[line[3]]
            except:
                pass
                #print "not filling bit",line[3]
        ###divide by number of LS
        for name in self.L1IndexNameMap.iterkeys():
            L1RatesBits[self.L1IndexNameMap[name]]=L1RatesBits[self.L1IndexNameMap[name]]/len(LSRange)
            
        ###total L1 PS table
        L1PSdict={}
        counter=0
        for line in self.L1PrescaleTable:
            L1PSdict[counter]=line
            counter=counter+1

        ###av ps dict
        L1PSbits={}    
        for bit in L1PSdict.iterkeys():
            L1PSbits[bit]=0
        for bit in L1PSdict.iterkeys():
            for LS in LSRange:
                L1PSbits[bit]=L1PSbits[bit]+L1PSdict[bit][self.PSColumnByLS[LS]]
        for bit in L1PSbits.iterkeys():            
            L1PSbits[bit]=L1PSbits[bit]/len(LSRange)

        
        ###convert dict of L1 bits to dict of L1 names        
        L1RatesNames={}
        for name in self.L1IndexNameMap.iterkeys():
            dummy=[]
            dummy.append(L1PSbits[self.L1IndexNameMap[name]])
            dummy.append(L1PSbits[self.L1IndexNameMap[name]])
            dummy.append(L1RatesBits[self.L1IndexNameMap[name]])
            dummy.append(L1RatesBits[self.L1IndexNameMap[name]]*L1PSbits[self.L1IndexNameMap[name]])
            L1RatesNames[name+'_v1']=dummy
           
        return L1RatesNames


    def GetL1PSbyseed(self):
        #for name in self.L1IndexNameMap.iterkeys():
        #    print name, self.L1IndexNameMap[name], self.L1PrescaleTable[self.L1IndexNameMap[name]]
        #self.HLTSeed[name]

        #for name in self.HLTSeed:
        #    print name, self.HLTSeed[name]
        #self.L1PrescaleTable[self.L1IndexNameMap[self.HLTSeed[name]]][psi]
        L1HLTSeeds=self.GetL1HLTseeds()
        HLTL1PS={}
        for HLTkey in L1HLTSeeds.iterkeys():
            #print HLTkey, L1HLTSeeds[HLTkey]
            dict={}
            for L1seed in L1HLTSeeds[HLTkey]:
                
                #try:
                #    print L1seed, L1HLTSeeds[HLTkey], self.L1PrescaleTable[self.L1IndexNameMap[L1seed]]
                #except:
                #    print 'fail'
                
                try:
                    dict[L1seed]=self.L1PrescaleTable[self.L1IndexNameMap[L1seed]]
                    
                except:
                    
                    dummylist=[]
                    for i in range(0,len(self.L1PrescaleTable[0])):
                        dummylist.append(1)
                    dict[L1seed]=dummylist
                    
                    #exit(2)
            #print HLTkey, dict    
            
            HLTL1PS[HLTkey]=dict
        #for HLTkey in HLTL1PS.iterkeys():
        #    print HLTkey, HLTL1PS[HLTkey]
        return HLTL1PS    

    def GetL1Rates(self,LSRange):

        sqlquery = "SELECT RUN_NUMBER, LUMI_SECTION, SCALER_NAME, RATE_HZ FROM CMS_GT_MON.V_SCALERS_TCS_TRIGGER WHERE RUN_NUMBER=%s and SCALER_NAME='L1AsPhysics' and LUMI_SECTION in %s"
         
        LSRangeSTR = str(LSRange)
        LSRangeSTR = LSRangeSTR.replace("[","(")
        LSRangeSTR = LSRangeSTR.replace("]",")")
                           
        query=sqlquery %(self.RunNumber, LSRangeSTR)

        #print query
        self.curs.execute(query)

        L1Rate=self.curs.fetchall()

        for line in L1Rate:
            #print line
            pass

        
        
        return L1Rate
    
    def AssemblePrescaleValues(self): ##Depends on output from ParseLumiPage and ParseTriggerModePage
        return ## WHAT DOES THIS FUNCTION DO???
        MissingName = "Nemo"
        for key in self.L1TriggerMode:
            self.L1Prescale[key] = {}
            for n in range(min(self.LSByLS),max(self.LSByLS)+1): #"range()" excludes the last element
                try:
                    self.L1Prescale[key][n] = self.L1TriggerMode[key][self.PSColumnByLS[n]]
                except:
                    if not key == MissingName:
                        self.MissingPrescale.append(key)
                        MissingName = key
                    if not n < 2:
                        print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

        for key in self.HLTTriggerMode:
            self.HLTPrescale[key] = {}
            for n in range(min(self.LSByLS),max(self.LSByLS)+1): #"range" excludes the last element
                try:
                    self.HLTPrescale[key][n] = self.HLTTriggerMode[key][self.PSColumnByLS[n]]
                except:
                    if not key == MissingName:
                        self.MissingPrescale.append(key)
                        MissingName = key
                    if not n < 2:
                        print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

        self.PrescaleValues = [self.L1Prescale,self.HLTPrescale,self.MissingPrescale]
        return self.PrescaleValues

    def ComputeTotalPrescales(self,StartLS,EndLS):
        return ## WHAT DOES THIS FUNCTION DO??
        IdealHLTPrescale = {}
        IdealPrescale = {}
        L1_zero = {}
        HLT_zero = {}
        n1 = {}
        n2 = {}
        L1 = {}
        L2 = {}
        H1 = {}
        H2 = {}
        InitialColumnIndex = self.PSColumnByLS[int(StartLS)]

        for key in self.HLTTriggerMode:
            try:
                DoesThisPathHaveAValidL1SeedWithPrescale = self.L1Prescale[self.HLTSeed[key]][StartLS]
            except:
                L1_zero[key] = True
                HLT_zero[key] = False
                continue

            IdealHLTPrescale[key] = 0.0
            IdealPrescale[key] = 0.0
            n1[key] = 0
            L1_zero[key] = False
            HLT_zero[key] = False

            for LSIterator in range(StartLS,EndLS+1): #"range" excludes the last element
                if self.L1Prescale[self.HLTSeed[key]][LSIterator] > 0 and self.HLTPrescale[key][LSIterator] > 0:
                    IdealPrescale[key]+=1.0/(self.L1Prescale[self.HLTSeed[key]][LSIterator]*self.HLTPrescale[key][LSIterator])
                else:
                    IdealPrescale[key]+=1.0 ##To prevent a divide by 0 error later
                    if self.L1Prescale[self.HLTSeed[key]][LSIterator] < 0.1:
                        L1_zero[key] = True
                    if self.HLTPrescale[key][LSIterator] < 0.1:
                        HLT_zero[key] = True
                if self.PSColumnByLS[LSIterator] == InitialColumnIndex:
                    n1[key]+=1

            if L1_zero[key] == True or HLT_zero[key] == True:
                continue

            IdealPrescale[key] = (EndLS + 1 - StartLS)/IdealPrescale[key]

            n2[key] = float(EndLS + 1 - StartLS - n1[key])
            L1[key] = float(self.L1Prescale[self.HLTSeed[key]][StartLS])
            L2[key] = float(self.L1Prescale[self.HLTSeed[key]][EndLS])
            H1[key] = float(self.HLTPrescale[key][StartLS])
            H2[key] = float(self.HLTPrescale[key][EndLS])

            IdealHLTPrescale[key] = ((n1[key]/L1[key])+(n2[key]/L2[key]))/((n1[key]/(L1[key]*H1[key]))+(n2[key]/(L2[key]*H2[key])))

        self.TotalPSInfo = [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2]

        return self.TotalPSInfo

        
    def CorrectForPrescaleChange(self,StartLS,EndLS):
        [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2] = self.TotalPSInfo
        xLS = {}
        RealPrescale = {}

        for key in self.HLTTriggerMode:
            if L1_zero[key] == True or HLT_zero[key] == True:
                continue
            [TriggerRate,L1Pass,PSPass,PS,Seed,StartLS,EndLS] = self.TriggerRates[key]
            if PS > 0.95 * IdealHLTPrescale[key] and PS < 1.05 * IdealHLTPrescale[key]:
                RealPrescale[key] = IdealPrescale[key]
                continue
                
            if H1[key] == H2[key] and L1[key] == L2[key] and not EndLS > max(self.LSByLS) - 1: ##Look for prescale change into the next LS
                H2[key] = float(self.HLTPrescale[key][EndLS+1])
                L2[key] = float(self.L1Prescale[self.HLTSeed[key]][EndLS+1])
            if H1[key] == H2[key] and L1[key] == L2[key] and not StartLS < 3:
                H1[key] = float(self.HLTPrescale[key][StartLS-1])
                L1[key] = float(self.L1Prescale[self.HLTSeed[key]][StartLS-1])
            if H1[key] == H2[key]:
                xLS[key] = 0
            else:
                xLS[key] = ((-(PS/IdealHLTPrescale[key])*(L2[key]*n1[key]+L1[key]*n2[key])*(H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key]))+((H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key])*(L2[key]*n1[key]+L1[key]*n2[key])))/(((PS/IdealHLTPrescale[key])*(L2[key]*n1[key]+L1[key]*n2[key])*(H1[key]*L1[key]-H2[key]*L2[key]))+((H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key])*(L2[key]-L1[key])))

            if xLS[key] > 1:
                xLS[key] = 1
            if xLS[key] < -1:
                xLS[key] = -1
            RealPrescale[key] = (n1[key] + n2[key])/(((n1[key] - xLS[key])/(H1[key]*L1[key]))+(n2[key]+xLS[key])/(H2[key]*L2[key]))

        self.CorrectedPSInfo = [RealPrescale,xLS,L1,L2,H1,H2]

        return self.CorrectedPSInfo
        
    def GetAvLumiPerRange(self, NMergeLumis=10):
        """
        This function returns a per-LS table of the average lumi of the previous NMergeLumis LS
        """
        AvLumiRange = []
        AvLumiTable = {}
        for ls,lumi in self.InstLumiByLS.iteritems():
            try:
                AvLumiRange.append(int(lumi))
            except:
                continue
            if len(AvLumiRange) == NMergeLumis:
                AvLumiRange = AvLumiRange[1:]
                AvLumiTable[ls] = sum(AvLumiRange)/NMergeLumis
        return AvLumiTable
        
    def GetTriggerVersion(self,triggerName):
        for key in self.HLTSeed.iterkeys():
            if StripVersion(key)==triggerName:
                return key
        return ""

    def Save(self, fileName):
        dir = os.path.dirname(fileName)    
        if not os.path.exists(dir):
            os.makedirs(dir)
        pickle.dump( self, open( fileName, 'w' ) )

    def Load(self, fileName):
        self = pickle.load( open( fileName ) )

def ConnectDB(user='trg'):
    try:
        host = os.uname()[1]
        #offline = 1 if host.startswith('lxplus') else 0
        if host.startswith('lxplus'):
            offline=1
        else:
            offline=0
    except:
        print "Please setup database parsing:\nsource set.sh"
    ##print offline
    trg = ['~centraltspro/secure/cms_trg_r.txt','~/secure/cms_trg_r.txt']
    hlt = ['~hltpro/secure/cms_hlt_r.txt','~/secure/cms_hlt_r.txt']

    if user == 'trg':
        cmd = 'cat %s' % (trg[offline],)
    elif user == 'hlt':
        cmd='cat %s' % (hlt[offline],)

    try:
        line=os.popen(cmd).readlines()
    except:
        print "ERROR Getting the database password!"
        print "They should be in %s and %s" % (trg[offline],hlt[offline],)
        print "You may need to copy them from the online machines"
        sys.exit(0)
    magic = line[0].rstrip("\n\r")
    connect = 'cms_%s_r/%s@cms_omds_lb' % (user,magic,)
    orcl = cx_Oracle.connect(connect)
    return orcl.cursor()
    

def GetLatestRunNumber(runNo=9999999,newRun=False):
    
    curs = ConnectDB()
    
    if runNo==9999999:

        ##
        ##SELECT MAX(RUNNUMBER) FROM CMS_RUNINFO.RUNNUMBERTBL
        ##SELECT MAX(RUNNUMBER) CMS_WBM.RUNSUMMARY WHERE TRIGGERS>0
        ## RunNoQuery="""
##         SELECT MAX(A.RUNNUMBER) FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_WBM.RUNSUMMARY B WHERE A.RUNNUMBER=B.RUNNUMBER AND B.TRIGGERS>0
##         """

        RunNoQuery="""SELECT MAX(A.RUNNUMBER) 
        FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B WHERE B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0
        """
        try:
            curs.execute(RunNoQuery)
            r, = curs.fetchone()
            ##print "\nr=",r
        except:
            print "not able to get run"

        ## RunNoQuery="""SELECT MAX(RUNNUMBER) FROM CMS_RUNINFO.RUNNUMBERTBL"""
##         try:
##             curs.execute(RunNoQuery)
##             ra, = curs.fetchone()
##             print "ra=",ra
##         except:
##             print "not able to get ra"


##         RunNoQuery="""SELECT TIER0_TRANSFER FROM CMS_WBM.RUNSUMMARY WHERE TRIGGERS>0 AND RUNUMBER=MAX(RUNNUMBER)"""
##         try:
##             curs.execute(RunNoQuery)
##             rb, = curs.fetchone()
##             print "rb=",rb
##         except:
##             print "not able to get rb"

##         RunNoQuery="""SELECT MAX(RUNNUMBER) FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS WHERE LUMISECTION > 0 """
##         try:
##             curs.execute(RunNoQuery)
##             rc, = curs.fetchone()
##             print "rc=",rc
##         except:
##             print "not able to get rc"
        
    else:
        r = runNo
    isCol=0

    TrigModeQuery = """
    SELECT TRIGGERMODE FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER = %d
    """ % r
    curs.execute(TrigModeQuery)
    try:
        trigm, = curs.fetchone()
    except:
        print "unable to get trigm from query for run ",r
    isCol=0
    isGood=1

       
    try:
        if trigm is None:
            isGood=0
        elif trigm.find('l1_hlt_collisions')!=-1:
            isCol=1
    except:
        isGood=0

    Tier0xferQuery = """
    SELECT TIER0_TRANSFER TIER0 FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER = %d
    """ % r
    curs.execute(Tier0xferQuery)
    tier0=1
    try:
        tier0, = curs.fetchone()
                    
    except:
        print "unable to get tier0 from query for run ",r

    if isCol and not tier0:
        #write(bcolors.FAIL)
        print "WARNING tier0 transfer is off"
        #write(bcolors.ENDC+"\n")
    elif not tier0:
        #write(bcolors.WARINING)
        print "Please check if tier0 transfer is supposed to be off"
        #write(bcolors.ENDC+"\n")


        
    return (r,isCol,isGood,)

def ClosestIndex(value,table):
    diff = 999999999;
    index = 0
    for i,thisVal in table.iteritems():
        if abs(thisVal-value)<diff:
            diff = abs(thisVal-value)
            index =i
    return index


def StripVersion(name):
    if re.match('.*_v[0-9]+',name):
        name = name[:name.rfind('_')]
    return name

def GetLastKnownPSIndex(psindex_dict):
    psi = 3
    for ls in reversed(psindex_dict.keys()):
        if psindex_dict[ls] is not None:
            psi = psindex_dict[ls]
            break
    return psi
