##################################
# DB.py
# Author: Charlie Mueller, Nathaniel Rupprecht, Alberto Zucchetta, Andrew Wightman, John Lawrence
# Date: June 11, 2015
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>    -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects 
##################################

# Imports
# For the parsing
import re

import DBConfigFile as cfg

from omsapi import OMSAPI

#initiate connection to endpoints and authenticate                                                                                                               
omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1")
omsapi.auth_krb()
#note this authentication only works on lxplus           

# Key version stripper
def stripVersion(name):
    if re.match('.*_v[0-9]+',name): name = name[:name.rfind('_')]
    return name

# A class that interacts with the HLT's oracle database and fetches information that we need
class DBParser:
    def __init__(self) :

        #initiate connection to endpoints and authenticate
        #omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1")
        #omsapi.auth_krb()
        #note this authentication only works on lxplus

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
        
    #returns the lumisection number with prescale index
    def getLSInfo(self, runNumber):
        ls_info = []
        q = omsapi.query("l1algorithmtriggersperlumisection")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        q.filter("bit", 1)
        data = q.data().json()['data']
        for thing in data:
            something = thing['attributes']
            ls_info.append([something["lumisection_number"], something['prescale_index']])
        return ls_info

    # Returns the various keys used for the specified run as a 5-tuple
    def getRunKeys(self,runNumber):
        q = omsapi.query("l1configurationkeys")
        q.filter("run_number", runNumber)
        item = q.data().json()['data'][0]['attributes']
        L1_HLT = item['l1_hlt_mode_stripped']
        GTRS = item['run_settings_key']
        TSC = item['l1_key']
        GT = item['gt_key']

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        item = q.data().json()['data'][0]['attributes']
        HLT = item['config_name']        
        
        return L1_HLT,HLT,GTRS,TSC,GT

    # Returns: True if we succeded, false if the run doesn't exist (probably)
    def getRunInfo(self, runNumber):

        q = omsapi.query("l1algorithmtriggersperlumisection")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        q.filter("bit",1)
        data = q.data().json()['data']
        for thing in data:
            something = thing['attributes']
            self.PSColumnByLS[something['lumisection_number']] = something['prescale_index']
        
        self.L1_HLT_Key, self.HLT_Key, self.GTRS_Key, self.TSC_Key, self.GT_Key = self.getRunKeys(runNumber)
        if self.HLT_Key == "":
            # The key query failed
            return False
        else:
            return True

    # Returns: A list of of information for each LS: ( { LS, instLumi, physics } )
    def getQuickLumiInfo(self,runNumber,minLS=-1,maxLS=9999999):
        _list = []
        
        q = omsapi.query("lumisections")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        something = q.data()
        response = something.json()
        
        for item in response['data']:
            thing = item['attributes']
            q2 = omsapi.query("l1algorithmtriggersperlumisection")
            q2.filter("run_number", runNumber)
            q2.filter("lumisection_number", thing['lumisection_number'])
            something2 = q2.data()
            response2 = something2.json()
            something3 = 10000*thing['init_lumi']
            
            for item2 in response2['data']:
                filler = item2['attributes']['prescale_index']
            _list.append([thing['lumisection_number'], something3, filler, thing['physics_flag']*thing['beam1_present'], 
                           thing['physics_flag']*thing['beam1_present']*thing['ebp_ready']*thing['ebm_ready']*
                           thing['eep_ready']*thing['eem_ready']*thing['hbhea_ready']*thing['hbheb_ready']*
                           thing['hbhec_ready']*thing['hf_ready']*thing['ho_ready']*thing['rpc_ready']*thing['dt0_ready']*
                           thing['dtp_ready']*thing['dtm_ready']*thing['cscp_ready']*thing['cscm_ready']*thing['tob_ready']*
                           thing['tibtid_ready']*thing['tecp_ready']*thing['tecm_ready']*thing['bpix_ready']*
                           thing['fpix_ready']*thing['esp_ready']*thing['esm_ready']])

        
        return _list

    # Use: Get the prescaled rate as a function 
    # Parameters: runNumber: the number of the run that we want data for
    # Returns: A dictionary [ triggerName ] [ LS ] <prescaled rate> 
    def getPSRates(self, runNumber, minLS=-1, maxLS=9999999):
        
        q = omsapi.query("hltpathrates")
        q.filter("run_number", runNumber)
        q.filter("last_lumisection_number", 400)
        q.per_page = 10000
        response = q.data()
        item = response.json()
        data = item['data']
        TriggerRates = {}
        for thing in data:
            something = thing['attributes']
            if something['path_name'] not in TriggerRates:
                TriggerRates[something['path_name']] = {}
                TriggerRates[something['path_name']][something['first_lumisection_number']] = something['rate']
            else:
                TriggerRates[something['path_name']][something['first_lumisection_number']] = something['rate']
        
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

        
        q = omsapi.query('hltpathinfo')
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        trigger_rates = {}
        for thing in data:
            something = thing['attributes']
            q2 = omsapi.query("hltpathrates")
            q2.filter("run_number", runNumber)
            q2.filter("path_name", something['path_name'])
            q2.per_page = 4000
            reponse2 = q2.data()
            item2 = response2.data()
            
            if not trigger_rates2.has_key(something['path_name']):
                trigger_rates2[something['path_name']] = {}
            data2 = item2['data']
            for thing2 in data2:
                something2 = thing2['attributes']
                trigger_rates[something['path_name']][something2['first_lumisection_number']] = [something['prescales'][1]['prescale']*something2['rate'], something2['rate']]

        return trigger_rates

    # Generates a dictionary that maps HLT path names to the corresponding path_id
    def getHLTNameMap(self,runNumber):
        
        q = omsapi.query("hltpathinfo")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        name_map = {}
        for thing in data:
            something = thing['attributes']
            name = stripVersion(something['path_name'])
            name_map[name] = something['path_id']

        
        return name_map

    # Note: This function is from DatabaseParser.py (with moderate modification)
    # Use: Sets the L1 trigger prescales for this class
    # Returns: (void)
    def getL1Prescales(self, runNumber):
        
        q = omsapi.query("l1prescalesets")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        response = q.data()
        table = response.json()
        data = table['data']

        for row in data:
            bunch = row['attributes']
            for item in bunch['prescales']:
                self.L1Prescales[bunch['algo_index']][item['prescale_index']] = item['prescale']
        
      
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
        
        if self.HLT_Key == "": self.getRunInfo(runNumber)

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        for thing in data:
            something = thing['attributes']
            self.HLTSeed[something['path_name']] = something['l1_prerequisite']


    # Note: This function is from DatabaseParser.py (with slight modification)
    # Use: Seems to return the algo index that corresponds to each trigger name
    # Returns: (void)
    def getL1NameIndexAssoc(self, runNumber):
        
        q = omsapi.query("l1prescalesets")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        for thing in data:
            filler = thing['attributes']
            self.L1IndexNameMap[filler['algo_name']] = filler['algo_index']
            self.L1NameIndexMap[filler['algo_index']] = filler['algo_name']
            self.L1Mask[filler['algo_index']] = filler['algo_mask']
            

    # Note: This is a function from DatabaseParser.py (with slight modification)
    # Use: Gets the prescales for the various HLT triggers
    def getHLTPrescales(self, runNumber):
        
        q = omsapi.query("hltprescalesets")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        for thing in data:
            something = thing['attributes']
            row2 = []
            for a in something['prescales']:
                row2.append(a['prescale'])
            self.HLTPrescales[something['path_name']] = row2


    # Use: Returns the prescale column names of the HLT menu used for the specified run
    def getPrescaleNames(self,runNumber):
        
        q = omsapi.query("hltprescalesets")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data'][0]['attributes']['prescales']
        ps_names = []
        for something in data:
            ps_names.append(something['prescale_name'])

        return ps_names

    # Note: This is a function from DatabaseParser.py (with slight modification)
    # Use: Gets the number of colliding bunches during a run
    def getNumberCollidingBunches(self, runNumber):
        
        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        response = q.data()
        something = response.json()
        q2 = omsapi.query("fills")
        print(something['data'][0]['attributes']['fill_number'])
        q2.filter("fill_number", something['data'][0]['attributes']['fill_number'])
        response2 = q2.data()
        something2 = response2.json()
        bunches = [something2['data'][0]['attributes']['bunches_colliding'], something2['data'][0]['attributes']['bunches_target']]
        
        return bunches

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
        
        q = omsapi.query("deadtimesperlumisection")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        response = q.data()
        data = response.json()
        deadTime = {}
        for something in data['data']:
            thing = something['attributes']
            deadTime[thing['lumisection_number']] = thing['deadtime_beamactive_total']
            
        return deadTime

    # Use: Gets the L1A physics lost rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysicsLost(self,runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate = {}
        for thing in data:
            something = thing['attributes']
            l1rate[something['lumisection_number']] = something['trigger_physics_lost']['rate']
        
        return l1rate

    # Use: Gets the total L1A physics rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysics(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate = {}
        for thing in data:
            something = thing['attributes']
            l1rate[something['lumisection_number']] = something['l1a_physics']['rate']

        return l1rate

    # Use: Gets the total L1A calibration rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ACalib(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate = {}
        for thing in data:
            something = thing['attributes']
            l1rate[something["lumisection_number"]] = something["l1a_calibration"]['rate']
            
        return l1rate

    # Use: Gets the total L1ARand rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ARand(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate = {}
        for thing in data:
            something = thing['attributes']
            l1rate[something["lumisection_number"]] = something["l1a_random"]['rate']

        return l1rate

    # Use: Gets the TOTAL L1 rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1rate(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerratesperlumisection")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        l1rate = {}
        for thing in data:
            something = thing['attributes']
            l1rate[something["lumisection_number"]] = something["l1a_total"]['rate']

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

    # Use: Get the trigger mode for the specified run
    def getTriggerMode(self, runNumber):
        
        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        mode = item['data'][0]['attributes']['trigger_mode']
        
        return mode

    def getFillRuns(self, fillNumber):
        
        q = omsapi.query("lumisections")
        q.filter("fill_number", fillNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        run_list = []
        for thing in item['data']:
            something = thing['attributes']
            if something['physics_flag']*something['beam1_stable']*something['beam2_stable']:
                if something['run_number'] not in run_list2:
                    run_list.append(something['run_number'])

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

    def getPathsInStreams(self,runNumber):

        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        stream_paths = {}
        for thing in data:
            something = thing['attributes']
            if something['stream_name'] not in stream_paths2:
                stream_paths[something['stream_name']] = []
            if something['path_name'] not in stream_paths2[something['stream_name']]:
                stream_paths[something['stream_name']].append(something['path_name'])

        return stream_paths

    # Returns a list of all L1 triggers used in the run
    def getL1Triggers(self,runNumber):
        
        q = omsapi.query("l1prescalesets")
        q.filter("run_number", runNumber)
        q.per_page = 4000
        response = q.data()
        item = response.json()
        data = item['data']
        L1_list = []
        for thing in data:
            something = thing['attributes']
            L1_list.append(something['algo_name'])

        return L1_list

    # Functionally very similar to getL1RawRates, but allows for specifying which scalar type to query, also does no un-prescaling
    def getL1Rates(self,runNumber,minLS=-1,maxLS=9999999,scaler_type=0):
        self.getRunInfo(runNumber)
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)

        

        return L1Triggers        # {'trigger': {LS: (rate,ps) } }

# -------------------- End of class DBParsing -------------------- #
