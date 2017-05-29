#####################################################################
# File: DataParser.py
# Author: Andrew Wightman
# Date Created: September 15, 2016
#
# Dependencies: DBParser.py
#
# Data Type Key:
#    ( a, b, c, ... )        -- denotes a tuple
#    [ a, b, c, ... ]        -- denotes a list
#    { key:obj }             -- denotes a dictionary
#    { key1: { key2:obj } }  -- denotes a nested dictionary
#####################################################################

import array

from DBParser import *

# --- 13 TeV constant values ---
ppInelXsec = 80000.
orbitsPerSec = 11246.

class DataParser:
    # This is an interface for DBParser() to select and manage the data returned by DBParser()
    def __init__(self):
        # type: () -> None
        self.parser = DBParser()

        # The lists all have the same number of elements, e.g.: len(self.lumi_data[trg][run]) == len(self.pu_data[trg][run])
        self.ls_data   = {}    # {'name': { run_number: [LS] } }
        self.rate_data = {}    # {'name': { run_number: { LS: raw_rates } } }
        self.ps_data   = {}    # {'name': { run_number: { LS: prescale  } } }
        self.pu_data   = {}    # {'name': { run_number: { LS: PU } } }
        self.lumi_data = {}    # {'name': { run_number: { LS: iLumi } } }
        self.det_data  = {}    # {'name': { run_number: { LS: detecotr_ready } } }
        self.bw_data   = {}    # {'name': { run_number: { LS: bandwidth } } }
        self.size_data = {}    # {'name': { run_number: { LS: size } } }
        self.lumi_info = {}    # {run_number: [ (LS,ilum,psi,phys,cms_ready) ] }
        self.bunch_map = {}    # {run_number: nBunches }

        self.hlt_triggers = []  # List of specific HLT triggers we want to get rates for, if empty --> get all HLT rates
        self.l1_triggers  = []  # List of specific L1 triggers we want to get rates for, if empty --> get all L1 rates
        self.runs_used    = []
        self.runs_skipped = []
        self.name_list = []     # List of all named objects for which we have data, e.g. triggers, datasets, streams, etc...
        self.psi_filter = []
        self.type_map = {}      # Maps each object name to a type: trigger, dataset, stream, or L1A
                                # NOTE: Still need to handle the case where if two objects share the same name, but diff type
                                # NOTE2: This approach should be fine, since DataParser owns the nameing, will need to be careful

        self.ls_filter = {}     # {run_number:[LS list]} - LS to ignore

        self.use_prescaled_rate = False # If true, then rates are not un-prescaled
        self.use_cross_section  = False # If true, then divide the rate by inst. lumi (only for L1 and HLT trigger data)
        self.normalize_bunches  = True  # Normalize by the number of colliding bunches
        self.correct_for_DT = True
        self.convert_output = True      # Flag to convert data from { LS: data } to [ data ], used in the data getters

        self.max_deadtime = 10.
        self.min_ls = -1
        self.max_ls = 9999999

        self.use_L1_triggers  = False   # Gets L1 rates
        self.use_HLT_triggers = False   # Gets HLT rates
        self.use_streams      = False   # Gets stream rates
        self.use_datasets     = False   # Gets dataset rates
        self.use_L1A_rate     = False   # Gets the L1A rates

        self.use_ps_mask = False        # Collects data only for LS in the specified prescale indices

        self.use_best_lumi = True       # Uses best luminosity as determined by BRIL
        self.use_PLTZ_lumi = False      # Uses luminosity reading from PLTZ
        self.use_HF_lumi   = False      # Uses luminosity reading from HF

        self.verbose = True

    def parseRuns(self,run_list):
        # type: (List[int]) -> None
        counter = 1
        for run in sorted(run_list):
            if self.verbose: print "Processing run: %d (%d/%d)" % (run,counter,len(run_list))
            counter += 1
            bunches = self.parser.getNumberCollidingBunches(run)[0]

            if bunches is None or bunches is 0:
                bunches = 1

            # [( LS,ilum,psi,phys,cms_ready ) ]
            lumi_info = self.parseLumiInfo(run)
            #if self.use_best_lumi:
            #    lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=0)
            #elif self.use_PLTZ_lumi:
            #    lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=1)
            #elif self.use_HF_lumi:
            #    lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=2)

            run_data = self.getRunData(run,bunches,lumi_info)
            for name in run_data:
                ls_array   = run_data[name]["LS"]
                rate       = run_data[name]["rate"]
                prescale   = run_data[name]["prescale"]
                pu         = run_data[name]["PU"]
                lumi       = run_data[name]["ilumi"]
                det_status = run_data[name]["status"]
                bw         = run_data[name]["bandwidth"]
                size       = run_data[name]["size"]

                if not name in self.name_list:
                    self.name_list.append(name)

                    self.ls_data[name]   = {}
                    self.rate_data[name] = {}
                    self.ps_data[name]   = {}
                    self.pu_data[name]   = {}
                    self.lumi_data[name] = {}
                    self.det_data[name]  = {}
                    self.bw_data[name]   = {}
                    self.size_data[name] = {}

                self.ls_data[name][run]   = ls_array
                self.rate_data[name][run] = rate
                self.ps_data[name][run]   = prescale
                self.pu_data[name][run]   = pu
                self.lumi_data[name][run] = lumi
                self.det_data[name][run]  = det_status
                self.bw_data[name][run]   = bw
                self.size_data[name][run] = size

            if len(run_data.keys()) == 0:   # i.e. no triggers/streams/datasets had enough valid rates
                self.runs_skipped.append(run)
            else:
                self.runs_used.append(run)
                self.bunch_map[run] = bunches
                self.lumi_info[run] = lumi_info

    def parseLumiInfo(self,run):
        # [( LS,ilum,psi,phys,cms_ready ) ]
        lumi_info = []

        trigger_mode = self.parser.getTriggerMode(run)[0]

        if trigger_mode.find('cosmics') > 0:
            # This is a cosmics menu --> No luminosity info
            if self.verbose:
                print "\tDetected cosmics run..."
                print "\tGetting lumi info..."
            for LS,psi in self.parser.getLSInfo(run):
                # We hard code phys and cms_ready to both be true for all LS in the run
                lumi_info.append([LS,0.0,psi,1,1])
        elif trigger_mode.find('collisions') > 0:
            # This is a collisions menu
            if self.verbose:
                print "\tDetected collisions run..."
                print "\tGetting lumi info..."
            if self.use_best_lumi:
                lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=0)
            elif self.use_PLTZ_lumi:
                lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=1)
            elif self.use_HF_lumi:
                lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=2)
        else:
            # Unknown menu --> For now we assume it's compatibale with collisions type menus
            if self.verbose:
                print "\tUnknown run type: %s" % (trigger_mode)
                print "\tGetting lumi info..."
            if self.use_best_lumi:
                lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=0)
            elif self.use_PLTZ_lumi:
                lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=1)
            elif self.use_HF_lumi:
                lumi_info = self.parser.getLumiInfo(run,minLS=self.min_ls,maxLS=self.max_ls,lumi_source=2)
        
        if self.ls_filter.has_key(run):
            new_lumi_info = []
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if LS in self.ls_filter[run]:
                    continue
                new_lumi_info.append([LS,ilum,psi,phys,cms_ready])
            lumi_info = new_lumi_info

        return lumi_info

    # This might be excessive, should think about reworking this section
    # ------
    # TODO: We need to ensure that none of the object names overlap with one another
    # (i.e. dataset names that overlap with stream names) for the rate data.
    def getRunData(self,run,bunches,lumi_info):
        # type: (int,int,List[Tuple[int,float,int,bool,bool]]) -> Dict[str: object]
        run_data = {}
        if bunches is None or bunches is 0:
            if self.verbose: print "Unable to get bunches"
            return {}

        if self.use_streams:
            run_data.update(self.getStreamData(run,bunches,lumi_info))
        if self.use_datasets:
            run_data.update(self.getDatasetData(run,bunches,lumi_info))
        if self.use_L1A_rate:
            run_data.update(self.getL1AData(run,bunches,lumi_info))
        if self.use_HLT_triggers:
            run_data.update(self.getHLTTriggerData(run,bunches,lumi_info))
        if self.use_L1_triggers:
            run_data.update(self.getL1TriggerData(run,bunches,lumi_info))

        return run_data

    # Returns information related to L1 triggers 
    def getL1TriggerData(self,run,bunches,lumi_info):
        # type: (int,int,List[Tuple[int,float,int,bool,bool]]) -> Dict[str: object]
        if self.verbose: print "\tGetting L1 rates..."
        L1_rates = self.parser.getL1Rates(run,minLS=self.min_ls,maxLS=self.max_ls,scaler_type=1)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for trigger in L1_rates:
            self.type_map[trigger] = "trigger"
            run_data[trigger] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            ps_dict    = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if psi not in self.psi_filter and self.use_ps_mask:
                    continue;

                if phys and not ilum is None and L1_rates[trigger].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = L1_rates[trigger][LS][0]
                    prescale = L1_rates[trigger][LS][1]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    if self.use_prescaled_rate:
                        if prescale != 0:
                            rate = rate/prescale
                        #else:
                        #    rate = 0

                    if self.use_cross_section:
                        rate = rate/ilum

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    ps_dict[LS] = prescale
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[trigger]["LS"] = ls_array
            run_data[trigger]["rate"] = rate_dict
            run_data[trigger]["prescale"] = ps_dict
            run_data[trigger]["PU"] = pu_dict
            run_data[trigger]["ilumi"] = lumi_dict
            run_data[trigger]["status"] = det_dict
            run_data[trigger]["bandwidth"] = bw_dict
            run_data[trigger]["size"] = size_dict
        return run_data

    # Returns information related to HLT triggers 
    def getHLTTriggerData(self,run,bunches,lumi_info):
        # type: (int,int,List[Tuple[int,float,int,bool,bool]]) -> Dict[str: object]
        if self.verbose: print "\tGetting HLT rates..."

        HLT_rates = self.parser.getHLTRates(run,self.hlt_triggers,minLS=self.min_ls,maxLS=self.max_ls)

        if self.correct_for_DT:
            self.correctForDeadtime(HLT_rates,run)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for trigger in HLT_rates:
            self.type_map[trigger] = "trigger"
            run_data[trigger] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            ps_dict    = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if psi not in self.psi_filter and self.use_ps_mask:
                    continue;

                if phys and not ilum is None and HLT_rates[trigger].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = HLT_rates[trigger][LS][0]
                    prescale = HLT_rates[trigger][LS][1]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    if self.use_prescaled_rate:
                        if prescale != 0:
                            rate = rate/prescale
                        #else:
                        #    rate = 0

                    if self.use_cross_section:
                        rate = rate/ilum

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    ps_dict[LS] = prescale
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[trigger]["LS"] = ls_array
            run_data[trigger]["rate"] = rate_dict
            run_data[trigger]["prescale"] = ps_dict
            run_data[trigger]["PU"] = pu_dict
            run_data[trigger]["ilumi"] = lumi_dict
            run_data[trigger]["status"] = det_dict
            run_data[trigger]["bandwidth"] = bw_dict
            run_data[trigger]["size"] = size_dict
        return run_data

    def getStreamData(self,run,bunches,lumi_info):
        # type: (int,int,List[Tuple[int,float,int,bool,bool]]) -> Dict[str: object]
        if self.verbose: print "\tGetting Stream rates..."
        data = self.parser.getStreamData(run,minLS=self.min_ls,maxLS=self.max_ls)   # {'stream': [ (LS,rate,size,bandwidth) ] }

        stream_rates = {}   # {'stream': {LS: (rate,size,bandwidth) } }

        # Format the output from DBParser()
        for name in data:
            stream_rates[name] = {}
            for LS, rate, size, bandwidth in data[name]:
                stream_rates[name][LS] = [ rate, size, bandwidth ]

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }
        
        blacklist = ["PhysicsEndOfFill","PhysicsMinimumBias0","PhysicsMinimumBias1","PhysicsMinimumBias2"]
        sum_list = []

        for _object in stream_rates:
            self.type_map[_object] = "stream"
            run_data[_object] = {}

            if _object[:7] == "Physics" and not _object in blacklist:
                sum_list.append(_object)

            ls_array   = array.array('f')
            rate_dict  = {}
            ps_dict    = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if psi not in self.psi_filter and self.use_ps_mask:
                    continue;

                if phys and not ilum is None and stream_rates[_object].has_key(LS):
                #if not ilum is None and stream_rates[_object].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = stream_rates[_object][LS][0]
                    size = stream_rates[_object][LS][1]
                    bandwidth = stream_rates[_object][LS][2]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    ps_dict[LS] = None
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = bandwidth
                    size_dict[LS] = size

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
            run_data[_object]["prescale"] = ps_dict
            run_data[_object]["PU"] = pu_dict
            run_data[_object]["ilumi"] = lumi_dict
            run_data[_object]["status"] = det_dict
            run_data[_object]["bandwidth"] = bw_dict
            run_data[_object]["size"] = size_dict

        self.sumObjects(run_data=run_data,new_name="Combined_Physics_Streams",sum_list=sum_list,obj_type="stream")

        return run_data

    def getDatasetData(self,run,bunches,lumi_info):
        # type: (int,int,List[Tuple[int,float,int,bool,bool]]) -> Dict[str: object]
        if self.verbose: print "\tGetting Dataset rates..."
        data = self.parser.getPrimaryDatasets(run,minLS=self.min_ls,maxLS=self.max_ls)   # {'dataset': [ (LS,rate) ] }

        dataset_rates = {}   # {'dataset': {LS: (rate) } }

        # Format the output from DBParser()
        for name in data:
            dataset_rates[name] = {}
            for LS, rate in data[name]:
                dataset_rates[name][LS] = [ rate ]

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for _object in dataset_rates:
            self.type_map[_object] = "dataset"
            run_data[_object] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            ps_dict    = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if psi not in self.psi_filter and self.use_ps_mask:
                    continue;

                if phys and not ilum is None and dataset_rates[_object].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = dataset_rates[_object][LS][0]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    ps_dict[LS] = None
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
            run_data[_object]["prescale"] = ps_dict
            run_data[_object]["PU"] = pu_dict
            run_data[_object]["ilumi"] = lumi_dict
            run_data[_object]["status"] = det_dict
            run_data[_object]["bandwidth"] = bw_dict
            run_data[_object]["size"] = size_dict
        return run_data

    # NOTE: L1A_rates has a slightly different dict format, the value-pair for the LS keys is NOT a list
    def getL1AData(self,run,bunches,lumi_info):
        # type: (int,int,List[Tuple[int,float,int,bool,bool]]) -> Dict[str: object]
        L1A_rates = {}   # {'L1A': {LS: rate } }
        if self.verbose: print "\tGetting L1APhysics rates..."
        L1A_rates["L1APhysics"] = self.parser.getL1APhysics(run)
        if self.verbose: print "\tGetting L1APhysics+Lost rates..."
        L1A_rates["L1APhysics+Lost"] = self.parser.getL1APhysicsLost(run)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for _object in L1A_rates:
            self.type_map[_object] = "L1A"
            run_data[_object] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            ps_dict    = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if psi not in self.psi_filter and self.use_ps_mask:
                    continue;

                if phys and not ilum is None and L1A_rates[_object].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = L1A_rates[_object][LS]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    ps_dict[LS] = None
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
            run_data[_object]["prescale"] = ps_dict
            run_data[_object]["PU"] = pu_dict
            run_data[_object]["ilumi"] = lumi_dict
            run_data[_object]["status"] = det_dict
            run_data[_object]["bandwidth"] = bw_dict
            run_data[_object]["size"] = size_dict
        return run_data

    # Use: Modifies the rates in Rates, correcting them for deadtime
    # Parameters:
    # -- Rates: A dict - {'trigger': {LS: (raw_rate,prescale) } }
    def correctForDeadtime(self,Rates,run_number):
        # type: (Dict[str,object],int) -> None
        dead_time = self.parser.getDeadTime(run_number)
        for LS in dead_time:
            for trigger in Rates:
                if Rates[trigger].has_key(LS): # Sometimes, LS's are missing
                    Rates[trigger][LS][0] *= (1. + dead_time[LS]/100.)
                    if dead_time[LS] > self.max_deadtime: # Do not plot lumis where deadtime is greater than 10%
                        del Rates[trigger][LS]

    # Creates a new dictionary key, that corresponds to the summed rates of all the specified objects
    # data: {'object': {"LS": list, "rate": {...}, ... } }
    def sumObjects(self,run_data,new_name,sum_list,obj_type):
        # type: (Dict[str,object],str,List[str],str) -> bool
        if not set(sum_list) <= set(run_data.keys()):
            if self.verbose: print "\tERROR: Specified objects that aren't in the run_data"
            return False
        if (len(sum_list)==0):
            print "\tERROR: sum_list has size=0 (see sumObjects in DataParser.py). May be that there were no streams for this run."
            return False
        ref_name = sum_list[0]
        ls_array   = array.array('f')
        rate_dict  = {}
        ps_dict    = {}
        pu_dict    = {}
        lumi_dict  = {}
        det_dict   = {}
        bw_dict    = {}
        size_dict  = {}

        # We only use LS that are in *all* of the objects
        ls_set = set(run_data[ref_name]["LS"])
        for name in sum_list:
            ls_set = ls_set & set(run_data[name]["LS"])
        ls_array.extend(sorted(ls_set))

        for LS in ls_array:
            total_rate = 0
            total_bw   = 0
            total_size = 0
            for name in sum_list:
                total_rate += run_data[name]["rate"][LS]
                try: total_bw     += run_data[name]["bandwidth"][LS]
                except: total_bw   = None

                try: total_size   += run_data[name]["size"][LS]
                except: total_size = None
            rate_dict[LS] = total_rate
            bw_dict[LS]   = total_bw
            size_dict[LS] = total_size
            ps_dict[LS]   = None
            pu_dict[LS]   = run_data[ref_name]["PU"][LS]
            lumi_dict[LS] = run_data[ref_name]["ilumi"][LS]
            det_dict[LS]  = run_data[ref_name]["status"][LS]

        self.type_map[new_name] = obj_type
        run_data[new_name] = {}
        run_data[new_name]["LS"]        = ls_array
        run_data[new_name]["rate"]      = rate_dict
        run_data[new_name]["prescale"]  = ps_dict
        run_data[new_name]["PU"]        = pu_dict
        run_data[new_name]["ilumi"]     = lumi_dict
        run_data[new_name]["status"]    = det_dict
        run_data[new_name]["bandwidth"] = bw_dict
        run_data[new_name]["size"]      = size_dict

        return True

    # Converts input: {'name': { run_number: { LS: data } } } --> {'name': {run_number: [ data ] } }
    def convertOutput(self,_input):
        # type: (Dict[str,object]) -> Dict[str,object]
        output = {}
        for name in _input:
            output[name] = {}
            for run in _input[name]:
                output[name][run] = array.array('f')
                for LS in sorted(_input[name][run].keys()):     # iterating over *sorted* LS is extremely important here
                    output[name][run].append(_input[name][run][LS])
        return output

    def resetData(self):
        # type: () -> None
        self.ls_data   = {}    # {'name': { run_number: [LS] } }
        self.rate_data = {}    # {'name': { run_number: { LS: raw_rates } } }
        self.ps_data   = {}    # {'name': { run_number: { LS: prescale } } }
        self.pu_data   = {}    # {'name': { run_number: { LS: PU } } }
        self.lumi_data = {}    # {'name': { run_number: { LS: iLumi } } }
        self.det_data  = {}    # {'name': { run_number: { LS: detecotr_ready } } }
        self.bw_data   = {}    # {'name': { run_number: { LS: bandwidth } } }
        self.size_data = {}    # {'name': { run_number: { LS: size } } }
        self.lumi_info = {}    # {run_number: [ (LS,ilum,psi,phys,cms_ready) ] }
        self.bunch_map = {}    # {run_number: nBunches }

        self.runs_used    = []
        self.runs_skipped = []
        self.name_list = []
        self.type_map = {}

####################################################################################################

    # --- All the 'getters' ---
    def getLSData(self):
        # type: () -> Dict[str,object]
        return self.ls_data

    def getRateData(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.rate_data)
        else:
            output = self.rate_data
        return output

    def getPSData(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.ps_data)
        else:
            output = self.ps_data
        return output

    def getPUData(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.pu_data)
        else:
            output = self.pu_data
        return output

    def getLumiData(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.lumi_data)
        else:
            output = self.lumi_data
        return output

    def getDetectorStatus(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.det_data)
        else:
            output = self.det_data
        return output

    def getBandwidthData(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.bw_data)
        else:
            output = self.bw_data
        return output

    def getSizeData(self):
        # type: () -> Dict[str,object]
        if self.convert_output:
            output = self.convertOutput(self.size_data)
        else:
            output = self.size_data
        return output

    def getLumiInfo(self):
        # type: () -> Dict[int,List[Tuple]]
        return self.lumi_info

    def getBunchMap(self):
        # type: () -> Dict[int,int]
        return self.bunch_map

    def getRunsUsed(self):
        # type: () -> List[int]
        return self.runs_used

    def getNameList(self):
        # type: () -> List[int]
        return self.name_list

    # Returns all the objects of type obj_type we have rate for
    def getObjectList(self,obj_type):
        # type: (str) -> List[str]
        _list = []
        for obj in self.name_list:
            if self.type_map[obj] == obj_type:
                _list.append(obj)
        return _list

    def getTypeMap(self):
        # type: () -> Dict[str,str]
        return self.type_map
