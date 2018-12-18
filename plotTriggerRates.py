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
import json
import sys

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

        #self.set_plotter_fits = False
        self.rate_monitor.plotter.set_plotter_fits = False

        self.rate_monitor.compare_fits = False

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
        self.rate_monitor.plotter.show_fit_runs  = False

        self.rate_monitor.plotter.root_file_name   = "rate_plots.root"
        self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
        self.rate_monitor.plotter.name_X  = "< PU >"
        self.rate_monitor.plotter.units_X = ""

        self.rate_monitor.plotter.ls_options['show_bad_ls']  = False
        self.rate_monitor.plotter.ls_options['rm_bad_beams'] = False
        self.rate_monitor.plotter.ls_options['rm_bad_det']   = False

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
                "lsVeto=",
                "pathVeto=",
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
                "vsLS",
                "useCrossSection",
                "useFills",
                "useBunches",
                "compareFits=",
                "showFitRuns"
            ])

        except:
            print "Error getting options: command unrecognized. Exiting."
            return False

        self.rate_monitor.ops = opt
        for label,op in opt:
            if label == "--fitFile":
                # Specify the .pkl file to be used to extract fits from
                # TODO: Needs to be updated to account for the fact that the plotter is expecting a different input
                #fits = self.readFits(str(op))
                #self.rate_monitor.plotter.setFits(fits)
                fit_info = self.readFits(str(op))

                #self.set_plotter_fits = True
                self.rate_monitor.plotter.set_plotter_fits = True

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--triggerList":
                # Specify the .list file that determines which triggers will be plotted
                trigger_list = self.readTriggerList(str(op))
                self.rate_monitor.object_list = trigger_list
                self.rate_monitor.data_parser.hlt_triggers = []
                self.rate_monitor.data_parser.l1_triggers = []
                for name in trigger_list:
                    if name[0:4] == "HLT_":
                        self.rate_monitor.data_parser.hlt_triggers.append(name)
                    elif name[0:3] == "L1_":
                        self.rate_monitor.data_parser.l1_triggers.append(name)
            elif label == "--saveDirectory":
                # Specify the directory that the plots will be saved to
                # NOTE: Doesn't work with --Secondary option
                self.rate_monitor.save_dir = str(op)
            elif label == "--useFit":
                # Use a specific fit type as the 'default' fit
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
            elif label == "--lsVeto":
                # Specifiy certain LS to veto/remove from consideration
                ls_veto = self.readLSVetoFile(str(op))
                self.rate_monitor.data_parser.ls_veto = ls_veto
            elif label == "--pathVeto":
                # Specify certain paths to veto/remove from consideration
                path_veto_list = self.readTriggerList(str(op))
                self.rate_monitor.data_parser.name_veto = path_veto_list
            elif label == "--Secondary":
                # Set the code to produce certification plots
                # NOTE: Still need to specify --fitFile and --triggerList
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.rate_monitor.certify_mode = True

                self.rate_monitor.use_pileup = False
                self.rate_monitor.use_lumi   = False
                self.rate_monitor.use_fills  = False
                self.rate_monitor.use_LS     = True
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
                #self.rate_monitor.data_parser.use_L1A_rate = False
                self.rate_monitor.data_parser.use_L1A_rate = True

                self.rate_monitor.plotter.color_by_fill = False

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True

                self.rate_monitor.plotter.ls_options['show_bad_ls']  = True
                self.rate_monitor.plotter.ls_options['rm_bad_beams'] = True
                self.rate_monitor.plotter.ls_options['rm_bad_det']   = False

                self.rate_monitor.plotter.root_file_name = "Cron_Job_Rates.root"
                #self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
                self.rate_monitor.plotter.name_X = "< PU >"
                self.rate_monitor.plotter.label_Y = "< PU >"
            elif label == "--updateOnlineFits":
                # Creates fits and saves them to the Fits directory
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
                self.rate_monitor.make_fits = True

                self.rate_monitor.plotter.use_fit     = True
                self.rate_monitor.plotter.show_errors = True
                self.rate_monitor.plotter.show_eq     = True
            elif label == "--multiFit":
                # Specify that we should plot all of the fit functions on the same plot
                #self.rate_monitor.make_fits = True

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
                self.rate_monitor.use_LS = False
            elif label == "--vsLS":
                # Plot vs the LS
                self.rate_monitor.use_pileup = False
                self.rate_monitor.use_lumi = False
                self.rate_monitor.use_LS = True
            elif label == "--useCrossSection":
                # Plot the (rate/inst. lumi) vs. <PU>
                self.rate_monitor.data_parser.normalize_bunches = False
                self.rate_monitor.data_parser.use_cross_section = True
            elif label == "--useFills":
                # Specify that the data should fetched by fill number
                self.rate_monitor.use_fills = True
                self.rate_monitor.plotter.color_by_fill = True  # Might want to make this an optional switch
            elif label == "--useBunches":
                # Don't try to normalize the rates by colliding bunches
                self.rate_monitor.data_parser.normalize_bunches = False
            elif label == "--compareFits":
                data_dict = self.readDataListTextFile(str(op))
                #print 'data_dict: ' , data_dict
                self.rate_monitor.fitter.data_dict = data_dict
                self.rate_monitor.compare_fits = True
            elif label == "--showFitRuns":
                self.rate_monitor.plotter.show_fit_runs = True
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
                #self.rate_monitor.run_list = self.getRuns(arg_list)
                self.rate_monitor.fitter.data_dict['user_input'] = self.getRuns(arg_list)
            else:
                self.rate_monitor.fill_list = []
                #self.rate_monitor.run_list = arg_list
                self.rate_monitor.fitter.data_dict['user_input'] = arg_list
        
        # Append the user specified fills or runs to the dictionary made from the compareFits text file 
        
        unique_runs = set()
        for data_group,runs in self.rate_monitor.fitter.data_dict.iteritems():
                unique_runs = unique_runs.union(runs)
        self.rate_monitor.run_list = list(unique_runs)
        #print self.rate_monitor.run_list 

        if len(self.rate_monitor.run_list) == 0:
            print "ERROR: No runs specified!"
            return False

        #if self.set_plotter_fits:
        if self.rate_monitor.plotter.set_plotter_fits:
            #self.rate_monitor.plotter.setFits(fits)
            self.rate_monitor.plotter.setFits(fit_info)

        # This needs to be done after we have our run_list, otherwise we can't get the run_list!
        if self.do_cron_job:
            if len(self.rate_monitor.plotter.fits.keys()) == 0:
                print "WARNING: No fit file specified!"
                self.rate_monitor.plotter.use_fit = False

            if len(self.rate_monitor.object_list) == 0:
                print "WARNING: No trigger list specified! Plotting all triggers..."

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

            ## Find which HLT paths are included in which streams
            #try:
            #    # {'stream': ['trigger_name'] }
            #    #stream_map = self.parser.getPathsInStreams(run_list[-1])    # Use the most recent run to generate the map
            #    stream_map = {}
            #    for run in run_list:
            #        tmp_map = self.parser.getPathsInStreams(run)
            #        for stream in tmp_map:
            #            if not stream_map.has_key(stream):
            #                stream_map[stream] = set()
            #            stream_map[stream] = stream_map[stream] | set(tmp_map[stream])
            #    for stream in stream_map:
            #        stream_map[stream] = list(stream_map[stream])
            #except:
            #    print "ERROR: Failed to get stream map"
            #    return False
            ## Find which HLT paths are included in which datasets
            #try:
            #    dataset_map = {}
            #    for run in run_list:
            #        tmp_map = self.parser.getPathsInDatasets(run)
            #        for dataset in tmp_map:
            #            if not dataset_map.has_key(dataset):
            #                dataset_map[dataset] = set()
            #            dataset_map[dataset] = dataset_map[dataset] | set(tmp_map[dataset])
            #    for dataset in dataset_map:
            #        dataset_map[dataset] = list(dataset_map[dataset])
            #except:
            #    print "ERROR: Failed to get dataset map"
            #    return False

            # Find which HLT paths are included in which streams/datasets
            try:
                path_mapping = {}
                for run in run_list:
                    tmp_map = self.parser.getPathsInDatasets(run)
                    #tmp_map = self.parser.getPathsInStreams(run)
                    for group_name in tmp_map:
                        if not path_mapping.has_key(group_name):
                            path_mapping[group_name] = set()
                        path_mapping[group_name] = path_mapping[group_name] | set(tmp_map[group_name])
                for group_name in path_mapping:
                    path_mapping[group_name] = list(path_mapping[group_name])
            except:
                print "ERROR: Failed to get stream/dataset map"
                return False

            group_map = {}

            # Add specific triggers to monitor to the group map, list of all objects from .list file
            group_map["Monitored_Triggers"] = list(self.rate_monitor.object_list)

            # We look for triggers in all runs to ensure we don't miss any (this should be unnecessary for the cron job though)
            L1_triggers = set()
            for run in sorted(run_list):
                tmp_list = self.parser.getL1Triggers(run)
                for item in tmp_list:
                    L1_triggers.add(item)

            # Add L1 triggers to the group map, list of all L1 triggers
            group_map["L1_Triggers"] = list(L1_triggers)
            self.rate_monitor.data_parser.l1_triggers = list(L1_triggers)

            # Add HLT triggers to the group map
            hlt_triggers = set()
            for path_owner in path_mapping:
                group_map[path_owner] = path_mapping[path_owner]
                for item in path_mapping[path_owner]:
                    hlt_triggers.add(item)

            # Make a group for all HLT triggers
            group_map["HLT_Triggers"] = list(hlt_triggers)

            self.rate_monitor.data_parser.hlt_triggers = list(hlt_triggers)

            # Update the object_list to include all the L1/HLT triggers in the menu
            self.rate_monitor.object_list += list(L1_triggers)
            self.rate_monitor.object_list += list(hlt_triggers)
            self.rate_monitor.group_map = group_map

        return True

    def readFits(self,fit_file):
        # type: (str) -> Dict[str,Dict[str,List[Any]]]

        fits = {}
        fit_info = {}
        # Try to open the file containing the fit info

        print "Reading fit file: %s" % (fit_file)

        try:
            pkl_file = open(fit_file, 'rb')
            #fits = pickle.load(pkl_file)    # {'obj': fit_params}
            fit_dict = pickle.load(pkl_file)
            if fit_dict.has_key('fit_runs'):
                fit_info = fit_dict
                fits_format = 'multi_info'
            else:
                fits = fit_dict
                for trig in fits.keys():
                    if type(fits[trig]) is list:
                        fits_format = 'dict_of_lists'
                    if type(fits[trig]) is dict:
                        fits_format = 'nested_dict'
            pkl_file.close()
            print 'fit type !!! ' , fits_format

            if fits_format == 'dict_of_lists':
                    tmp_dict = {}                   # {'obj': {'fit_type': fit_params } }
                    for obj in fits:
                        if fits[obj] is None:
                            # We were unable to generate a proper fit for this trigger
                            continue
                        fit_type = fits[obj][0]
                        tmp_dict[obj] = {}
                        tmp_dict[obj][fit_type] = fits[obj]
                    fits = tmp_dict
                    fit_info['fit_runs'] = {}
                    fit_info['triggers'] = fits
                    return fit_info

            if fits_format == 'nested_dict':
                    fit_info['fit_runs'] = {}
                    fit_info['triggers'] = fits
                    return fit_info
 
            if fits_format == 'multi_info':
                    return fit_info

        except:
            # File failed to open
            print "Error: could not open fit file: %s" % (fit_file)
            print "Info:",sys.exc_info()[0]
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

    # Creates a filter for the DataParser to exlude specific LS
    def readLSVetoFile(self,ls_veto_file):
        json_file = open(ls_veto_file)
        json_data = json.load(json_file)
        ls_veto = {}
        for run_number in json_data:
            ls_veto[int(run_number)] = []
            for ls_low,ls_high in json_data[run_number]:
                ls_veto[int(run_number)] += [x for x in range(ls_low,ls_high+1)]
        return ls_veto

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

    # Read text file of lists of runs 
    #def readDataListTextFile(self,datalist_file):
    #    path = datalist_file
    #    f = open(path,'r')
    #    dict1 = {}
    #    i=1
    #    for line in f:
    #        key = '%idata' % (i)
    #        data1 = []
    #        for run in line.split():
    #            data1.append(int(run))
    #            dict1[key] = data1
    #        i=i+1
    #    if self.rate_monitor.use_fills == True:
    #        for key in dict1:
    #            dict1[key] = self.getRuns(dict1[key])
    #    f.close()
    #    return dict1

    def readDataListTextFile(self,datalist_file):
        path = datalist_file
        f = open(path,'r')
        dict1 = {}
        i=1
        for line in f:
            if len(line.split(':')) == 2:
                data1 = []
                key = ''
                n = 0
                for word in line.split():
                    if n  == 0:
                        for character in word:
                            if character is not ':':
                                key = key + character
                    else:
                        data1.append(int(word))
                        dict1[key] = data1
                    n = n + 1
            if len(line.split(':')) == 1:
                key = '%idata' % (i)
                data1 = []
                for run in line.split():
                    data1.append(int(run))
                    dict1[key] = data1
                i=i+1
        if self.rate_monitor.use_fills == True:
            for key in dict1:
                dict1[key] = self.getRuns(dict1[key])
        f.close()
        return dict1


## ----------- End of class MonitorController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MonitorController()
    controller.run()

