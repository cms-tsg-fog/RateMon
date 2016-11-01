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

# This is an interface for DBParser() to select and manage the data returned by DBParser()
class DataParser:
    def __init__(self):
        self.parser = DBParser()

        # The lists all have the same number of elements, e.g.: len(self.lumi_data[trg][run]) == len(self.pu_data[trg][run])
        self.ls_data   = {}    # {'name': { run_number: [LS] } }
        self.rate_data = {}    # {'name': { run_number: { LS: raw_rates } } }
        self.pu_data   = {}    # {'name': { run_number: { LS: PU } } }
        self.lumi_data = {}    # {'name': { run_number: { LS: iLumi } } }
        self.det_data  = {}    # {'name': { run_number: { LS: detecotr_ready } } }
        self.bw_data   = {}    # {'name': { run_number: { LS: bandwidth } } }
        self.size_data = {}    # {'name': { run_number: { LS: size } } }
        self.lumi_info = {}    # {run_number: [ (LS,ilum,psi,phys,cms_ready) ] }
        self.bunch_map = {}    # {run_number: nBunches}

        self.runs_used    = []
        self.runs_skipped = []
        self.name_list = []     # List of named objects for which we have data, e.g. triggers, datasets, streams, etc...
        self.type_map = {}      # Maps each object name to a type: trigger, dataset, stream, or L1A
                                # NOTE: Still need to handle the case where if two objects share the same name, but diff type
                                # NOTE2: This approach should be fine, since DataParser owns the nameing, will need to be careful

        self.normalize_bunches = True
        self.correct_for_DT = True
        self.convert_output = True      # Flag to convert data from { LS: data } to [ data ], used in the data getters

        self.max_dead_time = 10.

        self.use_L1_triggers  = False   # Plot L1 rates
        self.use_HLT_triggers = False   # Plot HLT rates
        self.use_streams      = False   # Plot stream rates
        self.use_datasets     = False   # Plot dataset rates
        self.use_L1A_rate     = False   # Plots the L1A rates

        self.use_PLTZ_lumi = False
        self.use_HF_lumi   = False
        self.use_best_lumi = True

    def parseRuns(self,run_list):
        counter = 1
        for run in sorted(run_list):
            print "Processing run: %d (%d/%d)" % (run,counter,len(run_list))
            counter += 1
            print "\tGetting lumi info..."
            lumi_info = self.parser.getLumiInfo(run)                        # [( LS,ilum,psi,phys,cms_ready ) ]
            bunches = self.parser.getNumberCollidingBunches(run)[0]
            run_data = self.getRunData(run,bunches,lumi_info)
            for name in run_data:
                ls_array   = run_data[name]["LS"]
                rate       = run_data[name]["rate"]
                pu         = run_data[name]["PU"]
                lumi       = run_data[name]["ilumi"]
                det_status = run_data[name]["status"]
                bw         = run_data[name]["bandwidth"]
                size       = run_data[name]["size"]

                if not name in self.name_list:
                    self.name_list.append(name)

                    self.ls_data[name]   = {}
                    self.rate_data[name] = {}
                    self.pu_data[name]   = {}
                    self.lumi_data[name] = {}
                    self.det_data[name]  = {}
                    self.bw_data[name]   = {}
                    self.size_data[name] = {}

                self.ls_data[name][run]   = ls_array
                self.rate_data[name][run] = rate
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

    # This might be excessive, should think about reworking this section
    # ------
    # TODO: We need to ensure that none of object names overlap with one another
    # (i.e. dataset names overlap with stream names) for the rate data.
    def getRunData(self,run,bunches,lumi_info):
        run_data = {}

        if bunches is None or bunches is 0:
            print "Unable to get bunches"
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
        print "\tGetting L1 rates..."
        L1_rates = self.parser.getL1Rates(run,scaler_type=1)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for trigger in L1_rates:
            self.type_map[trigger] = "trigger"
            run_data[trigger] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if phys and not ilum is None and L1_rates[trigger].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = L1_rates[trigger][LS][0]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[trigger]["LS"] = ls_array
            run_data[trigger]["rate"] = rate_dict
            run_data[trigger]["PU"] = pu_dict
            run_data[trigger]["ilumi"] = lumi_dict
            run_data[trigger]["status"] = det_dict
            run_data[trigger]["bandwidth"] = bw_dict
            run_data[trigger]["size"] = size_dict
        return run_data

    # Returns information related to HLT triggers 
    def getHLTTriggerData(self,run,bunches,lumi_info):
        print "\tGetting HLT rates..."
        HLT_rates = self.parser.getRawRates(run)
        if self.correct_for_DT:
            self.correctForDeadtime(HLT_rates,run)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for trigger in HLT_rates:
            self.type_map[trigger] = "trigger"
            run_data[trigger] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if phys and not ilum is None and HLT_rates[trigger].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = HLT_rates[trigger][LS][0]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[trigger]["LS"] = ls_array
            run_data[trigger]["rate"] = rate_dict
            run_data[trigger]["PU"] = pu_dict
            run_data[trigger]["ilumi"] = lumi_dict
            run_data[trigger]["status"] = det_dict
            run_data[trigger]["bandwidth"] = bw_dict
            run_data[trigger]["size"] = size_dict
        return run_data

    def getStreamData(self,run,bunches,lumi_info):
        print "\tGetting Stream rates..."
        data = self.parser.getStreamData(run)   # {'stream': [ (LS,rate,size,bandwidth) ] }

        stream_rates = {}   # {'stream': {LS: (rate,size,bandwidth) } }

        # Format the output from DBParser()
        for name in data:
            stream_rates[name] = {}
            for LS, rate, size, bandwidth in data[name]:
                stream_rates[name][LS] = [ rate, size, bandwidth ]

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for _object in stream_rates:
            self.type_map[_object] = "stream"
            run_data[_object] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if phys and not ilum is None and stream_rates[_object].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = stream_rates[_object][LS][0]
                    size = stream_rates[_object][LS][1]
                    bandwidth = stream_rates[_object][LS][2]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = bandwidth
                    size_dict[LS] = size

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
            run_data[_object]["PU"] = pu_dict
            run_data[_object]["ilumi"] = lumi_dict
            run_data[_object]["status"] = det_dict
            run_data[_object]["bandwidth"] = bw_dict
            run_data[_object]["size"] = size_dict
        return run_data

    def getDatasetData(self,run,bunches,lumi_info):
        print "\tGetting Dataset rates..."
        data = self.parser.getPrimaryDatasets(run)   # {'dataset': [ (LS,rate) ] }

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
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if phys and not ilum is None and dataset_rates[_object].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = dataset_rates[_object][LS][0]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
            run_data[_object]["PU"] = pu_dict
            run_data[_object]["ilumi"] = lumi_dict
            run_data[_object]["status"] = det_dict
            run_data[_object]["bandwidth"] = bw_dict
            run_data[_object]["size"] = size_dict
        return run_data

    # NOTE: L1A_rates has a slightly different dict format, the value-pair for the LS keys is NOT a list
    def getL1AData(self,run,bunches,lumi_info):
        L1A_rates = {}   # {'L1A': {LS: rate } }
        print "\tGetting L1APhysics rates..."
        L1A_rates["L1APhysics"] = self.parser.getL1APhysics(run)
        print "\tGetting L1APhysics+Lost rates..."
        L1A_rates["L1APhysics+Lost"] = self.parser.getL1APhysicsLost(run)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for _object in L1A_rates:
            self.type_map[_object] = "L1A"
            run_data[_object] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if phys and not ilum is None and L1A_rates[_object].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = L1A_rates[_object][LS]

                    if self.normalize_bunches:
                        rate = rate/bunches

                    ls_array.append(LS)
                    rate_dict[LS] = rate
                    pu_dict[LS] = pu
                    lumi_dict[LS] = ilum
                    det_dict[LS] = cms_ready
                    bw_dict[LS] = None
                    size_dict[LS] = None

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
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
        # Get the deadtime
        dead_time = self.parser.getDeadTime(run_number)
        for LS in dead_time:
            for trigger in Rates:
                if Rates[trigger].has_key(LS): # Sometimes, LS's are missing
                    Rates[trigger][LS][0] *= (1. + dead_time[LS]/100.)
                    #if deadTime[LS] > self.maxDeadTime and not self.certifyMode:
                    if dead_time[LS] > self.max_dead_time: # Do not plot lumis where deadtime is greater than 10%
                        del Rates[trigger][LS]

    # Creates a new dictionary key, that corresponds to the summed rates of all the specified objects
    def sumObjects(self,new_name,sum_list,obj_type):
        if not set(sum_list) <= set(self.name_list):
            print "ERROR: Specified objects that aren't in the name_list"
            return False

        ref_name = sum_list[0]

        self.ls_data[new_name]   = {}
        self.rate_data[new_name] = {}
        self.pu_data[new_name]   = {}
        self.lumi_data[new_name] = {}
        self.det_data[new_name]  = {}
        self.bw_data[new_name]   = {}
        self.size_data[new_name] = {}

        for run in self.runs_used:
            # Use only LS that are in ALL objects
            # Possible alternative, is to instead assume rate = 0 for objects missing LS
            try:
                ls_set = set(self.ls_data[sum_list[0]][run])
                for obj in sum_list:
                    ls_set = ls_set & set(self.ls_data[obj][run])
                ls_array = array.array('f')
                ls_array.extend(sorted(ls_set))
            except KeyError:
                print "WARNING: At least one object for summing has no data for run %d" % run
                continue

            self.ls_data[new_name][run]   = ls_array

            self.rate_data[new_name][run] = {}
            self.pu_data[new_name][run]   = {}
            self.lumi_data[new_name][run] = {}
            self.det_data[new_name][run]  = {}
            self.bw_data[new_name][run]   = {}
            self.size_data[new_name][run] = {}

            for LS in ls_array:
                self.pu_data[new_name][run][LS]   = self.pu_data[ref_name][run][LS]
                self.lumi_data[new_name][run][LS] = self.lumi_data[ref_name][run][LS]
                self.det_data[new_name][run][LS]  = self.det_data[ref_name][run][LS]

                total_rate = 0
                total_bw = 0
                total_size = 0
                for obj in sum_list:
                    total_rate += self.rate_data[obj][run][LS]
                    try:
                        total_bw   += self.bw_data[obj][run][LS]
                        total_size += self.size_data[obj][run][LS]
                    except:
                        total_bw = None
                        total_size = None
                self.rate_data[new_name][run][LS] = total_rate
                self.bw_data[new_name][run][LS] = total_bw
                self.size_data[new_name][run][LS] = total_size

        self.name_list.append(new_name)
        self.type_map[new_name] = obj_type
        return True

    # Converts input: {'name': { run_number: { LS: data } } } --> {'name': run_number: [ data ] }
    def convertOutput(self,_input):
        output = {}
        for name in _input:
            output[name] = {}
            for run in _input[name]:
                output[name][run] = array.array('f')
                for LS in sorted(_input[name][run].keys()):     # iterating over sorted LS is extremely important here
                    output[name][run].append(_input[name][run][LS])
        return output

####################################################################################################

    # --- All the 'getters' ---
    def getLSData(self):
        return self.ls_data

    def getRateData(self):
        if self.convert_output:
            output = self.convertOutput(self.rate_data)
        else:
            output = self.rate_data
        return output

    def getPUData(self):
        if self.convert_output:
            output = self.convertOutput(self.pu_data)
        else:
            output = self.pu_data
        return output

    def getLumiData(self):
        if self.convert_output:
            output = self.convertOutput(self.lumi_data)
        else:
            output = self.lumi_data
        return output

    def getDetectorStatus(self):
        if self.convert_output:
            output = self.convertOutput(self.det_data)
        else:
            output = self.det_data
        return output

    def getBandwidthData(self):
        if self.convert_output:
            output = self.convertOutput(self.bw_data)
        else:
            output = self.det_data
        return output

    def getSizeData(self):
        if self.convert_output:
            output = self.convertOutput(self.size_data)
        else:
            output = self.det_data
        return output

    def getBunchMap(self):
        return self.bunch_map

    def getRunsUsed(self):
        return self.runs_used

    def getNameList(self):
        return self.name_list

    def getTypeMap(self):
        return self.type_map
