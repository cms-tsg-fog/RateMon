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
import sys
import os
import socket
import yaml

from omsapi import OMSAPI

PAGE_LIMIT = 10000

#initiate connection to endpoints and authenticate
hostname = socket.gethostname()

#This option uses a DB authentication only available on lxplus
if "lxplus" in hostname:
    omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1", cert_verify=False, verbose=False)
    omsapi.auth_krb()
#This option uses a token setup for the API VMs
elif "ruber" in hostname or "ater" in hostname or "caer" in hostname:
    stream = open(str('OMSConfig.yaml'), 'r')
    cfg  = yaml.safe_load(stream)
    my_app_id = cfg['token_info']['token_name']
    my_app_secret = cfg['token_info']['token_secret']
    omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1", cert_verify=False, verbose=False)
    omsapi.auth_oidc(my_app_id, my_app_secret, audience="cmsoms-prod")
#This option is for P5, no authentication necessary
else:
    omsapi = OMSAPI("http://cmsoms.cms:8080/api", verbose=False)

# Key version stripper
def stripVersion(name):
    if re.match('.*_v[0-9]+',name): name = name[:name.rfind('_')]
    return name

# A class that interacts with OMS and fetches information that we need
class DBParser:
    def __init__(self) :

        self.L1Prescales = {}       # {algo_index: {psi: prescale}}
        self.HLTPrescales = {}      # {'trigger': [prescales]}
        self.HLTSequenceMap = {}
        self.GTRS_Key = ""
        self.HLT_Key  = ""
        self.TSC_Key  = ""
        self.ConfigId = ""
        self.GT_Key   = ""

        self.HLTSeed = {}
        self.L1Mask = {}
        self.L1IndexNameMap = {}
        self.L1NameIndexMap = {}
        self.PSColumnByLS = {}

    #returns the lumisection number with prescale index
    def getLSInfo(self, runNumber):

        ls_info = []
        q = omsapi.query("l1algorithmtriggers")
        q.per_page = PAGE_LIMIT
        q.filter("run_number", runNumber)
        q.filter("bit", 0)
        q.custom("fields", "first_lumisection_number,initial_prescale")
        try:
            data = q.data().json()['data']
        except:
            print("Unable to get LS list for run %s" % runNumber)
            return []
        for item in data:
            ls_info.append([item['attributes']["first_lumisection_number"], item['attributes']['initial_prescale']['prescale_index']])

        return ls_info

    # Returns the various keys used for the specified run as a 5-tuple
    def getRunKeys(self,runNumber):

        L1_HLT,HLT,GTRS,TSC,GT = "","","","",""
        q = omsapi.query("l1configurationkeys")
        q.per_page=1
        q.filter("run_number", runNumber)
        q.custom("fields", "l1_hlt_mode_stripped,run_settings_key,l1_key,gt_key")
        q2 = omsapi.query("hltconfig")
        q2.set_validation(False)
        q2.per_page=1
        q2.filter("run_number", runNumber)
        q2.custom("fields", "config_name")
        try:
            item = q.data().json()['data'][0]['attributes']
            L1_HLT = item['l1_hlt_mode_stripped']
            GTRS = item['run_settings_key']
            TSC = item['l1_key']
            GT = item['gt_key']
            item2 = q2.data().json()['data'][0]['attributes']
            HLT = item2['config_name']
        except:
            print("[ERROR] Unable to get keys for this run, %d" % (runNumber))
        
        return L1_HLT,HLT,GTRS,TSC,GT

    # Returns: True if we succeded, false if the run doesn't exist (probably)
    # Populates self.PSColumnByLS (which prescale column is used in the LS)
    # Populates self.L1_HLT_Key, self.HLT_Key, self.GTRS_Key, self.TSC_Key, self.GT_Key via getRunKeys()
    def getRunInfo(self, runNumber):

        q = omsapi.query("l1algorithmtriggers")
        q.per_page = PAGE_LIMIT
        q.filter("run_number", runNumber)
        q.filter("bit",0)
        q.custom("fields", "first_lumisection_number,initial_prescale")
        try:
            data = q.data().json()['data']
        except:
            print("Trouble getting PS column by LS")
            return False
        for item in data:
            self.PSColumnByLS[item['attributes']['first_lumisection_number']] = item['attributes']['initial_prescale']['prescale_index']
        
        self.L1_HLT_Key, self.HLT_Key, self.GTRS_Key, self.TSC_Key, self.GT_Key = self.getRunKeys(runNumber)
        if self.HLT_Key == "":
            # The key query failed
            return False
        else:
            return True

    # Returns: A list of of information for each LS: ( { LS, instLumi, physics } )                                                                                                                    
    def getLumiInfo(self,runNumber,minLS=-1,maxLS=9999999):

        _list = []
        q = omsapi.query("lumisections")
        q.filter("run_number", runNumber)
        q.filter("lumisection_number", minLS, operator="GE")
        q.filter("lumiseciton_number", maxLS, operator="LE")
        q.custom("include", "meta")
        q.per_page = PAGE_LIMIT
        response = q.data().json()
        if response['data'][0]['meta']['row']['init_lumi']['units']=="10^{33}cm^{-2}s^{-1}":
            adjust = 1000
        elif response['data'][0]['meta']['row']['init_lumi']['units']=="10^{34}cm^{-2}s^{-1}":
            adjust = 10000
        else:
            adjust = 1
        q2 = omsapi.query("prescalechanges")
        q2.filter("run_number", runNumber)
        q2.custom("fields", "lumisection_number,new_prescale_index")
        q2.per_page = PAGE_LIMIT
        response2 = q2.data().json()
        for item in response['data']:
            thing = item['attributes']
            for ps_index in response2['data']:
                if thing['lumisection_number'] >= ps_index['attributes']['lumisection_number']:
                    ps = ps_index['attributes']['new_prescale_index'] 
            adjusted_lumi = adjust*thing['init_lumi']
            _list.append([thing['lumisection_number'], adjusted_lumi, ps, thing['physics_flag']*thing['beam1_present'],
                          thing['physics_flag']*thing['beam1_present']*thing['ebp_ready']*thing['ebm_ready']*
                          thing['eep_ready']*thing['eem_ready']*thing['hbhea_ready']*thing['hbheb_ready']*
                          thing['hbhec_ready']*thing['hf_ready']*thing['ho_ready']*thing['rpc_ready']*thing['dt0_ready']*
                          thing['dtp_ready']*thing['dtm_ready']*thing['cscp_ready']*thing['cscm_ready']*thing['tob_ready']*
                          thing['tibtid_ready']*thing['tecp_ready']*thing['tecm_ready']*thing['bpix_ready']*
                          thing['fpix_ready']*thing['esp_ready']*thing['esm_ready'],thing['pileup']])
            if thing['lumisection_number'] == maxLS:
                break
        return _list

    # Use: Gets the HLT rates in a run
    # Parameters: runNumer: the number of tbe run, trigger_list, triggers to get the rate of, minLS, maxLS: LS range
    # Returns: dictionary [tirgger_name][LS] <rate><prescale>
    def getHLTRates(self, runNumber, trigger_list=[],minLS=-1, maxLS=9999999):

        # First we need the HLT and L1 prescale rates and the HLT seed info                                                                                                                                
        if not self.getRunInfo(runNumber):
            print("Failed to get run info ")
            return {} # The run probably doesn't exist
        # Get L1 info                                                                                                                                                                                     
        self.getL1Info(runNumber)
        # Get HLT info
        self.getHLTSeeds(runNumber)
        self.getHLTPrescales(runNumber)
        self.HLT_name_map = self.getHLTNameMap(runNumber)

        trigger_list_version = []

        # If no list is given --> get rates for all HLT triggers
        if len(trigger_list) == 0:
            trigger_list_version = self.HLT_name_map.keys()
        else:
            for trigger in self.HLT_name_map.keys():
                if stripVersion(trigger) in trigger_list:
                    trigger_list_version.append(trigger)

        trigger_rates = {}
        for name in trigger_list_version:
            # Ignore triggers which don't appear in this run
            if not self.HLT_name_map:
                continue
            trigger_rates[stripVersion(name)] = self.getSingleHLTRate(runNumber,name,minLS,maxLS)

        return trigger_rates

    # Use: Gets the HLT rates of a single trigger
    # Note: This is only designed to be called within getHLTRates, since it depends on many self variables being populated before calling
    def getSingleHLTRate(self, runNumber, name, minLS=-1, maxLS=9999999):

        q = omsapi.query("hltpathrates")
        q.filter("run_number", runNumber)
        q.filter("path_name", name)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,rate")
        q.per_page = PAGE_LIMIT
        data = q.data().json()['data']
        trigger_rates = {}
        for item in data:
            LS = item['attributes']['first_lumisection_number']
            rate = item['attributes']['rate']
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

    # Returns: The minimum prescale value                                                                                                                                                                  
    def UnwindORSeed(self,expression,L1Prescales,psi):

        """                                                                                                                                                                                                
        Figures out the effective prescale for the OR of several seeds                                                                                                                                     
        we take this to be the *LOWEST* prescale of the included seeds                                                                                                                                     
        """
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
            if seed not in self.L1IndexNameMap:
                continue
            ps = L1Prescales[self.L1IndexNameMap[seed]][psi]
            if ps: minPS = min(ps,minPS)

        if minPS == 99999999999: return 0
        else: return minPS

    # Generates a dictionary that maps HLT path names to the corresponding path_id
    def getHLTNameMap(self,runNumber):
        
        q = omsapi.query("hltpathinfo")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.custom("fields", "path_name,path_id")
        q.per_page = PAGE_LIMIT
        data = q.data().json()['data']
        name_map = {}
        for item in data:
            name_map[item['attributes']['path_name']] = item['attributes']['path_id']
        
        return name_map

    # Use: Sets the L1 seed that each HLT trigger depends on
    # Returns: (void)
    # Note: Populates self.HLTSeed
    def getHLTSeeds(self, runNumber):
        
        if self.HLT_Key == "": self.getRunInfo(runNumber)
        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.custom("fields", "path_name,l1_prerequisite")
        q.per_page = PAGE_LIMIT
        data = q.data().json()['data']
        for item in data:
            if item['attributes']['l1_prerequisite'] != None:
                self.HLTSeed[item['attributes']['path_name']] = item['attributes']['l1_prerequisite'].lstrip('"').rstrip('"')

    # Use: Gets the prescales for the various HLT triggers
    def getHLTPrescales(self, runNumber):

        q = omsapi.query("hltprescalesets")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = PAGE_LIMIT
        data = q.data().json()['data']
        for item in data:
            row = []
            for a in item['attributes']['prescales']:
                row.append(a['prescale'])
            self.HLTPrescales[item['attributes']['path_name']] = row            

    # Use: Gets the number of colliding bunches during a run
    # Returns: list [bunches_colliding, bunches_target]
    def getNumberCollidingBunches(self, runNumber):
        
        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        q.custom("fields", "fill_number")
        q.per_page = 1
        data = q.data().json()
        q2 = omsapi.query("fills")
        q2.filter("fill_number", data['data'][0]['attributes']['fill_number'])
        q2.custom("fields", "bunches_colliding,bunches_target")
        q2.per_page = 1
        data2 = q2.data().json()
        try:
            bunches = [data2['data'][0]['attributes']['bunches_colliding'], data2['data'][0]['attributes']['bunches_target']]
        except:
            print("Failed to get run info")
            return [0,0]

        if bunches[0] == None:
            bunches[0] = 0
        if bunches[1] == None:
            bunches[1] = 0

        return bunches
    
    def getFillType(self, runNumber):
        
        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        q.custom("fields", "fill_number")
        q.per_page = 1
        data = q.data().json()
        q2 = omsapi.query("fills")
        q2.filter("fill_number", data['data'][0]['attributes']['fill_number'])
        q2.custom("fields", "fill_type_runtime")
        q2.per_page = 1
        data2 = q2.data().json()
        try:
            fill_type = data2['data'][0]['attributes']['fill_type_runtime']
        except:
            print("Failed to get run info")
            return None 
        return fill_type

    # Use: Get the latest LHC Satus
    # Returns: string
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
        q.per_page = PAGE_LIMIT
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,beamactive_total_deadtime")
        data = q.data().json()['data']
        deadTime = {}
        for item in data:
            deadTime[item['attributes']['first_lumisection_number']] = item['attributes']['beamactive_total_deadtime']['percent']
            
        return deadTime

    # Use: Gets the L1A physics lost rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysicsLost(self,runNumber,minLS=-1,maxLS=9999999):

        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,trigger_physics_lost")
        data = q.data().json()['data']
        l1rate = {}
        for item in data:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["trigger_physics_lost"]["rate"]
        
        return l1rate

    # Use: Gets the total L1A physics rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1APhysics(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,l1a_physics")
        q.per_page=PAGE_LIMIT
        data = q.data().json()['data']
        l1rate = {}
        for item in data:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_physics"]["rate"]

        return l1rate

    # Use: Gets the total L1 rate before DT
    # Returns: A dictionary: [ LS ] <rate>
    def getL1TotalPreDT(self, runNumber,minLS=-1,maxLS=9999999):

        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,total_before_deadtime")
        q.per_page=PAGE_LIMIT
        data = q.data().json()['data']
        l1rate = {}
        for item in data:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["total_before_deadtime"]["rate"]

        return l1rate

    # Use: Gets the total L1A calibration rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ACalib(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.filter("run_number", runNumber)
        q.custom("fields", "first_lumisection_number,l1a_calibration")
        q.per_page=PAGE_LIMIT
        data = q.data().json()['data']
        l1rate = {}
        for item in data:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_calibration"]["rate"]
            
        return l1rate

    # Use: Gets the total L1ARand rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1ARand(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,l1a_random")
        q.per_page=PAGE_LIMIT
        data = q.data().json()['data']
        l1rate = {}
        for item in data:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_random"]["rate"]

        return l1rate

    # Use: Gets the TOTAL L1 rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <rate>
    def getL1rate(self, runNumber,minLS=-1,maxLS=9999999):
        
        q = omsapi.query("l1triggerrates")
        q.custom("group[granularity]", "lumisection")
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", minLS, "GE")
        q.filter("last_lumisection_number", maxLS, "LE")
        q.custom("fields", "first_lumisection_number,l1a_total")
        q.per_page=PAGE_LIMIT
        data = q.data().json()['data']
        l1rate = {}
        for item in data:
            l1rate[item['attributes']["first_lumisection_number"]] = item['attributes']["l1a_total"]["rate"]

        return l1rate    

    # Use: Returns the number of the latest run to be stored in the DB
    # Returns: list, [runNumber, isCol, isGood, mode]
    def getLatestRunInfo(self):
        q = omsapi.query("runs")
        q.filter("last_lumisection_number", 1, "GE")
        q.sort("run_number", asc=False)
        q.custom("fields", "run_number")
        q.per_page = 1
        data = q.data().json()
        try:
            runNumber = data['data'][0]['attributes']['run_number']
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
        
        return [runNumber, isCol, isGood, mode]

    # Use: Get the trigger mode for the specified run
    # Returns: string
    def getTriggerMode(self, runNumber):
        
        q = omsapi.query("runs")
        q.filter("run_number", runNumber)
        q.custom("fields", "trigger_mode")
        q.per_page = 1
        try:
            mode = q.data().json()['data'][0]['attributes']['trigger_mode']
        except:
            print("Error: Unable to retrieve trigger mode.")
        
        return mode

    # Use: Get the lastest runs in a fill with stable beam
    # Returns: list, with run numbers
    def getFillRuns(self, fillNumber):
        
        q = omsapi.query("lumisections")
        q.filter("fill_number", fillNumber)
        q.custom("fields", "physics_flag,beam1_stable,beam2_stable,run_number")
        q.per_page = PAGE_LIMIT
        data = q.data().json()['data']
        run_list = []
        for item in data:
            if item['attributes']['physics_flag']*item['attributes']['beam1_stable']*item['attributes']['beam2_stable']:
                if item['attributes']['run_number'] not in run_list:
                    run_list.append(item['attributes']['run_number'])

        return run_list

    # Returns the runs from most recent fill with stable beams
    def getRecentRuns(self):
        
        q = omsapi.query("runs")
        q.filter("stable_beam", True)
        q.sort("fill_number", asc=False)
        q.custom("fields", "fill_number")
        q.per_page = 1
        data = q.data().json()
        last_fill = data['data'][0]['attributes']['fill_number']
        run_list = []
        run_list += self.getFillRuns(last_fill)

        return run_list, last_fill

    # Use: Get the list of streams and each HLT path in those streams
    # Returns: dictionary, [Stream]<path>
    def getPathsInStreams(self,runNumber):
        
        q = omsapi.query("hltconfigdata")
        q.set_validation(False)
        q.filter("run_number", runNumber)
        q.per_page = PAGE_LIMIT
        q.custom("fields", "stream_name,path_name")
        data = q.data().json()['data']
        stream_paths = {}
        for item in data:
            if item['attributes']['stream_name'] == None:
                continue
            if item['attributes']['stream_name'] not in stream_paths:
                stream_paths[item['attributes']['stream_name']] = []
            if item['attributes']['path_name'] not in stream_paths[item['attributes']['stream_name']]:
                stream_paths[item['attributes']['stream_name']].append(stripVersion(item['attributes']['path_name']))

        return stream_paths

    # Returns a list of all L1 triggers used in the run
    def getL1Triggers(self,runNumber):
        
        q = omsapi.query("l1prescalesets")
        q.filter("run_number", runNumber)
        q.per_page = PAGE_LIMIT
        q.custom("fields", "algo_name")
        data = q.data().json()['data']
        L1_list = []
        for item in data:
            L1_list.append(item['attributes']['algo_name'])

        return L1_list

    # Use: Gets the rates of L1 triggers per lumiseciton
    # Returns: dictionary <trigger_name><LS>(rate, prescale)
    def getL1Rates(self, runNumber, minLS=-1, maxLS=9999999, trigList=[]):
        
        L1Triggers = {}
        #Get all the triggers in one query
        if trigList == []:
            q = omsapi.query("l1algorithmtriggers/ratemon")
            q.filter("run_number", runNumber)
            try:
                data = q.data().json()['data']['attributes']
            except:
                print("Failed to get L1Prescales")
                return {}
            for lumi, item in enumerate(data['lumisections']):
                #bypass lumisecion 0, which is empty
                if item == {}:
                    continue
                if lumi < minLS:
                    continue
                if lumi > maxLS:
                    break
                for (rate, name, prescale) in zip(item['pre_dt_before_prescale_rate'], data['names'], data['prescales']):
                    if name == None or prescale == None:
                        continue
                    if name not in L1Triggers:
                        L1Triggers[name] = {}
                    L1Triggers[name][lumi] = [rate, prescale['value']]

        #Get the triggers for a subset of the total list, getting them one at a time
        else: 
            q = omsapi.query("l1algorithmtriggers")
            q.custom("fields", "pre_dt_before_prescale_rate,initial_prescale,first_lumisection_number")
            for name in trigList:
                L1Triggers[name] = {}
                q.clear_filter()
                q.filter("run_number", runNumber)
                q.filter("name", name)
                q.per_page = PAGE_LIMIT
                try:
                    data = q.data().json()['data']
                except:
                    print("Failed to get L1Prescales")
                    return {}
                for lumi, item in enumerate(data):
                    if lumi < minLS:
                        continue
                    if lumi > maxLS:
                        break
                    L1Triggers[name][lumi] = [item['attributes']['pre_dt_before_prescale_rate'], item['attributes']['initial_prescale']['prescale']]

        return L1Triggers

    # Use: Get the rates per stream as a function of lumisection
    # Returns: dictionary, <stream>(LS, rate, size, bandwidth)
    def getStreamData(self, runNumber, minLS=-1, maxLS=9999999):

        StreamData = {}
        if minLS < 1:
            minLS = 1
        for LS in range(minLS, maxLS):
            q = omsapi.query("streams")
            q.per_page=PAGE_LIMIT
            q.filter("run_number", runNumber)
            q.filter("last_lumisection_number", LS)
            q.custom("fields", "last_lumisection_number,rate,file_size,bandwidth,stream_name")
            response = q.data().json()['data']
            if response == []:
                break
            for item in response:
                stream_name = item['attributes']['stream_name']
                if stream_name not in StreamData:
                    StreamData[stream_name] = []
                StreamData[stream_name].append([item['attributes']['last_lumisection_number'], 
                                                item['attributes']['rate'], 
                                                item['attributes']['file_size']*1000000000, 
                                                item['attributes']['bandwidth']*1000000])
        return StreamData

    # Use: Get info for L1 prescales and bit trigger relations
    # Returns: void
    # Note: populates: self.L1IndexNameMap, self.L1NameIndexMap, self.L1Mask, self.L1Prescales
    def getL1Info(self, runNumber):
        
        q = omsapi.query("l1prescalesets")
        q.filter("run_number", runNumber)
        q.per_page = PAGE_LIMIT
        try:
            data = q.data().json()['data']
        except:
            print("Get L1 Name Index failed")
            return
        for item in data:
            self.L1IndexNameMap[item['attributes']['algo_name']] = item['attributes']['algo_index']
            self.L1NameIndexMap[item['attributes']['algo_index']] = item['attributes']['algo_name']
            self.L1Mask[item['attributes']['algo_index']] = item['attributes']['algo_mask']
            if item['attributes']['algo_index'] not in self.L1Prescales:
                self.L1Prescales[item['attributes']['algo_index']] = {}
            for row in item['attributes']['prescales']:
                self.L1Prescales[item['attributes']['algo_index']][row['prescale_index']] = row['prescale']

    # Use: Get the rate for each dataset in a run
    # Returns: dicitonary <Dataset name>[lumiseciton, rate]
    def getPrimaryDatasets(self, runNumber, minLS=-1, maxLS=9999999):

        q = omsapi.query("datasetrates")
        q.per_page = PAGE_LIMIT
        q.filter("run_number", runNumber)
        q.filter("first_lumisection_number", 1)
        q.custom("fields", "rate,dataset_name,first_lumisection_number,last_lumisection_number")
        try:
            data = q.data().json()['data']
        except:
            print("Error: Unable to retrieve PD data.")
        PrimaryDatasets = {}
        for item in data:
            PrimaryDatasets[item['attributes']['dataset_name']] = []
            q.clear_filter()
            q.filter("run_number", runNumber)
            q.filter("dataset_name", item['attributes']['dataset_name'])
            q.filter("first_lumisection_number", minLS, "GE")
            q.filter("last_lumisection_number", maxLS, "LE")
            rates = q.data().json()['data']
            for rate in rates:
                PrimaryDatasets[item['attributes']['dataset_name']].append([rate['attributes']['first_lumisection_number'], rate['attributes']['rate']])

        return PrimaryDatasets
        
    # This is a function for the old DBParser.py that was not able to be transferred to the OMS DB                                                                                                                                                                                                                                                                         
    # It is designed to get the list of Datasets and each HLT path within it                                                                                                                                                                                                                                                                                               
    # Returns: dicitonary <Dataset name>(HLT path) 
    def getPathsInDatastes(self, runNumber):
        raise NotImplemented()

# -------------------- End of class DBParsing -------------------- #
