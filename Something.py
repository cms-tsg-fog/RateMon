##################################
# DB.py
# Author: Charlie Mueller, Nathaniel Rupprecht, Alberto Zucchetta, Andrew Wightman
# Date: June 11, 2015
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>    -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects 
##################################

# Imports
import cx_Oracle
import socket
# For the parsing
import re

import DBConfigFile as cfg

from omsapi import OMSAPI

omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1")
omsapi.auth_krb()

# Key version stripper
def stripVersion(name):
    if re.match('.*_v[0-9]+',name): name = name[:name.rfind('_')]
    #name = str(name.split('_v[0-9]')[0])
    #p = re.compile(r"_v[0-9]\b")
    #name = p.sub('',name,)
    return name

# A class that interacts with the HLT's oracle database and fetches information that we need
class DBParser2:
    def __init__(self) :
        # Connect to the Database
        hostname = socket.gethostname()
        if hostname.find('lxplus') > -1: self.dsn_ = cfg.dsn_info['offline']
        else: self.dsn_ = cfg.dsn_info['online']

        orcl = cx_Oracle.connect(user=cfg.trg_connect['user'],password=cfg.trg_connect['passwd'],dsn=self.dsn_)
        # Create a DB cursor
        self.curs = orcl.cursor()

        self.L1Prescales = {}       # {algo_index: {psi: prescale}}
        self.HLTPrescales = {}      # {'trigger': [prescales]}
        self.HLTSequenceMap = {}
        self.GTRS_Key = ""
        self.HLT_Key  = ""
        self.TSC_Key  = ""
        self.ConfigId = ""
        self.GT_Key   = ""
        self.nAlgoBits = 128

        self.HLTSeed = {}
        self.L1Mask = {}
        self.L1IndexNameMap = {}
        self.L1NameIndexMap = {}
        self.PSColumnByLS = {}
        
    # Returns: a cursor to the HLT database
    def getHLTCursor(self):
        orcl = cx_Oracle.connect(user=cfg.hlt_connect['user'],password=cfg.hlt_connect['passwd'],dsn=self.dsn_)
        return orcl.cursor()

    # Returns: a cursor to the trigger database
    def getTrgCursor(self):
        orcl = cx_Oracle.connect(user=cfg.trg_connect['user'],password=cfg.trg_connect['passwd'],dsn=self.dsn_)
        return orcl.cursor()

    def getLSInfo(self, runNumber):
        sqlquery =  """
            SELECT
                LUMI_SECTION,
                PRESCALE_INDEX
            FROM
                CMS_UGT_MON.VIEW_LUMI_SECTIONS
            WHERE
                RUN_NUMBER = %s
            """ % (runNumber)
        ls_info = []
        try:
            self.curs.execute(sqlquery)
            ls_info = self.curs.fetchall()
        except:
            print("Unable to get LS list for run %s" % runNumber)

        print(ls_info)
        
        return ls_info

    # Returns the various keys used for the specified run as a 5-tuple
    def getRunKeys(self,runNumber):
        sqlquery =  """
                    SELECT
                        B.ID,
                        B.HLT_KEY,
                        B.L1_TRG_RS_KEY,
                        B.L1_TRG_CONF_KEY,
                        C.UGT_KEY
                    FROM
                        CMS_WBM.RUNSUMMARY A,
                        CMS_L1_HLT.L1_HLT_CONF B,
                        CMS_TRG_L1_CONF.L1_TRG_CONF_KEYS C
                    WHERE
                        B.ID = A.TRIGGERMODE AND
                        A.RUNNUMBER = %d AND
                        C.ID = B.L1_TRG_CONF_KEY
                    """ % (runNumber)
        L1_HLT,HLT,GTRS,TSC,GT = "","","","",""
        try: 
            self.curs.execute(sqlquery)
            L1_HLT,HLT,GTRS,TSC,GT = self.curs.fetchone()
        except:
            print("[ERROR] Unable to get keys for this run, %d" % (runNumber))

        q = omsapi.query("l1configurationkeys")
        q.filter("run_number", runNumber)
        response = q.data()
        data = response.json()
        item = data['data'][0]['attributes']
        test = True
        if L1_HLT != item['l1_hlt_mode_stripped']:
            test = False
            print(L1_HLT)
            print(item['l1_hlt_mode_stripped'])
        if GTRS != item['run_settings_key']:
            test = Flase
            print(GTRS)
            print(item['run_settings_key'])
        if TSC != item['l1_key']:
            test = False
            print(TSC)
            print(item['l1_key'])
        if GT != item['gt_key']:
            test = False
            print(GT)
            print(item['gt_key'])

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        response = q.data()
        data = response.json()
        item = data['data'][0]['attributes']
        if HLT != item['config_name']:
            test = False
            print(HLT)
            print(item['config_name'])

        if test:
            print("YES!!!")
        
        
        #print(L1_HLT,HLT,GTRS,TSC,GT)
        return L1_HLT,HLT,GTRS,TSC,GT

    # Returns: True if we succeded, false if the run doesn't exist (probably)
    def getRunInfo(self, runNumber):
        ## This query gets the L1_HLT Key (A), the associated HLT Key (B) and the Config number for that key (C)
        #KeyQuery = """
        #SELECT A.TRIGGERMODE, B.HLT_KEY, B.GT_RS_KEY, B.TSC_KEY, D.GT_KEY FROM
        #CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF B, CMS_HLT_GDR.U_CONFVERSIONS C, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
        #B.ID = A.TRIGGERMODE AND C.NAME = B.HLT_KEY AND D.TS_Key = B.TSC_Key AND A.RUNNUMBER=%d
        #""" % (runNumber)

        #KeyQuery = """
        #SELECT A.TRIGGERMODE, B.HLT_KEY, B.L1_TRG_RS_KEY, B.L1_TRG_CONF_KEY, B.UGT_KEY FROM
        #CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.V_L1_HLT_CONF_EXTENDED B, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
        #B.ID = A.TRIGGERMODE AND A.RUNNUMBER=%d
        #""" % (runNumber)

        sqlquery =  """
                    SELECT
                        LUMI_SECTION,
                        PRESCALE_INDEX
                    FROM
                        CMS_UGT_MON.VIEW_LUMI_SECTIONS
                    WHERE
                        RUN_NUMBER = %s
                    """ % (runNumber)

        q = omsapi.query("lumisection")
        q.filter("run_number", runNumber)
        something = q.data()
        response = something.json()
        print(response)

        my_lst = {}
        try:
            self.curs.execute(sqlquery)
            self.PSColumnByLS = {} 
            for lumi_section, prescale_column in self.curs.fetchall():
                self.PSColumnByLS[lumi_section] = prescale_column
                q = omsapi.query("l1algorithmtriggersperlumisection")
                q.filter("run_number", runNumber)
                q.filter("lumisection_number", lumi_section)
                something = q.data()
                response = something.json()
                for item in response['data']:
                    my_lst[lumi_section] = item['attributes']['prescale_index']
                #print prescale_column
        except:
            print("Trouble getting PS column by LS")
        

        print(self.PSColumnByLS)
        print(my_lst)
        if my_lst == self.PSColumnByLS:
            print("YES!!!")
        
        self.L1_HLT_Key, self.HLT_Key, self.GTRS_Key, self.TSC_Key, self.GT_Key = self.getRunKeys(runNumber)
        if self.HLT_Key == "":
            # The key query failed
            return False
        else:
            return True

    # Use: Get the instant luminosity for each lumisection from the database
    # Parameters:
    # -- runNumber: the number of the run that we want data for
    # Returns: A list of of information for each LS: ( { LS, instLumi, physics } )
    def getLumiInfo(self, runNumber, minLS=-1, maxLS=9999999, lumi_source=0):
        # NOTE: Currently making queries to CMS_BEAM_COND.CMS_BRIL_LUMINOSITY is taking excessively long times offline
        lumi_nibble = 16        # This is the value that WBM uses for lumi sections
        query = """
                SELECT
                    B.INSTLUMI,
                    A.PLTZERO_INSTLUMI,
                    A.HF_INSTLUMI,
                    B.LUMISECTION,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT*B.EBP_READY*
                        B.EBM_READY*B.EEP_READY*B.EEM_READY*
                        B.HBHEA_READY*B.HBHEB_READY*B.HBHEC_READY*
                        B.HF_READY*B.HO_READY*B.RPC_READY*
                        B.DT0_READY*B.DTP_READY*B.DTM_READY*
                        B.CSCP_READY*B.CSCM_READY*B.TOB_READY*
                        B.TIBTID_READY*B.TECP_READY*B.TECM_READY*
                        B.BPIX_READY*B.FPIX_READY*B.ESP_READY*B.ESM_READY,
                    C.PRESCALE_INDEX
                FROM
                    CMS_BEAM_COND.CMS_BRIL_LUMINOSITY A,
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B,
                    CMS_UGT_MON.VIEW_LUMI_SECTIONS C
                WHERE
                    A.RUN = %s AND
                    A.LUMINIBBLE = %s AND
                    A.RUN = B.RUNNUMBER AND
                    A.LUMISECTION = B.LUMISECTION AND
                    C.RUN_NUMBER(+) = B.RUNNUMBER AND
                    C.LUMI_SECTION(+) = B.LUMISECTION AND
                    B.LUMISECTION >= %s AND C.LUMI_SECTION >= %s AND
                    B.LUMISECTION <= %s AND C.LUMI_SECTION <= %s
                ORDER BY
                    LUMISECTION
                """ % (runNumber,lumi_nibble,minLS,minLS,maxLS,maxLS)
        self.curs.execute(query) # Execute the query
        _list = []
        for item in self.curs.fetchall():
            ilum = item[lumi_source]
            if ilum is None:
                if item[1]:
                    ilum = item[1]
                elif item[2]:
                    ilum = item[2]
                else:
                    ilum = None
            LS = item[3]
            phys = item[4]
            cms_ready = item[5]
            psi = item[6]
            _list.append([int(LS),float(ilum),int(psi),bool(phys),bool(cms_ready)])
        
        q = omsapi.query("lumisections")
        q.filter("run_number", runNumber)
        response = q.data().json()
        print(response)

        return _list

    # Use: Get the instant luminosity for each lumisection (only from CMS_RUNTIME_LOGGER.LUMI_SECTIONS)
    # Parameters:
    # -- runNumber: the number of the run that we want data for
    # Returns: A list of of information for each LS: ( { LS, instLumi, physics } )
    def getQuickLumiInfo(self,runNumber,minLS=-1,maxLS=9999999):
        query = """
                SELECT
                    B.INSTLUMI,
                    B.LUMISECTION,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT*B.EBP_READY*
                        B.EBM_READY*B.EEP_READY*B.EEM_READY*
                        B.HBHEA_READY*B.HBHEB_READY*B.HBHEC_READY*
                        B.HF_READY*B.HO_READY*B.RPC_READY*
                        B.DT0_READY*B.DTP_READY*B.DTM_READY*
                        B.CSCP_READY*B.CSCM_READY*B.TOB_READY*
                        B.TIBTID_READY*B.TECP_READY*B.TECM_READY*
                        B.BPIX_READY*B.FPIX_READY*B.ESP_READY*B.ESM_READY,
                    C.PRESCALE_INDEX
                FROM
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B,
                    CMS_UGT_MON.VIEW_LUMI_SECTIONS C
                WHERE
                    B.RUNNUMBER = %s AND
                    C.RUN_NUMBER(+) = B.RUNNUMBER AND
                    C.LUMI_SECTION(+) = B.LUMISECTION AND
                    B.LUMISECTION >= %s AND C.LUMI_SECTION >= %s AND
                    B.LUMISECTION <= %s AND C.LUMI_SECTION <= %s
                ORDER BY
                    LUMISECTION
                """ % (runNumber,minLS,minLS,maxLS,maxLS)

        self.curs.execute(query) # Execute the query
        _list = []
        for item in self.curs.fetchall():
            ilum = item[0]
            #print ilum
            LS = item[1]
            phys = item[2]
            cms_ready = item[3]
            psi = item[4]
            _list.append([int(LS),float(ilum),int(psi),bool(phys),bool(cms_ready)])

        print("LOOK HERE!!!")
        q = omsapi.query("lumisections")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        something = q.data()
        response = something.json()
        _list2 = []
        
        for item in response['data']:
            thing = item['attributes']
            q2 = omsapi.query("l1algorithmtriggersperlumisection")
            q2.filter("run_number", runNumber)
            q2.filter("lumisection_number", thing['lumisection_number'])
            something2 = q2.data()
            response2 = something2.json()
            something3 = 10000*thing['init_lumi']
            #print thing['init_lumi'], thing['end_lumi']
            for item2 in response2['data']:
                filler = item2['attributes']['prescale_index']
            _list2.append([thing['lumisection_number'], something3, filler, thing['physics_flag']*thing['beam1_present'], 
                           thing['physics_flag']*thing['beam1_present']*thing['ebp_ready']*thing['ebm_ready']*
                           thing['eep_ready']*thing['eem_ready']*thing['hbhea_ready']*thing['hbheb_ready']*
                           thing['hbhec_ready']*thing['hf_ready']*thing['ho_ready']*thing['rpc_ready']*thing['dt0_ready']*
                           thing['dtp_ready']*thing['dtm_ready']*thing['cscp_ready']*thing['cscm_ready']*thing['tob_ready']*
                           thing['tibtid_ready']*thing['tecp_ready']*thing['tecm_ready']*thing['bpix_ready']*
                           thing['fpix_ready']*thing['esp_ready']*thing['esm_ready']])

        print(_list)
        print(_list2)
        if _list == _list2:
            print("YESS!!!")


        return _list

    # Use: Get the prescaled rate as a function 
    # Parameters: runNumber: the number of the run that we want data for
    # Returns: A dictionary [ triggerName ] [ LS ] <prescaled rate> 
    def getPSRates(self, runNumber, minLS=-1, maxLS=9999999):
        # Note: we find the raw rate by dividing CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS.Accept by 23.31041

        sqlquery =  """
                    SELECT
                        A.LSNUMBER,
                        SUM(A.PACCEPT),
                        (
                            SELECT
                                M.NAME
                            FROM
                                CMS_HLT_GDR.U_PATHS M,
                                CMS_HLT_GDR.U_PATHIDS L
                            WHERE
                                L.PATHID=A.PATHID AND
                                M.ID=L.ID_PATH
                        ) PATHNAME
                    FROM
                        CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A
                    WHERE
                        RUNNUMBER = %s AND
                        A.LSNUMBER >= %s AND
                        A.LSNUMBER <= %s
                    GROUP BY
                        A.LSNUMBER,A.PATHID
                    """ % (runNumber, minLS, maxLS)

        try:
            self.curs.execute(sqlquery)
        except:
            print("Getting rates failed. Exiting.")
            exit(2) # Exit with error
        TriggerRates = {}

        for LS, HLTPass, triggerName in self.curs.fetchall():
            
            rate = HLTPass/23.31041 # A lumisection is 23.31041 seconds
            name = stripVersion(triggerName)

            if name not in TriggerRates:
                # Initialize the value of TriggerRates[name] to be a dictionary, which we will fill with [ LS, rate ] data
                TriggerRates[name] = {}
                TriggerRates[name][LS] = rate
            else:
                TriggerRates[name][LS] = rate
        #print(TriggerRates)
        #q = omsapi.query("hltpathinfo")
        #q.filter("run_number", runNumber)
        #q.per_page = 4000
        #response = q.data()
        #item = response.json()
        #data = item['data']
        #TriggerRates2 = {}
        #for thing in data:
        #    something = thing['attributes']
        #    q2 = omsapi.query("hltpathrates")
        #    q2.filter("run_number", runNumber)
        #    q2.filter("path_name", something["path_name"])
        #    q2.per_page = 4000
        #    response2 = q2.data()
        #    item2 = response2.json()
        #    #print(item2)
        #    data2 = item2['data']
        #    for thing2 in data2:
        #        something2 = thing2['attributes']
        #        if something2['path_name'] not in TriggerRates2:
        #            TriggerRates2[something2['path_name']] = {}
        #            TriggerRates2[something2['path_name']][something2['first_lumisection_number']] = something2['rate']
        #        else:
        #            TriggerRates2[something2['path_name']][something2['first_lumisection_number']] = something2['rate']
        
        #if TriggerRates == TriggerRates2:
        #    print("YES!!!")
        #else:
            #print(TriggerRates)
            #print(TriggerRates2)
            

        return TriggerRates

    # Similar to the 'getRawRates' query, but is restricted to triggers that appear in trigger_list
    def getHLTRates(self, runNumber, trigger_list=[],minLS=-1, maxLS=9999999):
        # First we need the HLT and L1 prescale rates and the HLT seed info
        if not self.getRunInfo(runNumber):
            print("Failed to get run info ")
            return {} # The run probably doesn't exist

        # Get L1 info
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)
        # Get HLT info
        self.getHLTSeeds(runNumber)
        #self.getHLTPrescales(runNumber)

        # Get the prescale index as a function of LS
        for LS, psi in self.curs.fetchall():
            self.PSColumnByLS[LS] = psi

        self.HLT_name_map = self.getHLTNameMap(runNumber)

        if len(trigger_list) == 0:
            # If no list is given --> get rates for all HLT triggers
            trigger_list = list(self.HLT_name_map.keys())

        trigger_rates = {}
        for name in trigger_list:
            if name not in self.HLT_name_map:
                # Ignore triggers which don't appear in this run
                continue
            trigger_rates[name] = self.getSingleHLTRate(runNumber,name,minLS,maxLS)

        q = omsapi.query('hltpathinfo')
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        print(item)
        data = item['data']
        trigger_rates2 = {}
        for thing in data:
            something = thing['attributes']
            q2 = omsapi.query("hltpathrates")
            q2.filter("run_number", runNumber)
            q2.filter("path_name", something['path_name'])
            q2.per_page = 4000
            item2 = q2.data()
            #print(item2)
            if not trigger_rates2.has_key(something['path_name']):
                trigger_rates2[something['path_name']] = {}
            data2 = item2['data']
            for thing2 in data2:
                something2 = thing2['attributes']
                trigger_rates2[something['path_name']][something2['first_lumisection_number']] = [something['prescales'][1]['prescale']*something2['rate'], something2['rate']]

        if trigger_rates == trigger_rates2:
            print("YES!!!")
        else:
            print(trigger_rates)
            print(trigger_rates2)

        return trigger_rates

    # Gets the HLT rate for a single trigger
    # WARNING: This function is meant to be called by the wrapper funciton 'getHLTRates', since many of the 'self.' dictionaries change between runs
    def getSingleHLTRate(self, runNumber, name, minLS=-1, maxLS=9999999):
        # Cache the various dictionaries, so we don't have to repeat the queries
        path_id = self.HLT_name_map[name]
        sqlquery =  """
                    SELECT
                        A.LSNUMBER,
                        SUM(A.L1PASS),
                        SUM(A.PSPASS),
                        SUM(A.PACCEPT),
                        SUM(A.PEXCEPT)
                    FROM
                        CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A
                    WHERE
                        A.RUNNUMBER = %s AND
                        A.PATHID = %s AND
                        A.LSNUMBER >= %s AND
                        A.LSNUMBER <= %s
                    GROUP BY
                        A.LSNUMBER, A.PATHID
                    """ % (runNumber,path_id,minLS,maxLS)
        try: 
            self.curs.execute(sqlquery)
        except:
            print("Getting rates for %s failed. Exiting." % name)
            exit(2) # Exit with error

        trigger_rates = {}
        for LS, L1Pass, PSPass, HLTPass, HLTExcept in self.curs.fetchall():
            rate = HLTPass/23.31041 # HLTPass is events in this LS, so divide by 23.31041 s to get rate
            hltps = 0 # HLT Prescale

            # TODO: We can probably come up with a better solution then a try, except here
            try: 
                psi = self.PSColumnByLS[LS] # Get the prescale index
            except:
                psi = 0

            if psi is None:
                psi = 0
            
            try:
                hltps = self.HLTPrescales[name][psi]
            except:
                hltps = 1.

            hltps = float(hltps)
                    
            try:
                if self.HLTSeed[name] in self.L1IndexNameMap:
                    l1ps = self.L1Prescales[self.L1IndexNameMap[self.HLTSeed[name]]][psi]
                else:
                    l1ps = self.UnwindORSeed(self.HLTSeed[name],self.L1Prescales,psi)
            except:
                l1ps = 1

            ps = l1ps*hltps
            trigger_rates[LS] = [ps*rate, ps]
        return trigger_rates

    # Generates a dictionary that maps HLT path names to the corresponding path_id
    def getHLTNameMap(self,runNumber):
        sqlquery =  """
                    SELECT DISTINCT
                        C.PATHID,
                        B.NAME
                    FROM
                        CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A,
                        CMS_HLT_GDR.U_PATHS B,
                        CMS_HLT_GDR.U_PATHIDS C
                    WHERE
                        A.RUNNUMBER = %s AND
                        A.PATHID = C.PATHID AND
                        B.ID = C.ID_PATH
                    """ % (runNumber)

        q = omsapi.query("hltpathinfo")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        name_map2 = {}
        #print(data)
        for thing in data:
            something = thing['attributes']
            name = stripVersion(something['path_name'])
            name_map2[name] = something['path_id']

        name_map = {}
        self.curs.execute(sqlquery)
        for path_id,path_name in self.curs.fetchall():
            name = stripVersion(path_name)
            name_map[name] = path_id

        Test = True
        for test in name_map2:
            if name_map[test] != name_map2[test]:
                Test = False
                print(test)
                print(name_map[test])
                print(name_map2[test])


        if Test:
            print("YESS!!!")
        
            #print(name_map)
            #print("inbetween")
            #print(name_map2)

        return name_map

    # Note: This function is from DatabaseParser.py (with moderate modification)
    # Use: Sets the L1 trigger prescales for this class
    # Returns: (void)
    def getL1Prescales(self, runNumber):
        sqlquery =  """
                    SELECT
                        A.ALGO_INDEX,
                        A.ALGO_NAME,
                        B.PRESCALE,
                        B.PRESCALE_INDEX
                    FROM
                        CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING A,
                        CMS_UGT_MON.VIEW_UGT_RUN_PRESCALE B
                    WHERE
                        A.ALGO_INDEX = B.ALGO_INDEX AND
                        A.RUN_NUMBER = B.RUN_NUMBER AND
                        A.RUN_NUMBER = %s
                    ORDER BY
                        A.ALGO_INDEX
                    """ % (runNumber)

        try:
            self.curs.execute(sqlquery)
        except:
            print("Get L1 Prescales query failed")
            return 

        ps_table = self.curs.fetchall()
        self.L1Prescales = {}

        if len(ps_table) < 1:
            print("Cannot get L1 Prescales")
            return

        #print "LOOK HERE!!!"
        q = omsapi.query("l1prescalesets")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        response = q.data()
        table = response.json()
        data = table['data']
        i = 0

        for object in ps_table:
            algo_index = object[0]
            algo_name = object[1]
            algo_ps = object[2]
            ps_index = object[3]
            if algo_index not in self.L1Prescales: self.L1Prescales[algo_index] = {}
            self.L1Prescales[algo_index][ps_index] = algo_ps
            
        print(self.L1Prescales)
        print("HERE!!!")
        print(data)
        for row in data:
            bunch = row['attributes']
            #print bunch
            for item in bunch['prescales']:
                if self.L1Prescales[bunch['algo_index']][item['prescale_index']] == item['prescale']:
                    print(bunch['algo_index'], item['prescale_index'], item['prescale'])
        
      
    # Note: This function is from DatabaseParser.py
    # Use: Frankly, I'm not sure. I don't think its ever been called. Read the (origional) info string
    # Returns: The minimum prescale value
    def UnwindORSeed(self,expression,L1Prescales,psi):
        """
        Figures out the effective prescale for the OR of several seeds
        we take this to be the *LOWEST* prescale of the included seeds
        """
        #if expression.find(" OR ") == -1:
        #    return -1  # Not an OR of seeds
        #seedList = expression.split(" OR ")
        #if len(seedList)==1:
        #    return -1 # Not an OR of seeds, really shouldn't get here...
        #minPS = 99999999999
        #for seed in seedList:
        #    if not self.L1IndexNameMap.has_key(seed): continue
        #    ps = L1Prescales[self.L1IndexNameMap[seed]]
        #    if ps: minPS = min(ps,minPS)
        #if minPS==99999999999: return 0
        #else: return minPS

        # Ignore 'AND' L1 seeds
        if expression.find(" AND ") != -1:
            return 1

        seedList = []
        # This 'if' might be redundent
        if expression.find(" OR ") != -1:
            for elem in expression.split(" OR "):
                # Strip all whitespace from the split strings
                seedList.append(elem.replace(" ",""))
        else:
            expression = expression.replace(" ","")
            seedList.append(expression)

        minPS = 99999999999
        for seed in seedList:
            if seed not in self.L1IndexNameMap: continue
            ps = L1Prescales[self.L1IndexNameMap[seed]][psi]
            if ps: minPS = min(ps,minPS)
        if minPS == 99999999999: return 0
        else: return minPS

    # Note: This function is from DatabaseParser.py (with slight modifications), double (##) comments are origionals
    # Use: Sets the L1 seed that each HLT trigger depends on
    # Returns: (void)
    def getHLTSeeds(self, runNumber):
        ### Check
        ## This is a rather delicate query, but it works!
        ## Essentially get a list of paths associated with the config, then find the module of type HLTLevel1GTSeed associated with the path
        ## Then find the parameter with field name L1SeedsLogicalExpression and look at the value
        ##
        ## NEED TO BE LOGGED IN AS CMS_HLT_R
        if self.HLT_Key == "": self.getRunInfo(runNumber)

        tmpcurs = self.getHLTCursor()
        sqlquery =  """
                    SELECT
                        s.name,
                        d.value
                    FROM
                        cms_hlt_gdr.u_confversions h,
                        cms_hlt_gdr.u_pathid2conf a,
                        cms_hlt_gdr.u_pathid2pae n,
                        cms_hlt_gdr.u_paelements b,
                        cms_hlt_gdr.u_pae2moe c,
                        cms_hlt_gdr.u_moelements d,
                        cms_hlt_gdr.u_mod2templ e,
                        cms_hlt_gdr.u_moduletemplates f,
                        cms_hlt_gdr.u_pathids p,
                        cms_hlt_gdr.u_paths s
                    WHERE 
                        h.name='%s' AND
                        a.id_confver=h.id AND
                        n.id_pathid=a.id_pathid AND
                        b.id=n.id_pae AND
                        c.id_pae=b.id AND
                        d.id=c.id_moe AND
                        d.name='L1SeedsLogicalExpression' AND
                        e.id_pae=b.id AND
                        f.id=e.id_templ AND
                        f.name='HLTL1TSeed' AND
                        p.id=n.id_pathid AND
                        s.id=p.id_path
                    ORDER BY
                        value
                    """ % (self.HLT_Key,)
        
        tmpcurs.execute(sqlquery)
        for HLTPath,L1Seed in tmpcurs.fetchall():
            name = stripVersion(HLTPath) # Strip the version from the trigger name
            if name not in self.HLTSeed: ## this should protect us from L1_SingleMuOpen
                #self.HLTSeed[HLTPath] = L1Seed.lstrip('"').rstrip('"')
                self.HLTSeed[name] = L1Seed.lstrip('"').rstrip('"') 

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        HLTSeed2 = {}
        for thing in data:
            something = thing['attributes']
            HLTSeed2[something['path_name']] = something['l1_prerequisite']

        if self.HLTSeed == HLTSeed2:
            print("YES!!!")
        else:
            print(self.HLTSeed)
            print(HLTSeed2)

    # Note: This function is from DatabaseParser.py (with slight modification)
    # Use: Seems to return the algo index that corresponds to each trigger name
    # Returns: (void)
    def getL1NameIndexAssoc(self, runNumber):
        ## get the L1 algo names associated with each algo bit
        ### Check
        #if self.GT_Key == "":
        #    self.getRunInfo(runNumber)
        #old GT query    
        #AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
        #WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
        #ORDER BY ALGO_INDEX""" % (self.GT_Key,)
        AlgoNameQuery = """
                        SELECT
                            ALGO_INDEX,
                            ALGO_NAME,
                            ALGO_MASK
                        FROM
                            CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING
                        WHERE
                            RUN_NUMBER=%s
                        """ % (runNumber)
        try:
            self.curs.execute(AlgoNameQuery)
        except:
            print("Get L1 Name Index failed")
            return

        q = omsapi.query("l1prescalesets")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        #print(item)
        data = item['data']
        index_name = {}
        name_index = {}
        index_mask = {}
        for thing in data:
            filler = thing['attributes']
            index_name[filler['algo_name']] = filler['algo_index']
            name_index[filler['algo_index']] = filler['algo_name']
            index_mask[filler['algo_index']] = filler['algo_mask']
            
        
        for bit,name,mask in self.curs.fetchall():
            name = stripVersion(name)
            name = name.replace("\"","")
            self.L1IndexNameMap[name] = bit
            self.L1NameIndexMap[bit]=name
            self.L1Mask[bit] = mask

        if index_name == self.L1IndexNameMap:
            print("YES!!!")
        else:
            print(index_name)
            print(self.L1IndexNameMap)
        if name_index == self.L1NameIndexMap:
            print("YES!!!")
        else:
            print(name_index)
            print(self.L1NameIndexMap)
        if index_mask == self.L1Mask:
            print("YES!!!")
        else:
            print(index_mask)
            print(self.L1Mask)

    # Note: This is a function from DatabaseParser.py (with slight modification)
    # Use: Gets the prescales for the various HLT triggers
    def getHLTPrescales(self, runNumber):
        ### Check
        if self.HLT_Key == "":
            self.getRunInfo(runNumber)
        tmp_curs = self.getHLTCursor()

        configIDQuery = """
                        SELECT
                            CONFIGID
                        FROM
                            CMS_HLT_GDR.U_CONFVERSIONS
                        WHERE
                            NAME='%s'
                        """ % (self.HLT_Key)

        tmp_curs.execute(configIDQuery)
        ConfigId, = tmp_curs.fetchone()

        SequencePathQuery ="""
            SELECT
                prescale_sequence,
                triggername
            FROM
                (
                    SELECT
                        J.ID,
                        J.NAME,
                        LAG(J.ORD,1,0) OVER (order by J.ID) PRESCALE_SEQUENCE,
                        J.VALUE TRIGGERNAME,
                        trim('{' from trim('}' from LEAD(J.VALUE,1,0) OVER (order by J.ID))) as PRESCALE_INDEX
                    FROM
                        CMS_HLT_GDR.U_CONFVERSIONS A,
                        CMS_HLT_GDR.U_CONF2SRV S,
                        CMS_HLT_GDR.U_SERVICES B,
                        CMS_HLT_GDR.U_SRVTEMPLATES C,
                        CMS_HLT_GDR.U_SRVELEMENTS J
                    WHERE
                        A.CONFIGID=%s AND
                        A.ID=S.ID_CONFVER AND
                        S.ID_SERVICE=B.ID AND
                        C.ID=B.ID_TEMPLATE AND
                        C.NAME='PrescaleService' AND
                        J.ID_SERVICE=B.ID
                ) Q
            WHERE
                NAME='pathName'
            """ % (ConfigId,)
        
        tmp_curs.execute(SequencePathQuery)
        HLTSequenceMap = {}
        for seq,name in tmp_curs.fetchall():
            name = name.lstrip('"').rstrip('"')
            name = stripVersion(name)
            HLTSequenceMap[seq]=name
            
        SequencePrescaleQuery = """
            WITH
                pq AS
                    (
                        SELECT 
                            Q.*
                        FROM
                            (
                                SELECT
                                    J.ID,
                                    J.NAME,
                                    LAG(J.ORD,1,0) OVER (order by J.ID) PRESCALE_SEQUENCE,
                                    J.VALUE TRIGGERNAME,
                                    trim('{' from trim('}' from LEAD(J.VALUE,1,0) OVER (order by J.ID))) AS PRESCALE_INDEX
                                FROM
                                    CMS_HLT_GDR.U_CONFVERSIONS A,
                                    CMS_HLT_GDR.U_CONF2SRV S,
                                    CMS_HLT_GDR.U_SERVICES B,
                                    CMS_HLT_GDR.U_SRVTEMPLATES C,
                                    CMS_HLT_GDR.U_SRVELEMENTS J
                                WHERE
                                    A.CONFIGID=%s AND
                                    A.ID=S.ID_CONFVER AND
                                    S.ID_SERVICE=B.ID AND
                                    C.ID=B.ID_TEMPLATE AND
                                    C.NAME='PrescaleService' AND
                                    J.ID_SERVICE=B.ID
                            ) Q
                        WHERE 
                            NAME='pathName'
                    )
            SELECT 
                prescale_sequence,
                MYINDEX,
                regexp_substr (prescale_index, '[^,]+', 1, rn) mypsnum
            FROM
                pq
            CROSS JOIN
                (
                    SELECT
                        rownum rn,
                        mod(rownum -1, level) MYINDEX
                    FROM 
                        (
                            SELECT
                                max (length (regexp_replace (prescale_index, '[^,]+'))) + 1 mx
                            FROM
                                pq
                        )
                    CONNECT BY
                        level <= mx
                )
            WHERE
                regexp_substr (prescale_index, '[^,]+', 1, rn) is not null
            ORDER BY
                prescale_sequence, myindex
            """ % (ConfigId,)
        
        tmp_curs.execute(SequencePrescaleQuery)
        lastIndex=-1
        lastSeq=-1
        row = []

        for seq,index,val in tmp_curs.fetchall():
            if lastIndex != index-1:
                self.HLTPrescales[HLTSequenceMap[seq-1]] = row
                row=[]
            lastSeq=seq
            lastIndex=index
            row.append(val)
        q = omsapi.query("hltprescalesets")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        #print(item)
        data = item['data']
        HLTPrescales2 = {}
        for thing in data:
            something = thing['attributes']
            row2 = []
            for a in something['prescales']:
                row2.append(a['prescale'])
            HLTPrescales2[something['path_name']] = row2
        
        if self.HLTPrescales == HLTPrescales2:
            print("YES!!!")
        else:
            print(self.HLTPrescales)
            print(HLTPrescales2)



    # Use: Returns the prescale column names of the HLT menu used for the specified run
    def getPrescaleNames(self,runNumber):
        ### Check
        if self.HLT_Key == "":
            self.getRunInfo(runNumber)
        tmp_curs = self.getHLTCursor()
        configIDQuery = """
                        SELECT
                            CONFIGID
                        FROM
                            CMS_HLT_GDR.U_CONFVERSIONS
                        WHERE
                            NAME='%s'
                        """ % (self.HLT_Key)

        tmp_curs.execute(configIDQuery)
        ConfigId, = tmp_curs.fetchone()

        sqlquery = """
            SELECT
                J.NAME,
                TRIM('{' FROM TRIM('}' FROM J.VALUE))
            FROM
                CMS_HLT_GDR.U_CONFVERSIONS A,
                CMS_HLT_GDR.U_CONF2SRV S,
                CMS_HLT_GDR.U_SERVICES B,
                CMS_HLT_GDR.U_SRVTEMPLATES C,
                CMS_HLT_GDR.U_SRVELEMENTS J
            WHERE
                A.CONFIGID=%s AND
                A.ID=S.ID_CONFVER AND
                S.ID_SERVICE=B.ID AND
                C.ID=B.ID_TEMPLATE AND
                C.NAME='PrescaleService' AND
                J.ID_SERVICE=B.ID AND
                J.NAME='lvl1Labels'
            """ % (ConfigId,)
        tmp_curs.execute(sqlquery)
        name,ps_str = tmp_curs.fetchone()
        ps_names = [x.strip().strip('"') for x in ps_str.strip().split(',')]

        q = omsapi.query("hltprescalesets")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data'][0]['attributes']['prescales']
        ps_names2 = []
        for something in data:
            ps_names2.append(something['prescale_name'])

        if ps_names == ps_names2:
            print("YES!!!")
        else:
            print(ps_names)
            print(ps_names2)


        return ps_names

    # Use: Returns the globaltag string for the HLT menu that was used in the specified run
    def getGlobalTag(self,runNumber):
        global_tag = ""
        HLT_Key = self.getRunKeys(runNumber)[1]

        if HLT_Key == "":
            # The key query failed
            return global_tag

        sqlquery = """
            SELECT
                D.VALUE
            FROM
                CMS_HLT_GDR.U_CONFVERSIONS A,
                CMS_HLT_GDR.U_CONF2ESS B,
                CMS_HLT_GDR.U_ESSOURCES C,
                CMS_HLT_GDR.U_ESSELEMENTS D
            WHERE
                A.NAME = '%s' AND
                A.ID = B.ID_CONFVER AND
                B.ID_ESSOURCE = C.ID AND
                B.ID_ESSOURCE = D.ID_ESSOURCE AND
                C.NAME = 'GlobalTag' AND
                D.NAME = 'globaltag'
        """ % (HLT_Key)

        try:
            self.curs.execute(sqlquery)
            global_tag, = self.curs.fetchone()
            global_tag = global_tag.strip('"')
        except:
            print("[ERROR] Failed to get globaltag for run, %d" % (runNumber))

        print(global_tag)
        return global_tag

    # Note: This is a function from DatabaseParser.py (with slight modification)
    # Use: Gets the number of colliding bunches during a run
    def getNumberCollidingBunches(self, runNumber):
        # Get Fill number first
        sqlquery =  """
                    SELECT
                        LHCFILL
                    FROM
                        CMS_WBM.RUNSUMMARY
                    WHERE
                        RUNNUMBER=%s
                    """ % (runNumber)
        self.curs.execute(sqlquery)
        
        try: fill = self.curs.fetchone()[0]
        except: return [0,0]
        
        # Get the number of colliding bunches
        sqlquery =  """
                    SELECT
                        NCOLLIDINGBUNCHES,
                        NTARGETBUNCHES
                    FROM
                        CMS_RUNTIME_LOGGER.RUNTIME_SUMMARY
                    WHERE
                        LHCFILL=%s
                    """ % (fill)
        try:
            self.curs.execute(sqlquery)
            bunches = self.curs.fetchall()[0]
            bunches = [ int(bunches[0]), int(bunches[1]) ]
            #return bunches
        except:
            #print "database error querying for num colliding bx" 
            return [0, 0]

        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        response = q.data()
        something = response.json()
        q2 = omsapi.query("fills")
        print(something['data'][0]['attributes']['fill_number'])
        q2.filter("fill_number", something['data'][0]['attributes']['fill_number'])
        response2 = q2.data()
        something2 = response2.json()
        bunches2 = [something2['data'][0]['attributes']['bunches_colliding'], something2['data'][0]['attributes']['bunches_target']]
        if bunches == bunches2:
            print("YES!!!")
        print(bunches)
        print(bunches2)
        
        return bunches

    # Use: Gets the last LHC status
    # Returns: A dictionary: [ status ] <text_value>
    def getLHCStatus(self):
        import time 
        utime = int(time.time())
        print(str(utime))
        print(str(utime-86400))
        print(utime)
        sqlquery =  """
                    SELECT
                        A.VALUE,
                        CMS_LHCGMT_COND.GMTDB.VALUE_TEXT(A.GROUPINDEX,A.VALUE) TEXT_VALUE
                    FROM
                        CMS_LHCGMT_COND.LHC_GMT_EVENTS A,
                        CMS_LHCGMT_COND.LHC_GMT_EVENT_DESCRIPTIONS B
                    WHERE
                        A.SOURCE=B.SOURCE(+) AND
                        A.SOURCE=5130 AND
                        A.SECONDS BETWEEN %s AND %s
                    ORDER BY
                        A.SECONDS DESC,A.NSECONDS DESC
                    """ % (str(1533000000-86400), str(1533000000))
        self.curs.execute(sqlquery)
        queryResult = self.curs.fetchall()
        print(queryResult)
        if len(queryResult) == 0: return ['----','Not available']
        elif len(queryResult[0]) >1: return queryResult[0]
        else: return ['---','Not available']
        
    # Use: Gets the dead time as a function of lumisection
    # Returns: A dictionary: [ LS ] <Deadtime>
    def getDeadTime(self,runNumber,minLS=-1,maxLS=9999999):
        sqlquery =  """
                    SELECT
                        SECTION_NUMBER,
                        DEADTIME_BEAMACTIVE_TOTAL
                    FROM
                        CMS_TCDS_MONITORING.tcds_cpm_deadtimes_v
                    WHERE
                        RUN_NUMBER=%s AND
                        SECTION_NUMBER >= %s AND
                        SECTION_NUMBER <= %s
                    """ % (runNumber,minLS,maxLS)
        
        self.curs.execute(sqlquery)

        q = omsapi.query("deadtimesperlumisection")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        response = q.data()
        data = response.json()
        #print data
        deadTime2 = {}
        for something in data['data']:
            thing = something['attributes']
            deadTime2[thing['lumisection_number']] = thing['deadtime_beamactive_total']
        
        deadTime = {}
        for ls, dt in self.curs.fetchall():
            deadTime[ls] = dt

        if deadTime == deadTime2:
            print("YES!!!")
        else:
            print(deadTime)
            print(deadTime2)
            
        return deadTime

    # Use: Gets the L1A physics lost rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysicsLost(self,runNumber,minLS=-1,maxLS=9999999):
        sqlquery =  """
                    SELECT
                        SECTION_NUMBER,
                        SUP_TRG_RATE_TT1
                    FROM
                        CMS_TCDS_MONITORING.tcds_cpm_rates_v
                    WHERE
                        RUN_NUMBER=%s AND
                        SECTION_NUMBER >= %s AND
                        SECTION_NUMBER <= %s
                    """ % (runNumber,minLS,maxLS)
        self.curs.execute(sqlquery)

        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        _list = {}
        for thing in data:
            something = thing['attributes']
            _list[something['lumisection_number']] = something['trigger_physics_lost']['rate']
        
        l1rate = {}
        for ls, rate in self.curs.fetchall():
            l1rate[ls] = rate

        if l1rate == _list:
            print("YES!!!")
        else:
            print(l1rate)
            print(_list)
            
        return l1rate

    # Use: Gets the total L1A physics rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysics(self, runNumber,minLS=-1,maxLS=9999999):
        sqlquery =  """
                    SELECT
                        SECTION_NUMBER,
                        TRG_RATE_TT1
                    FROM
                        CMS_TCDS_MONITORING.tcds_cpm_rates_v
                    WHERE
                        RUN_NUMBER=%s AND
                        SECTION_NUMBER >= %s AND
                        SECTION_NUMBER <= %s
                    """ % (runNumber,minLS,maxLS)

        self.curs.execute(sqlquery)

        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate2 = {}
        for thing in data:
            something = thing['attributes']
            l1rate2[something['lumisection_number']] = something['l1a_physics']['rate']

        
        l1rate = {}
        for ls, rate in self.curs.fetchall():
            l1rate[ls] = rate

        if l1rate == l1rate2:
            print("YES!!!")
        else:
            print(l1rate)
            print(l1rate2)
            
        return l1rate

    # Use: Gets the total L1A calibration rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ACalib(self, runNumber,minLS=-1,maxLS=9999999):
        sqlquery =  """
                    SELECT
                        SECTION_NUMBER,
                        TRG_RATE_TT2
                    FROM
                        CMS_TCDS_MONITORING.tcds_cpm_rates_v
                    WHERE
                        RUN_NUMBER=%s AND
                        SECTION_NUMBER >= %s AND
                        SECTION_NUMBER <= %s
                    """ % (runNumber,minLS,maxLS)
        self.curs.execute(sqlquery)
        
        l1rate = {}
        for ls, rate in self.curs.fetchall():
            l1rate[ls] = rate

        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate2 = {}
        for thing in data:
            something = thing['attributes']
            l1rate2[something["lumisection_number"]] = something["l1a_calibration"]['rate']

        if l1rate == l1rate2:
            print("YES!!!")
        else:
            print(l1rate)
            print(l1rate2)
            
        return l1rate

    # Use: Gets the total L1ARand rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ARand(self, runNumber,minLS=-1,maxLS=9999999):
        sqlquery =  """
                    SELECT
                        SECTION_NUMBER,
                        TRG_RATE_TT3
                    FROM
                        CMS_TCDS_MONITORING.tcds_cpm_rates_v
                    WHERE
                        RUN_NUMBER=%s AND
                        SECTION_NUMBER >= %s AND
                        SECTION_NUMBER <= %s
                    """ % (runNumber,minLS,maxLS)
        self.curs.execute(sqlquery)
        
        l1rate = {}
        for ls, rate in self.curs.fetchall():
            l1rate[ls] = rate
            
        return l1rate

    # Use: Gets the TOTAL L1 rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1rate(self, runNumber,minLS=-1,maxLS=9999999):
        # TODO: This function's name is very similar to getL1Rates, consider renaming
        sqlquery =  """
                    SELECT
                        SECTION_NUMBER,
                        TRG_RATE_TOTAL
                    FROM
                        CMS_TCDS_MONITORING.tcds_cpm_rates_v
                    WHERE
                        RUN_NUMBER=%s AND
                        SECTION_NUMBER >= %s AND
                        SECTION_NUMBER <= %s
                    """ % (runNumber,minLS,maxLS)
        
        self.curs.execute(sqlquery)
        
        l1rate = {}
        for ls, rate in self.curs.fetchall():
            l1rate[ls] = rate
            
        return l1rate    

    # Use: Returns the number of the latest run to be stored in the DB
    def getLatestRunInfo(self):
        query = """
                SELECT
                    MAX(A.RUNNUMBER)
                FROM
                    CMS_RUNINFO.RUNNUMBERTBL A,
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B
                WHERE
                    B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0
                """
        try:
            self.curs.execute(query)
            runNumber = self.curs.fetchone()
        except:
            print("Error: Unable to retrieve latest run number.")
            return

        mode = self.getTriggerMode(runNumber)
        isCol = 0
        isGood = 1
        
        if mode is None:
            isGood = 0
        elif mode[0].find('l1_hlt_collisions') != -1:
            isCol = 1
                        
        Tier0xferQuery = """
            SELECT
                TIER0_TRANSFER TIER0
            FROM
                CMS_WBM.RUNSUMMARY
            WHERE
                RUNNUMBER = %d
            """ % (runNumber)
        self.curs.execute(Tier0xferQuery)
        tier0 = 1
        try:
            tier0 = self.curs.fetchone()
        except:
            print("Error: Unable to get tier0 status.")
            
        if isCol and not tier0:
            print("WARNING: tier0 transfer is off")
        elif not tier0:
            print("Please check if tier0 transfer is supposed to be off.")
            
        return [runNumber[0], isCol, isGood, mode]

    def getWbmUrl(self,runNumber,pathName,LS):
        if pathName[0:4] == "HLT_":
            sqlquery =  """
                        SELECT
                            A.PATHID,
                            (
                                SELECT
                                    M.NAME
                                FROM
                                    CMS_HLT_GDR.U_PATHS M,
                                    CMS_HLT_GDR.U_PATHIDS L
                                WHERE
                                    L.PATHID=A.PATHID AND M.ID=L.ID_PATH
                            ) PATHNAME
                        FROM
                            CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A
                        WHERE
                            RUNNUMBER=%s AND A.LSNUMBER=%s
                        """ % (runNumber, LS)

            try: self.curs.execute(sqlquery)
            except: return "-"

            for id,fullName in self.curs.fetchall():
                name = stripVersion(fullName)
                if name == pathName:
                    url = "https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/ChartHLTTriggerRates?fromLSNumber=&toLSNumber=&minRate=&maxRate=&drawCounts=0&drawLumisec=1&runID=%s&pathID=%s&TRIGGER_PATH=%s&LSLength=23.310409580838325" % (runNumber,id,fullName)
                    return url
                
        elif pathName[0:3]=="L1_":
            try:
                bitNum = self.L1IndexNameMap[pathName]
                url = "https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/ChartL1TriggerRates?fromTime=&toTime=&fromLSNumber=&toLSNumber=&minRate=&maxRate=&minCount=&maxCount=&preDeadRates=1&drawCounts=0&drawLumisec=1&runID=%s&bitID=%s&type=0&TRIGGER_NAME=%s&LSLength=23.310409580838325" % (runNumber,bitNum,pathName)
                return url
            except:
                return "-"
            
        return "-"
    
    # Use: Get the trigger mode for the specified run
    def getTriggerMode(self, runNumber):
        TrigModeQuery = """
                        SELECT
                            TRIGGERMODE
                        FROM
                            CMS_WBM.RUNSUMMARY
                        WHERE
                            RUNNUMBER = %d
                        """ % (runNumber)
        try:
            self.curs.execute(TrigModeQuery)
            mode = self.curs.fetchone()
        except:
            print("Error: Unable to retrieve trigger mode.")

        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        mode2 = item['data'][0]['attributes']['trigger_mode']
        if mode == mode2:
            print("YES!!!")
        else:
            print(mode)
            print(mode2)

        return mode

    # Use: Retrieves the data from all streams
    # Returns: A dictionary [ stream name ] { LS, rate, size, bandwidth }
    def getStreamData(self, runNumber, minLS=-1, maxLS=9999999):
        cursor = self.getTrgCursor()
        #StreamQuery =   """
        #                SELECT
        #                    A.lumisection,
        #                    A.stream,
        #                    B.nevents/23.31041,
        #                    B.filesize,
        #                    B.filesize/23.31041
        #                FROM
        #                    CMS_STOMGR.FILES_CREATED A,
        #                    CMS_STOMGR.FILES_INJECTED B
        #                WHERE
        #                    A.filename = B.filename AND
        #                    A.runnumber = %s AND
        #                    A.lumisection >= %s AND
        #                    A.lumisection <= %s
        #                """ % (runNumber, minLS, maxLS)

        StreamQuery =   """
                        SELECT
                            A.LUMISECTION,
                            A.STREAM,
                            A.NEVENTS/23.31041,
                            A.FILESIZE,
                            A.FILESIZE/23.31041
                        FROM
                            CMS_WBM.VIEW_SM_SUMMARY A
                        WHERE
                            A.RUNNUMBER = %s AND
                            A.LUMISECTION >= %s AND
                            A.LUMISECTION <= %s
                        """ % (runNumber,minLS,maxLS)

        try:
            cursor.execute(StreamQuery)
            #self.curs.execute(StreamQuery)
            streamData = cursor.fetchall()
        except:
            print("Error: Unable to retrieve stream data.")

        StreamData = {}
        for LS, stream, rate, size, bandwidth in streamData:
            if stream not in StreamData:
                StreamData[stream] = []
            StreamData[stream].append( [LS, rate, size, bandwidth] )

        for thing in StreamData:
            rate_filler = 0.0
            size_filler = 0.0
            band_filler = 0.0
            for something in StreamData[thing]:
                rate_filler = rate_filler + something[1]
                size_filler = size_filler + something[2]
                band_filler = band_filler + something[3]
            print(thing)
            print(rate_filler)
            print(size_filler)
            print(band_filler)

        return StreamData

    def getPrimaryDatasets(self, runNumber, minLS=-1, maxLS=9999999):
        cursor = self.getTrgCursor()
        PDQuery =   """
                    SELECT
                        DISTINCT E.NAME,
                        F.LSNUMBER,
                        F.ACCEPT/23.31041
                    FROM
                        CMS_HLT_GDR.U_CONFVERSIONS A,
                        CMS_HLT_GDR.U_CONF2STRDST B,
                        CMS_WBM.RUNSUMMARY C,
                        CMS_HLT_GDR.U_DATASETIDS D,
                        CMS_HLT_GDR.U_DATASETS E,
                        CMS_RUNINFO.HLT_SUPERVISOR_DATASETS F
                    WHERE
                        D.ID = B.ID_DATASETID AND
                        E.ID = D.ID_DATASET AND
                        B.ID_CONFVER = A.ID AND
                        D.ID = F.DATASETID AND
                        A.CONFIGID = C.HLTKEY AND
                        F.RUNNUMBER = C.RUNNUMBER AND
                        C.RUNNUMBER = %s AND
                        F.LSNUMBER >=%s AND
                        F.LSNUMBER <=%s
                    ORDER BY
                        E.NAME
                    """ % (runNumber,minLS,maxLS)

        try:
            cursor.execute(PDQuery)
            #self.curs.execute(PDQuery)
            pdData = cursor.fetchall()
        except:
            print("Error: Unable to retrieve PD data.")

        PrimaryDatasets = {}
        for pd, LS, rate, in pdData:
            if pd not in PrimaryDatasets:
                PrimaryDatasets[pd] = []
            PrimaryDatasets[pd].append( [LS, rate] )
        
        print(PrimaryDatasets)
        
        return PrimaryDatasets

    def getFillRuns(self, fillNumber):
        #query = """SELECT A.FILL_NUMBER, A.RUN_NUMBER, B.PHYSICS_FLAG*B.BEAM1_STABLE*B.BEAM2_STABLE, A.SECTION_NUMBER 
        #            FROM CMS_TCDS_MONITORING.tcds_cpm_counts_v A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B
        #            WHERE A.FILL_NUMBER=%s AND A.RUN_NUMBER=B.RUNNUMBER""" % (fillNumber)
        #self.curs.execute(query)
        #output = self.curs.fetchone()
        #run_list = []
        #while (not output is None):
        #    if output is None:
        #        break
        #    run_number = output[1]
        #    flag = output[2]
        #    if not run_number in run_list and flag == 1:
        #        run_list.append(run_number)
        #    output = self.curs.fetchone()

        tmp_list = []
        run_list = []
        query = """
                SELECT 
                    DISTINCT A.RUN_NUMBER,
                    B.RUNNUMBER
                FROM 
                    CMS_TCDS_MONITORING.tcds_cpm_counts_v A,
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B
                WHERE 
                    A.FILL_NUMBER=%s AND
                    A.RUN_NUMBER=B.RUNNUMBER
                ORDER BY 
                    A.RUN_NUMBER
                """ % (fillNumber)
        self.curs.execute(query)
        self.curs.fetchone()    # Discard the first run as it is actually from the previous fill
        for item in self.curs.fetchall():
            tmp_list.append(item[0])    # Add all runs from the fill to the list

        # We make the same query, but this time filter out runs w/o stable beam
        # NOTE: Might be able to bundle this into a single query, but for now this should work
        query = """
                SELECT 
                    DISTINCT A.RUN_NUMBER,
                    B.RUNNUMBER
                FROM 
                    CMS_TCDS_MONITORING.tcds_cpm_counts_v A,
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B
                WHERE 
                    A.FILL_NUMBER=%s AND
                    A.RUN_NUMBER=B.RUNNUMBER AND
                    B.PHYSICS_FLAG*B.BEAM1_STABLE*B.BEAM2_STABLE=1
                ORDER BY 
                    A.RUN_NUMBER
                """ % (fillNumber)
        self.curs.execute(query)
        for item in self.curs.fetchall():
            # We only include runs that are actually in this fill (i.e. runs with stable beams)!
            if item[0] in tmp_list:
                run_list.append(item[0])

        q = omsapi.query("lumisections")
        q.filter("fill_number", fillNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        run_list2 = []
        for thing in item['data']:
            something = thing['attributes']
            if something['physics_flag']*something['beam1_stable']*something['beam2_stable']:
                if something['run_number'] not in run_list2:
                    run_list2.append(something['run_number'])
        
        if run_list == run_list2:
            print("YES!!!")
            print(run_list)
            print(run_list2)
        else:
            print("NO!!!")
            print(run_list)
            print(run_list2)


        return run_list

    # Returns the runs from most recent fill with stable beams
    def getRecentRuns(self):
        query = """
                SELECT
                    DISTINCT A.RUN_NUMBER,
                    A.FILL_NUMBER
                FROM 
                    CMS_TCDS_MONITORING.tcds_cpm_counts_v A,
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B
                WHERE
                    A.RUN_NUMBER=B.RUNNUMBER AND
                    B.PHYSICS_FLAG*B.BEAM1_STABLE*B.BEAM2_STABLE=1
                ORDER BY 
                    A.RUN_NUMBER DESC
                """
        self.curs.execute(query)

        noCandidates = False
        last_fill = -1
        while True:
            row = self.curs.fetchone()
            if row is None:
                noCandidates = True
                break
            current_fill = row[1]
            if current_fill == last_fill:
                continue
            else:
                last_fill = current_fill
            # Check if the fill has valid runs
            run_list = []
            run_list += self.getFillRuns(current_fill)
            if len(run_list) > 0:
                # We have valid runs!
                break
        return run_list, last_fill

    # Returns a dictionary of streams that map to a list containing all the paths within that stream
    def getPathsInStreams(self,runNumber):
        # WARNING: NEED TO TEST THIS QUERY
        if not self.getRunInfo(runNumber):
            return None

        query = """
                SELECT
                    D.NAME,
                    G.NAME
                FROM
                    CMS_HLT_GDR.U_CONFVERSIONS A,
                    CMS_HLT_GDR.U_PATHID2CONF B,
                    CMS_HLT_GDR.U_PATHIDS C,
                    CMS_HLT_GDR.U_PATHS D,
                    CMS_HLT_GDR.U_PATHID2STRDST E,
                    CMS_HLT_GDR.U_STREAMIDS F,
                    CMS_HLT_GDR.U_STREAMS G
                WHERE
                    A.NAME = '%s' AND
                    B.ID_CONFVER = A.ID AND
                    C.ID = B.ID_PATHID AND
                    D.ID = C.ID_PATH AND
                    E.ID_PATHID = B.ID_PATHID AND
                    F.ID = E.ID_STREAMID AND
                    G.ID = F.ID_STREAM
                ORDER BY
                    G.NAME
                """ % (self.HLT_Key)

        self.curs.execute(query)

        stream_paths = {}       # {'stream_name': [trg_paths] }
        for trg,stream in self.curs.fetchall():
            trg = stripVersion(trg)
            if stream not in stream_paths:
                stream_paths[stream] = []

            if not trg in stream_paths[stream]:
                stream_paths[stream].append(trg)

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        stream_paths2 = {}
        for thing in data:
            something = thing['attributes']
            if something['stream_name'] not in stream_paths2:
                stream_paths2[something['stream_name']] = []
            if something['path_name'] not in stream_paths2[something['stream_name']]:
                stream_paths2[something['stream_name']].append(something['path_name'])


        if stream_paths == stream_paths2:
            print("YES!!!")
        else:
            print(stream_paths)
            print(stream_paths2)

        return stream_paths

    def getPathsInDatasets(self,runNumber):
        if not self.getRunInfo(runNumber):
            return None

        query = """
                SELECT
                    D.NAME,
                    G.NAME
                FROM
                    CMS_HLT_GDR.U_CONFVERSIONS A,
                    CMS_HLT_GDR.U_PATHID2CONF B,
                    CMS_HLT_GDR.U_PATHIDS C,
                    CMS_HLT_GDR.U_PATHS D,
                    CMS_HLT_GDR.U_PATHID2STRDST E,
                    CMS_HLT_GDR.U_DATASETIDS F,
                    CMS_HLT_GDR.U_DATASETS G
                WHERE
                    A.NAME = '%s' AND
                    B.ID_CONFVER = A.ID AND
                    C.ID = B.ID_PATHID AND
                    D.ID = C.ID_PATH AND 
                    E.ID_PATHID = B.ID_PATHID AND
                    F.ID = E.ID_DATASETID AND
                    G.ID = F.ID_DATASET
                """ % (self.HLT_Key)

        self.curs.execute(query)

        dataset_paths = {}      # {'dataset_name': [trg_paths] }
        for trg,dataset in self.curs.fetchall():
            trg = stripVersion(trg)
            if dataset not in dataset_paths:
                dataset_paths[dataset] = []

            if not trg in dataset_paths[dataset]:
                dataset_paths[dataset].append(trg)

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        dataset_paths2 = {}
        for thing in data:
            something = thing['attributes']
            if something['stream_name'] not in dataset_paths2:
                dataset_paths2[something['stream_name']] = []
            if something['path_name'] not in dataset_paths2[something['stream_name']]:
                dataset_paths2[something['stream_name']].append(something['path_name'])

        if dataset_paths == dataset_paths2:
            print("YES!!!")
        else:
            print(dataset_paths)
            print("INBETWEEN!!!")
            print(dataset_paths2)


        return dataset_paths

    # Returns a list of all L1 triggers used in the run
    def getL1Triggers(self,runNumber):
        query = """
                SELECT
                    ALGO_NAME
                FROM
                    CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING
                WHERE
                    RUN_NUMBER = %s
                """ % (runNumber)

        self.curs.execute(query)

        q = omsapi.query("l1prescalesets")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        L1_list2 = []
        for thing in data:
            something = thing['attributes']
            L1_list2.append(something['algo_name'])

        L1_list = []
        for item in self.curs.fetchall():
            L1_list.append(item[0])

        if L1_list == L1_list2:
            print("YES!!!")
        else:
            print(L1_list)
            print(l1_list2)

        return L1_list

    # Functionally very similar to getL1RawRates, but allows for specifying which scalar type to query, also does no un-prescaling
    def getL1Rates(self,runNumber,minLS=-1,maxLS=9999999,scaler_type=0):
        self.getRunInfo(runNumber)
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)

        #pre-DT rates query (new uGT)
        #(0, 'ALGORITHM_RATE_AFTER_PRESCALE'),
        #(1, 'ALGORITHM_RATE_BEFORE_PRESCALE'),
        #(2, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE'),
        #(3, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_BY_HLT'),
        #(4, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_PHYSICS'),
        #(5, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_CALIBRATION'),
        #(6, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_RANDOM')

        run_str = "0%d" % runNumber
        query = """
                SELECT
                    LUMI_SECTIONS_ID,
                    ALGO_RATE,
                    ALGO_INDEX
                FROM
                    CMS_UGT_MON.VIEW_ALGO_SCALERS
                WHERE
                    SCALER_TYPE = %d AND
                    LUMI_SECTIONS_ID LIKE '%s%%'
                """ % (scaler_type,run_str)
        self.curs.execute(query)

        L1Triggers = {}
        for tup in self.curs.fetchall():
            ls = int(tup[0].split('_')[1].lstrip('0'))
            rate = tup[1]
            algo_bit = tup[2]

            if ls < minLS or ls > maxLS:
                #TODO: Move this check directly into the query
                continue

            algo_name = self.L1NameIndexMap[algo_bit]
            psi = self.PSColumnByLS[ls]
            algo_ps = self.L1Prescales[algo_bit][psi]

            if algo_name not in L1Triggers:
                L1Triggers[algo_name] = {}

            L1Triggers[algo_name][ls] = [rate, algo_ps]
        
        print(self.L1NameIndexMap)
        print(self.PSColumnByLS)
        print(self.L1Prescales)
        print(L1Triggers)
        return L1Triggers        # {'trigger': {LS: (rate,ps) } }

# -------------------- End of class DBParsing -------------------- #
