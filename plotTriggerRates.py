#######################################################
# File: plotTriggerRates.py
# Author: Charlie Mueller, Nathaniel Rupprecht, Andrew Wightman
# Date Created: June 19, 2015
#
# Dependencies: RateMonitor.py, DBParser.py
#
# Data Type Key:
#    ( a, b, c, ... )       -- denotes a tuple
#    [ a, b, c, ... ]       -- denotes a list
#    { key:obj }            -- denotes a dictionary
#    { key1:{ key2:obj } }  -- denotes a nested dictionary
#####################################################################

import getopt # For getting command line options

from DBParser import *
from RateMonitor import *

class MonitorController:
    def __init__(self):
        # type: () -> None

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

        self.rate_monitor.data_parser.normalize_bunches  = True
        self.rate_monitor.data_parser.use_prescaled_rate = False
        self.rate_monitor.data_parser.use_cross_section  = False

        self.rate_monitor.data_parser.use_L1_triggers  = True
        self.rate_monitor.data_parser.use_HLT_triggers = True
        self.rate_monitor.data_parser.use_streams  = False 
        self.rate_monitor.data_parser.use_datasets = False
        self.rate_monitor.data_parser.use_L1A_rate = False

        self.rate_monitor.fitter.use_best_fit = False

        self.rate_monitor.plotter.color_by_fill  = False       # Determines how to color the plots
        self.rate_monitor.plotter.use_fit        = False
        self.rate_monitor.plotter.use_multi_fit  = False
        self.rate_monitor.plotter.show_errors    = False
        self.rate_monitor.plotter.show_eq        = False
        self.rate_monitor.plotter.save_png       = True
        self.rate_monitor.plotter.save_root_file = True

        self.rate_monitor.plotter.root_file_name   = "rate_plots.root"
        self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
        self.rate_monitor.plotter.name_X  = "< PU >"
        self.rate_monitor.plotter.units_X = ""

    # Use: Parses arguments from the command line and sets class variables
    # Returns: True if parsing was successful, False if not
    def parseArgs(self):
        # type: () -> bool

        # Get the command line arguments
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",[ 
                "fitFile=",
                "triggerList=",
                "saveDirectory=",
                "useFit=",
                "psFilter=",
                "Secondary",
                "datasetRate",
                "L1ARate",
                "streamRate",
                "streamBandwidth",
                "streamSize",
                "cronJob",
                "updateOnlineFits",
                "createFit",
                "multiFit",
                "bestFit",
                "nonLinear",
                "vsInstLumi",
                "useCrossSection",
                "useFills"
            ])

        except:
            print "Error getting options: command unrecognized. Exiting."
            return False

        self.rate_monitor.ops = opt
        for label,op in opt:
            if label == "--fitFile":
                # Specify the .pkl file to be used to extract fits from
                # TODO: Needs to be updated to account for the fact that the plotter is expecting a different input
                fits = self.readFits(str(op))
                self.rate_monitor.plotter.setFits(fits)

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--triggerList":
                # Specify the .list file that determines which triggers will be plotted
                trigger_list = self.readTriggerList(str(op))
                self.rate_monitor.object_list = trigger_list
            elif label == "--saveDirectory":
                # Specify the directory that the plots will be saved to
                # NOTE: Doesn't work with --Secondary option
                self.rate_monitor.save_dir = str(op)
            elif label == "--useFit":
                # TODO: Figure out what this does
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.rate_monitor.make_fits  = True

                self.rate_monitor.plotter.default_fit = str(op)

                self.rate_monitor.plotter.use_multi_fit = False
                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--psFilter":
                # Specify which prescale indicies to use, ex: '--psFilter=1,2,3' will only use PSI 1,2,3
                self.rate_monitor.data_parser.use_ps_mask = True
                self.rate_monitor.data_parser.psi_filter = [int(x) for x in str(op).split(',')]
            elif label == "--Secondary":
                # Set the code to produce certification plots
                # NOTE: Still need to specify --fitFile and --triggerList
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.rate_monitor.certify_mode = True

                self.rate_monitor.use_pileup = False
                self.rate_monitor.use_lumi   = False
                self.rate_monitor.use_fills  = False
                self.rate_monitor.make_fits  = False

                self.rate_monitor.data_parser.use_L1_triggers    = True
                self.rate_monitor.data_parser.use_HLT_triggers   = True
                self.rate_monitor.data_parser.normalize_bunches  = False
                self.rate_monitor.data_parser.use_prescaled_rate = False

                self.rate_monitor.data_parser.max_deadtime = 100.

                self.rate_monitor.plotter.use_fit = True
                self.rate_monitor.plotter.save_root_file = True
            elif label == "--datasetRate":
                # Make plots of dataset rates
                self.rate_monitor.data_parser.use_L1_triggers  = False
                self.rate_monitor.data_parser.use_HLT_triggers = False
                self.rate_monitor.data_parser.use_streams  = False 
                self.rate_monitor.data_parser.use_datasets = True
                self.rate_monitor.data_parser.use_L1A_rate = False
                
                self.rate_monitor.plotter.root_file_name   = "Dataset_Rates.root"
                #self.rate_monitor.plotter.label_Y = "dataset rate / num colliding bx [Hz]"
            elif label == "--L1ARate":
                # Make plots of the L1A rate
                self.rate_monitor.data_parser.use_L1_triggers  = False
                self.rate_monitor.data_parser.use_HLT_triggers = False
                self.rate_monitor.data_parser.use_streams  = False 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = True
                
                self.rate_monitor.plotter.root_file_name   = "L1A_Rates.root"
                #self.rate_monitor.plotter.label_Y = "L1A rate / num colliding bx [Hz]"
            elif label == "--streamRate":
                # Make plots of the stream rates
                self.rate_monitor.data_parser.use_L1_triggers  = False
                self.rate_monitor.data_parser.use_HLT_triggers = False
                self.rate_monitor.data_parser.use_streams  = True 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False
                
                self.rate_monitor.plotter.root_file_name   = "Stream_Rates.root"
                #self.rate_monitor.plotter.label_Y = "stream rate / num colliding bx [Hz]"
            elif label == "--streamBandwidth":
                # Make plots of the stream bandwidths
                # NEEDS TO BE TESTED
                self.rate_monitor.use_stream_bandwidth = True

                self.rate_monitor.data_parser.use_L1_triggers  = False
                self.rate_monitor.data_parser.use_HLT_triggers = False
                self.rate_monitor.data_parser.use_streams  = True 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False
                
                self.rate_monitor.data_parser.normalize_bunches = False

                self.rate_monitor.plotter.root_file_name   = "Stream_Bandwidth.root"
            elif label == "--streamSize":
                # Make plots of stream sizes
                # NEEDS TO BE TESTED
                self.rate_monitor.use_stream_size = True

                self.rate_monitor.data_parser.use_L1_triggers  = False
                self.rate_monitor.data_parser.use_HLT_triggers = False
                self.rate_monitor.data_parser.use_streams  = True 
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False

                self.rate_monitor.data_parser.normalize_bunches = False
                
                self.rate_monitor.plotter.root_file_name   = "Stream_Size.root"
            elif label == "--cronJob":
                # Set the code to produce plots for the cron jobs
                # NOTE: Still need to specify --triggerList, --saveDirectory, and --fitFile
                # NEEDS MORE TESTING
                self.do_cron_job = True

                self.rate_monitor.use_pileup = True
                self.rate_monitor.use_fills  = False
                self.rate_monitor.make_fits  = False

                self.rate_monitor.use_grouping = True

                self.rate_monitor.data_parser.use_L1_triggers  = True
                self.rate_monitor.data_parser.use_HLT_triggers = True
                self.rate_monitor.data_parser.use_streams  = True
                self.rate_monitor.data_parser.use_datasets = True
                self.rate_monitor.data_parser.use_L1A_rate = False

                self.rate_monitor.plotter.color_by_fill = False       # Determines how to color the plots

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True

                self.rate_monitor.plotter.root_file_name = "Cron_Job_Rates.root"
                #self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
                self.rate_monitor.plotter.name_X = "< PU >"
                self.rate_monitor.plotter.label_Y = "< PU >"
            elif label == "--updateOnlineFits":
                # Creates fits and saves them to the Fits directory
                # NOTE: Still need to specify --triggerList
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.rate_monitor.update_online_fits = True

                self.rate_monitor.use_pileup = True
                self.rate_monitor.make_fits  = False    # We make this false, since we need to make more then one fit file

                self.rate_monitor.data_parser.use_L1_triggers  = True
                self.rate_monitor.data_parser.use_HLT_triggers = True
                self.rate_monitor.data_parser.use_streams  = False
                self.rate_monitor.data_parser.use_datasets = False
                self.rate_monitor.data_parser.use_L1A_rate = False

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True

                self.rate_monitor.plotter.save_root_file = False

                self.rate_monitor.object_list = self.readTriggerList("monitorlist_COLLISIONS.list")
            elif label == "--createFit":
                # Specify that we should create fits
                # NEEDS TO BE FINISHED
                self.rate_monitor.make_fits = True

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--multiFit":
                # Specify that we should plot all of the fit functions on the same plot
                self.rate_monitor.make_fits = True

                self.rate_monitor.plotter.use_fit       = True
                self.rate_monitor.plotter.use_multi_fit = True
                self.rate_monitor.plotter.show_errors   = False
                self.rate_monitor.plotter.show_eq       = False
            elif label == "--bestFit":
                # Specify that only the best fit is to be used (as opposed to only the default one)
                self.rate_monitor.make_fits = True

                self.rate_monitor.fitter.use_best_fit = True

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--vsInstLumi":
                # Plot vs the instantaenous luminosity
                self.rate_monitor.use_pileup = False
                self.rate_monitor.use_lumi = True
            elif label == "--useCrossSection":
                # Plot the (rate/inst. lumi) vs. <PU>
                self.rate_monitor.data_parser.normalize_bunches = False
                self.rate_monitor.data_parser.use_cross_section = True
            elif label == "--useFills":
                # Specify that the data should fetched by fill number
                self.rate_monitor.use_fills = True
                self.rate_monitor.plotter.color_by_fill = True  # Might want to make this an optional switch
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

        # This needs to be done after we have our run_list, otherwise we can't get the run_list!
        if self.do_cron_job:
            if len(self.rate_monitor.plotter.fits.keys()) == 0:
                print "ERROR: Must specify a fit file, --fitFile=path/to/file"
                return False
            elif len(self.rate_monitor.object_list) == 0:
                print "ERROR: Must specify a monitor list, --triggerList=path/to/file"
                return False

            run_list = sorted(self.rate_monitor.run_list)

            # We check that each run used a physics menu
            #tmp_list = []
            #for run in run_list:
            #    if self.parser.getRunInfo(run):
            #        if self.parser.HLT_Key[:14] == "/cdaq/physics/":
            #            tmp_list.append(run)
            #run_list = list(tmp_list)

            if len(run_list) == 0:
                print "No valid runs. Exiting"
                return False

            grp_map = {}

            # Add triggers to monitor to the group map, list of all objects from .list file
            grp_map["Monitored_Triggers"] = list(self.rate_monitor.object_list)

            # We look for triggers in all runs to ensure we don't miss any (this should be unnecessary for the cron job though)
            L1_triggers = set()
            for run in sorted(run_list):
                tmp_list = self.parser.getL1Triggers(run)
                for item in tmp_list:
                    L1_triggers.add(item)

            # Add L1 triggers to the group map, list of all L1 triggers
            grp_map["L1_Triggers"] = list(L1_triggers)
            
            # Find which HLT paths are included in which streams
            try:
                # {'stream': ['trigger_name'] }
                #stream_map = self.parser.getPathsInStreams(run_list[-1])    # Use the most recent run to generate the map
                stream_map = {}
                for run in run_list:
                    tmp_map = self.parser.getPathsInStreams(run)
                    for stream in tmp_map:
                        if not stream_map.has_key(stream):
                            stream_map[stream] = set()
                        stream_map[stream] = stream_map[stream] | set(tmp_map[stream])
                for stream in stream_map:
                    stream_map[stream] = list(stream_map[stream])
            except:
                print "ERROR: Failed to get stream map"
                return False

            # Add a Physics stream to the group map, list of all HLT triggers in a particular stream
            hlt_triggers = set()
            for stream in stream_map:
                #if stream[:7] == "Physics":
                    grp_map[stream] = stream_map[stream]
                    for item in stream_map[stream]:
                        hlt_triggers.add(item)

            # Make a group for all HLT triggers
            grp_map["HLT_Triggers"] = list(hlt_triggers)

            # Update the object_list to include all the L1/HLT triggers in the menu
            self.rate_monitor.object_list += list(L1_triggers)
            self.rate_monitor.object_list += list(hlt_triggers)
            self.rate_monitor.group_map = grp_map

        return True

    def readFits(self,fit_file):
        # type: (str) -> Dict[str,Dict[str,List[Any]]]

        fits = {}
        # Try to open the file containing the fit info
        try:
            pkl_file = open(fit_file, 'rb')
            fits = pickle.load(pkl_file)    # {'obj': fit_params}
            pkl_file.close()
            tmp_dict = {}                   # {'obj': {'fit_type': fit_params } }
            for obj in fits:
                fit_type = fits[obj][0]
                tmp_dict[obj] = {}
                tmp_dict[obj][fit_type] = fits[obj]
            fits = tmp_dict
            return fits
        except:
            # File failed to open
            print "Error: could not open fit file: %s" % (self.fitFile)
            return {}

    def readTriggerList(self,trigger_file):
        # type: (str) -> List[str]

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
        # type: (List[int]) -> List[int]

        if len(arg_list) == 0:
            print "No fills specified!"
            return []

        run_list = []
        fill_map = {}   # {run_number: fill_number}
        for fill in sorted(arg_list):
            print "Getting runs from fill %d..." % fill
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
        # type: () -> None
        if self.parseArgs(): self.rate_monitor.run()

## ----------- End of class MonitorController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MonitorController()
    controller.run()