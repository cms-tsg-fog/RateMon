from DBParser import *

class RateObject:
    def __init__(self):
        self.parser = DBParser()    # Could make this an inherited class
        self.name = ""              # Name of the objects

        # The Data
        self.ls = {}                # { run_number: [LS] }
        self.rates = {}             # { run_number: [raw_rate] }
        self.pu_data   = {}         # { run_number: [PU] }
        self.lumi_data = {}         # { run_number: [iLumi] }
        self.det_data  = {}         # { run_number: [detector_ready] }

        self.run_list  = []         # Runs used to produce the data
        self.fill_list = []         # Fills used to produce the runs/data
        self.fill_map  = {}         # Maps a run to a fill - {run_number: fill }
        self.bunch_map = {}         # Maps nBunches to a particular run - {run_number: bunches}

        self.useFills = False

    def setInput(self,src_list):
        if self.useFills:
            self.fill_map = src_list
            self.run_list = src_list.keys()
            for key in src_list:
                self.fill_list.append(src_list[key])
        else:
            self.run_list = src_list

    def setFillMap(self,_map):
        self.fill_map = _map
        self.run_list = _map.keys()

    def setBunchMap(self,_map):
        self.bunch_map = _map

    # We don't want to call DBParser() for every object from the menu --> would need to re-design DBParser() or it would be WAY to slow
    #def makeFillMap(self):
    #    if not self.useFills:
    #        print "ERROR: Input must be set to use fills"
    #        return {}
    #    for fill in self.fill_list:
    #        tmp_list = self.parser.getFillRuns(fill)
    #        self.run_list += tmp_list
    #        for run in tmp_list:
    #            self.fill_map[run] = fill
    #def makeBunchMap(self):
    #    for run in self.run_list:
    #        bunch_map[run] = self.parser.getNumberCollidingBunches(run)[0]

class TriggerObject(RateObject):
    def __init__(self):
        self.datasets = []      # Datasets this trigger is apart of
        self.streams = []       # Streams this trigger is apart of

class StreamObject(RateObject):
    def __init__(self):
        self.triggers = []      # Triggers that are contained in this Stream
        self.datasets = []      # Datasets that are contained in this Stream

class DatasetObject(RateObject):
    def __init__(self):
        self.triggers = []      # Triggers that are contained in this dataset
        self.streams = []       # Streams this dataset is apart of