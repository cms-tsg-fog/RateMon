#######################################################
# File: plotTriggerRates.py
# Author: Charlie Mueller, Andrew Wightman
# Date Created: June 19, 2015
#
# Dependencies: RateMonitor.py DBParser.py
#
#######################################################

# Imports
import getopt # For getting command line options

from DBParser_rewrite import *
from RateMonitor_rewrite import *

class MonitorController:
    def __init__(self):
        self.parser = DBParser()
        self.rate_monitor = RateMonitor()

        self.do_cron_job = False

        # Set the default state for the rate_monitor and plotter to produce plots for triggers
        self.rate_monitor.object_list = []

        self.rate_monitor.use_fills          = False
        self.rate_monitor.use_pileup         = True
        self.rate_monitor.use_lumi           = False
        self.rate_monitor.make_fits          = False
        self.rate_monitor.update_online_fits = False

        self.rate_monitor.data_parser.use_triggers = True
        self.rate_monitor.data_parser.use_streams  = False 
        self.rate_monitor.data_parser.use_datasets = False
        self.rate_monitor.data_parser.use_L1A_rate = False

        self.rate_monitor.plotter.use_fills      = False       # Determines how to color the plots
        self.rate_monitor.plotter.use_fit        = False
        self.rate_monitor.plotter.show_errors    = False
        self.rate_monitor.plotter.show_eq        = False
        self.rate_monitor.plotter.save_png       = True
        self.rate_monitor.plotter.save_root_file = False

        self.rate_monitor.plotter.file_name   = "testing_plot_rewrite.root"
        self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
        self.rate_monitor.plotter.name_X = "< PU >"
        self.rate_monitor.plotter.units_X = ""

    # Use: Parses arguments from the command line and sets class variables
    # Returns: True if parsing was successful, False if not
    def parseArgs(self):
        # Get the command line arguments
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",["fitFile=","triggerList=","saveDirectory=","Secondary",
                                                        "datasetRate","L1ARate","streamRate","streamBandwidth",
                                                        "streamSize","cronJob","updateOnlineFits","createFit","nonLinear",
                                                        "vsInstLumi","useFills"])
        except:
            print "Error getting options: command unrecognized. Exiting."
            return False

        self.rate_monitor.ops = opt
        for label,op in opt:
            if label == "--fitFile":
                fits = self.readFits(str(op))
                self.rate_monitor.plotter.setFits(fits)

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--triggerList":
                trigger_list = self.readTriggerList(str(op))
                self.rate_monitor.object_list = trigger_list
            elif label == "--saveDirectory":
                self.rate_monitor.save_dir = str(op)
            elif label == "--Secondary":
                # NEEDS TO BE IMPLEMENTED/TESTED
                xkcd = ""
            elif label == "--datasetRate":
                self.rate_monitor.data_parser.use_triggers = False
                self.rate_monitor.data_parser.use_streams  = False 
                self.rate_monitor.data_parser.use_datasets = True
                self.rate_monitor.data_parser.use_L1A_rate = False
                
                self.rate_monitor.plotter.file_name   = "Dataset_Rates.root"
                self.rate_monitor.plotter.label_Y = "dataset rate / num colliding bx [Hz]"
            elif label == "--L1ARate":
                self.rate_monitor.data_parser.use_triggers = False
                self.rate_monitor.data_parser.use_streams  = False 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = True
                
                self.rate_monitor.plotter.file_name   = "L1A_Rates.root"
                self.rate_monitor.plotter.label_Y = "L1A rate / num colliding bx [Hz]"
            elif label == "--streamRate":
                self.rate_monitor.data_parser.use_triggers = False
                self.rate_monitor.data_parser.use_streams  = True 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False
                
                self.rate_monitor.plotter.file_name   = "Stream_Rates.root"
                self.rate_monitor.plotter.label_Y = "stream rate / num colliding bx [Hz]"
            elif label == "--streamBandwidth" or label == "--streamSize":
                # NEEDS TO BE TESTED
                self.rate_monitor.data_parser.use_triggers = False
                self.rate_monitor.data_parser.use_streams  = True 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False
                
                self.rate_monitor.data_parser.normalize_bunches = False

                self.rate_monitor.plotter.file_name   = "Stream_Bandwidth.root"
                #self.rate_monitor.plotter.label_Y = "stream rate / num colliding bx [Hz]"
                self.rate_monitor.plotter.label_Y = "stream bandwidth [bytes]"
            elif label == "--streamSize":
                # NEEDS TO BE TESTED
                self.rate_monitor.data_parser.use_triggers = False
                self.rate_monitor.data_parser.use_streams  = True 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False

                self.rate_monitor.data_parser.normalize_bunches = False
                
                self.rate_monitor.plotter.file_name   = "Stream_Size.root"
                self.rate_monitor.plotter.label_Y = "stream size [bytes]"
            elif label == "--cronJob":
                # NEEDS MORE TESTING
                self.do_cron_job = True

                self.rate_monitor.use_pileup       = True
                self.rate_monitor.use_fills        = False
                self.rate_monitor.make_fits        = False

                self.rate_monitor.use_grouping = True

                self.rate_monitor.data_parser.use_triggers = True
                self.rate_monitor.data_parser.use_streams  = True
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False

                self.rate_monitor.plotter.use_fills   = False       # Determines how to color the plots

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True

                self.rate_monitor.plotter.file_name = "Cron_Job_Rates.root"
                self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
                self.rate_monitor.plotter.name_X = "< PU >"

            elif label == "--updateOnlineFits":
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.rate_monitor.update_online_fits = True

                self.rate_monitor.use_pileup = True
                self.rate_monitor.make_fits  = False

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True

                self.rate_monitor.object_list = self.readTriggerList("monitorlist_TEST.list")
            elif label == "--createFit":
                # NEEDS TO BE FINISHED
                self.rate_monitor.make_fits = True

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True

            elif label == "--nonLinear":
                # This is always true by default --> might no longer need this option (could rework it)
                xkcd = ""
            elif label == "--vsInstLumi":
                self.rate_monitor.use_pileup = False
                self.rate_monitor.use_lumi = True
            elif label == "--useFills":
                self.rate_monitor.use_fills = True
                self.rate_monitor.plotter.use_fills = True  # Might want to make this an optional switch
            else:
                print "Unimplemented option '%s'." % label
                return False

        # Process Arguments
        if len(args) > 0: # There are arguments to look at
            arg_list = []
            for item in args:
                arg_list.append(int(item))
            if self.rate_monitor.use_fills:
                self.rate_monitor.fill_list = arg_list
                self.rate_monitor.run_list = self.getRuns(arg_list)
            else:
                self.rate_monitor.fill_list = []
                self.rate_monitor.run_list = arg_list

        if len(self.rate_monitor.run_list) == 0:
            print "ERROR: No runs specified!"
            return False

        # This needs to be done after we have our run_list, otherwise we can't get the group_map
        if self.do_cron_job:
            if len(self.rate_monitor.plotter.fits.keys()) == 0:
                print "ERROR: Must specify a fit file, --fitFile=path/to/file"
                return False
            elif len(self.rate_monitor.object_list) == 0:
                print "ERROR: Must specify a monitor list, --triggerList=path/to/file"
                return False

            run_list = sorted(self.rate_monitor.run_list)

            grp_map = {}

            # Add triggers to monitor to the group map, list of all objects from .list file
            grp_map["Monitored_Triggers"] = list(self.rate_monitor.object_list)
            #grp_map["Monitored_Triggers"] = trigger_list

            # We look for triggers in all runs to ensure we don't miss any (this is unnecessary for the cron job though)
            L1_triggers = []
            for run in sorted(run_list):
                tmp_list = self.parser.getL1Triggers(run)
                for item in tmp_list:
                    if not item in L1_triggers:
                        L1_triggers.append(item)

            # Add L1 triggers to the group map, list of all L1 triggers
            grp_map["L1_Triggers"] = L1_triggers
            
            # Find which HLT paths are included in which streams
            try:
                stream_map = self.parser.getPathsInStreams(run_list[-1])    # Use the most recent run to generate the map
            except:
                print "ERROR: Failed to get stream map"
                return False

            # Add a Physics stream to the group map, list of all HLT triggers in a particular stream
            phys_streams = []
            hlt_triggers = set()
            for stream in stream_map:
                #phys_streams.append(stream)
                if stream[:7] == "Physics":
                    grp_map[stream] = stream_map[stream]
                    #hlt_triggers.add(stream_map[stream])
                    hlt_triggers = hlt_triggers | set(stream_map[stream])
                    #phys_streams.append(stream)

            # Add Streams to the group map, list of all (physics) streams
            #grp_map["Streams"] = phys_streams

            # Update the object_list to include all the things we want to plot
            self.rate_monitor.object_list += L1_triggers
            #self.rate_monitor.object_list += phys_streams
            self.rate_monitor.object_list += list(hlt_triggers)

            self.rate_monitor.group_map = grp_map

        return True

    def readFits(self,fit_file):
        fits = {} # {'trigger': fit_params}
        # Try to open the file containing the fit info
        try:
            pkl_file = open(fit_file, 'rb')
            fits = pickle.load(pkl_file)
            pkl_file.close()
            return fits
        except:
            # File failed to open
            print "Error: could not open fit file: %s" % (self.fitFile)
            return {}

    def readTriggerList(self,trigger_file):
        path = trigger_file
        f = open(path,'r')

        print "Reading trigger file: %s" % path

        output_list = []
        for line in f:
            line = line.strip() # Remove whitespace/EOL chars
            if line[0] == "#":
                continue
            output_list.append(line)
        f.close()
        return output_list

    # Gets the runs from each fill specified in arg_list
    def getRuns(self,arg_list):
        if len(arg_list) == 0:
            print "No fills specified!"
            return []

        run_list = []
        fill_map = {}   # {run_number: fill_number}
        for fill in sorted(arg_list):
            print "Getting runs from fill %d" % fill
            new_runs = self.parser.getFillRuns(fill)
            if len(new_runs) == 0:
                print "\tFill %d has no eligible runs!"
                continue
            for run in new_runs:
                fill_map[run] = fill
            run_list += new_runs
        self.rate_monitor.plotter.fill_map = fill_map
        return run_list

    # Use: Runs the rateMonitor object using parameters supplied as command line arguments
    def run(self):
        if self.parseArgs(): self.rate_monitor.run()

## ----------- End of class MonitorController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MonitorController()
    controller.run()