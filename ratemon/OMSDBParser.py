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
        q = omsapi.query("l1algorithmtriggers")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        q.filter("bit", 1)
        data = q.data().json()['data']
        for thing in data:
            something = thing['attributes']
            ls_info.append([something["first_lumisection_number"], something['initial_prescale']['prescale_index']])
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

        q = omsapi.query("l1algorithmtriggers")
        q.per_page = 4000
        q.filter("run_number", runNumber)
        q.filter("bit",1)
        data = q.data().json()['data']
        for thing in data:
            something = thing['attributes']
            self.PSColumnByLS[something['first_lumisection_number']] = something['initial_prescale']['prescale_index']
        
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
        q.per_page = 400
        response = q.data().json()
        q2 = omsapi.query("l1algorithmtriggers")

        for item in response['data']:
            thing = item['attributes']
            adjusted_lumi = 10000*thing['init_lumi']
            q2.clear_filter()
            q2.filter("run_number", runNumber)
            q2.filter("first_lumisection_number", thing['lumisection_number'])
            data2 = q2.data().json()
            if data2['data'] == []:
                break
            _list.append([thing['lumisection_number'], adjusted_lumi, data2['data'][0]['attributes']['initial_prescale']['prescale_index'], thing['physics_flag']*thing['beam1_present'],
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

        self.HLT_name_map = self.getHLTNameMap(runNumber)

        if len(trigger_list) == 0:
            # If no list is given --> get rates for all HLT triggers
            trigger_list = list(self.HLT_name_map.keys())

        
        q = omsapi.query('hltprescalesets')
        q.custom("filter[run_number]", runNumber)
        q.set_validation(False)
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
            response2 = q2.data()
            item2 = response2.json()
            
            if something['path_name'] not in trigger_rates:
                trigger_rates[something['path_name']] = {}
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
        response = q.data().json()
        data = response['data']

        for row in data:
            bunch = row['attributes']
            if bunch['algo_index'] not in self.L1Prescales:
                self.L1Prescales[bunch['algo_index']] = {}
            for item in bunch['prescales']:
                self.L1Prescales[bunch['algo_index']][item['prescale_index']] = item['prescale']
        
      
    # Note: This function is from DatabaseParser.py (with slight modifications)
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
        
        q = omsapi.query("diplogger")
        q.filter("source_dir", "dip/acc/LHC/RunControl/BeamMode")
        q.filter("dip_time", "last")
        data = q.data().json()
        return data['data'][0]['attributes']['value']
        
    # Use: Gets the dead time as a function of lumisection
    # Returns: A dictionary: [ LS ] <Deadtime>
    def getDeadTime(self,runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("deadtimes")
        q.per_page = 200
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        response = q.data()
        data = response.json()
        deadTime = {}
        for something in data['data']:
            thing = something['attributes']
            deadTime[thing['first_lumisection_number']] = thing['beamactive_total_deadtime']['counter']
            
        return deadTime

    # Use: Gets the L1A physics lost rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysicsLost(self,runNumber,minLS=-1,maxLS=9999999):

        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.per_page=200
        data = q.data().json()
        l1rate = {}
        for item in data['data']:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["trigger_physics_lost"]["rate"]
        
        return l1rate

    # Use: Gets the total L1A physics rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysics(self, runNumber,minLS=-1,maxLS=9999999):
        
       
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.per_page=200
        data = q.data().json()
        l1rate = {}
        for item in data['data']:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_physics"]["rate"]

        return l1rate

    # Use: Gets the total L1A calibration rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ACalib(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.per_page=200
        data = q.data().json()
        l1rate = {}
        for item in data['data']:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_calibration"]["rate"]
            
        return l1rate

    # Use: Gets the total L1ARand rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ARand(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.per_page=200
        data = q.data().json()
        l1rate = {}
        for item in data['data']:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_random"]["rate"]

        return l1rate

    # Use: Gets the TOTAL L1 rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1rate(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.per_page=200
        data = q.data().json()
        l1rate = {}
        for item in data['data']:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_total"]["rate"]

        return l1rate    

    # Use: Returns the number of the latest run to be stored in the DB
    def getLatestRunInfo(self):
        q = omsapi.query("runs")
        q.filter("number_of_lumisections", 1, "GE")
        q.sort("run_number", asc=False)
        data = q.data().json()
        runNumber = data['data'][0]['attributes']['run_number']

        mode = self.getTriggerMode(runNumber)
        isCol = 0
        isGood = 1
        
        if mode is None:
            isGood = 0
        elif mode[0].find('l1_hlt_collisions') != -1:
            isCol = 1
        
            
        return [runNumber, isCol, isGood, mode]

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
                if something['run_number'] not in run_list:
                    run_list.append(something['run_number'])

        return run_list

    # Returns the runs from most recent fill with stable beams
    def getRecentRuns(self):
        
        q = omsapi.query("runs")
        q.filter("stable_beam", True)
        q.sort("fill_number", asc=False)
        q.per_page = 10
        data = q.data().json()
        last_fill = data['data'][0]['attributes']['fill_number']
        run_list = []
        run_list += self.getFillRuns(last_fill)
        
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

    def getL1Rates(self, runNumber, minLS=-1, maxLS=9999999, scalar_type=0):
        self.getRunInfo(runNumber)
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)
        
        L1Triggers = {}
        q = omsapi.query("l1algorithmtriggers")
        q.per_page=200
        q.filter("run_number", runNumber)
        q.custom("group[granularity]", "run")
        data = q.data().json()['data'][0]['attributes']
        first_LS = data['first_lumisection_number']
        last_LS = data['last_lumisection_number']
        for i in range(first_LS, last_LS):
            q.clear_filter()
            q.filter("run_number", runNumber)
            q.filter("first_lumisection_number", i)
            data = q.data().json()['data']
            for item in data:
                if item['attributes']['name'] not in L1Triggers:
                    L1Triggers[item['attributes']['name']] = {}
                L1Triggers[item['attributes']['name']][i] = [item['attributes']['pre_dt_rate'], item['attributes']['initial_prescale']['prescale']]
                
        return L1Triggers

# -------------------- End of class DBParsing -------------------- #
