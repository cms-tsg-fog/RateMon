import array

from DBParser_rewrite import *

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
        self.name_list = []     # List of named objects to be plotted, e.g. triggers, datasets, streams, etc...

        self.normalize_bunches = True
        self.correct_for_DT = True
        self.convert_output = True

        self.max_dead_time = 10.

        self.use_streams  = False   # Plot stream rates
        self.use_datasets = False   # Plot dataset rates
        self.use_L1A_rate = False   # Plots the L1A rates

        self.supported_modes = ["streams","datasets","L1Arates","triggers"]
        self.mode = "triggers"

    def parseRuns(self,run_list):
        counter = 1
        for run in sorted(run_list):
            print "Processing run: %d (%d/%d)" % (run,counter,len(run_list))
            counter += 1
            bunches = self.parser.getNumberCollidingBunches(run)[0]
            lumi_info = self.parser.getLumiInfo(run)                        # [( LS,ilum,psi,phys,cms_ready ) ]
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

        # We want to manually add data for the sum of physics streams/datasets
        if self.use_streams:
            object_list = []
            for obj in self.name_list:
                if obj[:7] == "Physics":
                    object_list.append(obj)
            self.sumObjects("Combined_Physics_Streams",object_list)
        elif self.use_datasets:
            self.sumObjects("Combined_Physics_Datasets",object_list)

    # This might be excessive, should think about reworking this section
    # ------
    # We could move self.parser.getLumiInfo out of the individual member functions and then use the
    # output directly in the member functions. We then just need to ensure that none of object names
    # overlap with one another (i.e. dataset names overlap with stream names) for the rate data.
    # getTriggerData(...) and getDatasetData(...) would still need to make sure to create a key:value
    # pair for bandwidth and size, so as to ensure that the structure is identical for every getter.
    # Although the value will be different (i.e. None type vs. an array type), but this should be fine
    def getRunData(self,run,bunches,lumi_info):
        #if not self.checkMode():
        #    return None

        if self.use_streams:
            run_data = self.getStreamData(run,bunches,lumi_info)
        elif self.use_datasets:
            run_data = self.getDatasetData(run,bunches,lumi_info)
        elif self.use_L1A_rate:
            run_data = self.getL1AData(run,bunches,lumi_info)
        else:
            run_data = self.getTriggerData(run,bunches,lumi_info)

        #if self.mode == "triggers":
        #    run_data = self.getTriggerData(run,bunches,lumi_info)
        #elif self.mode == "streams":
        #    run_data = self.getStreamData(run,bunches,lumi_info)
        #elif self.mode == "datasets":
        #    run_data = self.getDatasetData(run,bunches,lumi_info)
        #elif self.mode == "L1ARates":
        #    run_data = self.getL1AData(run,bunches,lumi_info)

        return run_data

    # Returns information related to L1/HLT triggers 
    def getTriggerData(self,run,bunches,lumi_info):
        if bunches is None or bunches is 0:
            print "Unable to get bunches"
            return {}

        print "\tGetting HLT rates..."
        HLT_rates = self.parser.getRawRates(run)
        if self.correct_for_DT:
            self.correctForDeadtime(HLT_rates,run)
        print "\tGetting L1 rates..."
        L1_rates = self.parser.getL1RawRates(run,self.correct_for_DT)

        all_rates = {}  # {'trigger': {LS: (raw_rate, prescale) } }
        all_rates.update(HLT_rates)
        all_rates.update(L1_rates)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for trigger in all_rates:
            run_data[trigger] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
            bw_dict    = {}
            size_dict  = {}
            for LS,ilum,psi,phys,cms_ready in lumi_info:
                if phys and not ilum is None and all_rates[trigger].has_key(LS):
                    pu = (ilum/bunches*ppInelXsec/orbitsPerSec)
                    rate = all_rates[trigger][LS][0]

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
        if bunches is None or bunches is 0:
            print "Unable to get bunches"
            return {}

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
        if bunches is None or bunches is 0:
            print "Unable to get bunches"
            return {}

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
        if bunches is None or bunches is 0:
            print "Unable to get bunches"
            return {}

        L1A_rates = {}   # {'L1A': {LS: rate } }
        print "\tGetting L1APhysics rates..."
        L1A_rates["L1APhysics"] = self.parser.getL1APhysics(run)
        print "\tGetting L1APhysics+Lost rates..."
        L1A_rates["L1APhysics+Lost"] = self.parser.getL1APhysicsLost(run)

        run_data = {}   # {'object': {"LS": list, "rate": {...}, ... } }

        for _object in L1A_rates:
            run_data[_object] = {}
            ls_array   = array.array('f')
            rate_dict  = {}
            pu_dict    = {}
            lumi_dict  = {}
            det_dict   = {}
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

            run_data[_object]["LS"] = ls_array
            run_data[_object]["rate"] = rate_dict
            run_data[_object]["PU"] = pu_dict
            run_data[_object]["ilumi"] = lumi_dict
            run_data[_object]["status"] = det_dict
            run_data[_object]["bandwidth"] = None
            run_data[_object]["size"] = None
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
    def sumObjects(self,new_name,sum_list):
        if not set(sum_list) <= set(self.name_list):
            print "ERROR: Specified objects that aren't in the name_list"
            return
        else:
            self.name_list.append(new_name)

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
            ls_set = set(self.ls_data[sum_list[0]][run])
            for obj in sum_list:
                ls_set = ls_set & set(self.ls_data[obj][run])
            ls_array = array.array('f')
            ls_array.extend(sorted(ls_set))

            pu   = self.pu_array[obj][run][LS]
            lumi = self.lumi_data[obj][run][LS]
            det_ready  = self.det_data[obj][run][LS]

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
                self.det_data[new_name][run][LS]  = self.det_data[new_name][run][LS]

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

    def checkMode(self):
        if self.mode in self.supported_modes:
            return True
        else:
            print "ERROR: Unsupported mode specified - %s" % self.mode
            return False

    # Converts input: {'name': { run_number: { LS: raw_rates } } } --> {'name': run_number: [ data ] }
    def convertOutput(self,_input):
        output = {}
        for name in _input:
            output[name] = {}
            for run in _input[name]:
                output[name][run] = array.array('f')
                for LS in sorted(_input[name][run].keys()):
                    output[name][run].append(_input[name][run][LS])
        return output

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

    def getBunchMap(self):
        return self.bunch_map

    def getRunsUsed(self):
        return self.runs_used

    def getNameList(self):
        return self.name_list
