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
import yaml
import sys

from DBParser import *
from RateMonitor import *

class MonitorController:
    def __init__(self):

        self.ops_dict = {
            "dbConfigFile="    : None,
            "fitFile="         : None,
            "triggerList="     : None,
            "saveDirectory="   : None,
            "useFit="          : None,
            "psFilter="        : None,
            "lsVeto="          : None,
            "rootFileName="    : None,
            "exportRoot"       : None,
            "pathVeto"         : None,
            "Secondary"        : None,
            "datasetRate"      : None,
            "L1ARate"          : None,
            "streamRate"       : None,
            "streamBandwidth"  : None,
            "streamSize"       : None,
            "cronJob"          : None,
            "updateOnlineFits" : None,
            "createFit"        : None,
            "multiFit"         : None,
            "bestFit"          : None,
            #"vsInstLumi"      : None,
            "vsLS"             : None,
            #"useCrossSection" : None,
            "useFills"         : None,
            "useBunches"       : None,
            "compareFits="     : None,
            "showFitRunGroups" : None,
            "makeTitle"        : None,
            "exportJson"      : None,
        }
        self.usr_input_data_lst = None
        #self.do_cron_job = False # A default option

    # Set the default values for variables
    def setDefaults(self):

        self.do_cron_job = False

        # Set the default state for the rate_monitor and plotter to produce plots for triggers
        self.rate_monitor.object_list = []

        self.rate_monitor.plotter.set_plotter_fits = False
        self.rate_monitor.plotter.compare_fits = False

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
        self.rate_monitor.plotter.save_root_file = False
        self.rate_monitor.plotter.show_fit_runs  = False

        self.rate_monitor.plotter.root_file_name   = "rate_plots.root"
        self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
        self.rate_monitor.plotter.name_X  = "< PU >"
        self.rate_monitor.plotter.units_X = ""

        self.rate_monitor.plotter.ls_options['show_bad_ls']  = False
        self.rate_monitor.plotter.ls_options['rm_bad_beams'] = False
        self.rate_monitor.plotter.ls_options['rm_bad_det']   = False

    # Set variables based on options provided
    def setOptions(self,ops_dict,data_lst):

        # Take care of db config file first and set defualts
        self.parser = DBParser(ops_dict["dbConfigFile="])
        self.rate_monitor = RateMonitor(ops_dict["dbConfigFile="])
        self.setDefaults()

        # Loop over options and set class variables
        for op_name, op_val in ops_dict.items():
            if op_val is not None: # Should think more about this if statement and edge cases...
            #if op_val or op_val is 0:
                #print ("\tk,v:",op_name, op_val)
                if op_name == "dbConfigFile=":
                    pass # DB cfg already implemented
                elif op_name == "fitFile=":
                    fit_info = op_val
                    self.rate_monitor.plotter.set_plotter_fits = True
                    self.rate_monitor.plotter.use_fit     = True
                    self.rate_monitor.plotter.show_errors = True
                    self.rate_monitor.plotter.show_eq     = True
                elif op_name == "triggerList=":
                    trigger_list = op_val
                    self.rate_monitor.object_list = trigger_list
                    self.rate_monitor.data_parser.hlt_triggers = []
                    self.rate_monitor.data_parser.l1_triggers = []
                    for name in trigger_list:
                        if name[0:4] == "HLT_":
                            self.rate_monitor.data_parser.hlt_triggers.append(name)
                        elif name[0:3] == "L1_":
                            self.rate_monitor.data_parser.l1_triggers.append(name)
                elif op_name == "exportRoot":
                    self.rate_monitor.plotter.save_root_file = True
                elif op_name == "exportJson":
                    self.rate_monitor.exportJSON = op_val
                elif op_name == "makeTitle":
                    self.rate_monitor.plotter.styleTitle = op_val
                elif op_name == "rootFileName=":
                    self.rate_monitor.plotter.save_root_file = True
                    self.rate_monitor.root_file_name = op_val
                elif op_name == "saveDirectory=":
                   self.rate_monitor.save_dir = op_val
                elif op_name == "useFit=":
                    self.rate_monitor.plotter.default_fit = op_val
                    self.rate_monitor.make_fits  = True
                    self.rate_monitor.plotter.use_multi_fit = False
                    self.rate_monitor.plotter.use_fit     = True
                    self.rate_monitor.plotter.show_errors = True
                    self.rate_monitor.plotter.show_eq     = True
                elif op_name == "psFilter=":
                    self.rate_monitor.data_parser.psi_filter = op_val
                    self.rate_monitor.data_parser.use_ps_mask = True
                elif op_name == "lsVeto=":
                    self.rate_monitor.data_parser.ls_veto = op_val
                elif op_name == "pathVeto=":
                    self.rate_monitor.data_parser.name_veto = op_val
                elif op_name == "compareFits=":
                    data_dict = op_val
                    self.rate_monitor.fitter.data_dict = data_dict
                    self.rate_monitor.plotter.compare_fits = True
                elif op_name == "Secondary":
                    self.rate_monitor.certify_mode = True
                    self.rate_monitor.use_pileup   = False
                    self.rate_monitor.use_lumi     = False
                    self.rate_monitor.use_fills    = False
                    self.rate_monitor.use_LS       = True
                    self.rate_monitor.make_fits    = False
                    self.rate_monitor.data_parser.use_L1_triggers    = True
                    self.rate_monitor.data_parser.use_HLT_triggers   = True
                    self.rate_monitor.data_parser.normalize_bunches  = False
                    self.rate_monitor.data_parser.use_prescaled_rate = False
                    self.rate_monitor.data_parser.max_deadtime       = 100.
                    self.rate_monitor.plotter.use_fit        = True
                    self.rate_monitor.plotter.save_root_file = True
                elif op_name == "datasetRate":
                    self.rate_monitor.data_parser.use_L1_triggers  = False
                    self.rate_monitor.data_parser.use_HLT_triggers = False
                    self.rate_monitor.data_parser.use_streams  = False 
                    self.rate_monitor.data_parser.use_datasets = True
                    self.rate_monitor.data_parser.use_L1A_rate = False
                    self.rate_monitor.plotter.root_file_name   = "Dataset_Rates.root"
                elif op_name == "L1ARate":
                    self.rate_monitor.data_parser.use_L1_triggers  = False
                    self.rate_monitor.data_parser.use_HLT_triggers = False
                    self.rate_monitor.data_parser.use_streams  = False 
                    self.rate_monitor.data_parser.use_datasets = False
                    self.rate_monitor.data_parser.use_L1A_rate = True
                    self.rate_monitor.plotter.root_file_name   = "L1A_Rates.root"
                elif op_name == "streamRate":
                    self.rate_monitor.data_parser.use_L1_triggers  = False
                    self.rate_monitor.data_parser.use_HLT_triggers = False
                    self.rate_monitor.data_parser.use_streams  = True 
                    self.rate_monitor.data_parser.use_datasets = False
                    self.rate_monitor.data_parser.use_L1A_rate = False
                    self.rate_monitor.plotter.root_file_name   = "Stream_Rates.root"
                elif op_name == "streamBandwidth":
                    self.rate_monitor.use_stream_bandwidth = True
                    self.rate_monitor.data_parser.use_L1_triggers  = False
                    self.rate_monitor.data_parser.use_HLT_triggers = False
                    self.rate_monitor.data_parser.use_streams  = True 
                    self.rate_monitor.data_parser.use_datasets = False
                    self.rate_monitor.data_parser.use_L1A_rate = False
                    self.rate_monitor.data_parser.normalize_bunches = False
                    self.rate_monitor.plotter.root_file_name   = "Stream_Bandwidth.root"
                elif op_name == "streamSize":
                    self.rate_monitor.use_stream_size = True
                    self.rate_monitor.data_parser.use_L1_triggers  = False
                    self.rate_monitor.data_parser.use_HLT_triggers = False
                    self.rate_monitor.data_parser.use_streams  = True 
                    self.rate_monitor.data_parser.use_datasets = False
                    self.rate_monitor.data_parser.use_L1A_rate = False
                    self.rate_monitor.data_parser.normalize_bunches = False
                    self.rate_monitor.plotter.root_file_name   = "Stream_Size.root"
                elif op_name == "cronJob":
                    self.do_cron_job = True
                    self.rate_monitor.use_pileup   = True
                    self.rate_monitor.use_fills    = False
                    self.rate_monitor.make_fits    = False
                    self.rate_monitor.use_grouping = True
                    self.rate_monitor.data_parser.use_L1_triggers  = True
                    self.rate_monitor.data_parser.use_HLT_triggers = True
                    self.rate_monitor.data_parser.use_streams      = True
                    self.rate_monitor.data_parser.use_datasets     = True
                    self.rate_monitor.data_parser.use_L1A_rate     = True
                    self.rate_monitor.plotter.color_by_fill = False
                    self.rate_monitor.plotter.use_fit       = True
                    self.rate_monitor.plotter.show_errors   = True
                    self.rate_monitor.plotter.show_eq       = True
                    self.rate_monitor.plotter.ls_options['show_bad_ls']  = True
                    self.rate_monitor.plotter.ls_options['rm_bad_beams'] = True
                    self.rate_monitor.plotter.ls_options['rm_bad_det']   = False
                    self.rate_monitor.plotter.root_file_name = "Cron_Job_Rates.root"
                    self.rate_monitor.plotter.name_X  = "< PU >"
                    self.rate_monitor.plotter.label_Y = "< PU >"
                elif op_name == "updateOnlineFits":
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
                    self.rate_monitor.object_list = self.readTriggerList("TriggerLists/monitorlist_COLLISIONS.list")
                elif op_name == "createFit":
                    self.rate_monitor.make_fits = True
                    self.rate_monitor.plotter.use_fit     = True
                    self.rate_monitor.plotter.show_errors = True
                    self.rate_monitor.plotter.show_eq     = True
                elif op_name == "multiFit":
                    self.rate_monitor.plotter.use_fit       = True
                    self.rate_monitor.plotter.use_multi_fit = True
                    self.rate_monitor.plotter.show_errors   = False
                    self.rate_monitor.plotter.show_eq       = False
                elif op_name == "bestFit":
                    self.rate_monitor.make_fits = True
                    self.rate_monitor.fitter.use_best_fit = True
                    self.rate_monitor.plotter.use_fit     = True
                    self.rate_monitor.plotter.show_errors = True
                    self.rate_monitor.plotter.show_eq     = True
                elif op_name == "vsLS":
                    self.rate_monitor.use_pileup = False
                    self.rate_monitor.use_lumi = False
                    self.rate_monitor.use_LS = True
                elif op_name == "useFills":
                    self.rate_monitor.use_fills = True
                    self.rate_monitor.plotter.color_by_fill = True  # Might want to make this an optional switch
                elif op_name == "useBunches":
                    self.rate_monitor.data_parser.normalize_bunches = False
                elif op_name == "showFitRunGroups":
                    self.rate_monitor.plotter.show_fit_run_groups = True
                else:
                    print("Unimplemented option '%s'." % op_name)
                    return False

        # Process the runs and fills
        arg_list = self.usr_input_data_lst
        if self.rate_monitor.use_fills:
            self.rate_monitor.fill_list = arg_list
            self.rate_monitor.fitter.data_dict['user_input'] = self.getRuns(arg_list)
        else:
            self.rate_monitor.fill_list = []
            self.rate_monitor.fitter.data_dict['user_input'] = arg_list

        # Append the user specified fills or runs to the dictionary made from the compareFits text file 
        unique_runs = set()
        for data_group,runs in self.rate_monitor.fitter.data_dict.items():
                unique_runs = unique_runs.union(runs)
        self.rate_monitor.run_list = list(unique_runs)
        #print self.rate_monitor.run_list 

        if len(self.rate_monitor.run_list) == 0:
            print("ERROR: No runs specified!")
            return False

        # Could go inside fitFile option stuff?
        if self.rate_monitor.plotter.set_plotter_fits:
            self.rate_monitor.plotter.setFits(fit_info)

        # Cron job stuff:
        # This needs to be done after we have our run_list, otherwise we can't get the run_list!
        if self.do_cron_job:
            if len(list(self.rate_monitor.plotter.fits.keys())) == 0:
                print("WARNING: No fit file specified!")
                self.rate_monitor.plotter.use_fit = False

            if len(self.rate_monitor.object_list) == 0:
                print("WARNING: No trigger list specified! Plotting all triggers...")

            run_list = sorted(self.rate_monitor.run_list)

            if len(run_list) == 0:
                print("No valid runs. Exiting")
                return False

            # Find which HLT paths are included in which streams/datasets
            try:
                path_mapping = {}
                for run in run_list:
                    tmp_map = self.parser.getPathsInDatasets(run)
                    #tmp_map = self.parser.getPathsInStreams(run)
                    for group_name in tmp_map:
                        if group_name not in path_mapping:
                            path_mapping[group_name] = set()
                        path_mapping[group_name] = path_mapping[group_name] | set(tmp_map[group_name])
                for group_name in path_mapping:
                    path_mapping[group_name] = list(path_mapping[group_name])
            except:
                print("ERROR: Failed to get stream/dataset map")
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

    # Use: Parses arguments from the command line and sets class variables
    # Returns: True if parsing was successful, False if not
    def parseArgs(self):

        # Get the command line arguments
        try:
            opt, args = getopt.getopt(sys.argv[1:],"",list(self.ops_dict.keys()))
        except:
            print("Error getting options: command unrecognized. Exiting.")
            return False

        # Load the db config file
        dbConfigLoaded = False;
        for label, op in opt:
            #print(label)
            if label == "--dbConfigFile":
                dbConfigLoaded = True;
                with open(str(op), 'r') as stream:
                    try:
                        dbCfg = yaml.safe_load(stream)
                    except yaml.YAMLError as exc:
                        print("Unable to read the given YAML database configuration file. Error:", exc)
                        # Exit with error, we can't continue without connecting to the DB
                        sys.exit(1)
                #self.parser = DBParser(dbCfg)
                #self.rate_monitor = RateMonitor(dbCfg)
                self.ops_dict["dbConfigFile="] = dbCfg
            else:
                pass
        if not dbConfigLoaded:
            print("No database configuration file specified. Call the script with --dbConfigFile=dbConfigFile.yaml")
            # Exit with error, we can't continue without connecting to the DB
            sys.exit(1)

        for label,op in opt:

            if label == "--fitFile":
                # Specify the .pkl file to be used to extract fits from
                # TODO: Needs to be updated to account for the fact that the plotter is expecting a different input
                fit_info = self.readFits(str(op))
                self.ops_dict["fitFile="] = fit_info

            elif label == "--triggerList":
                # Specify the .list file that determines which triggers will be plotted
                trigger_list = self.readTriggerList(str(op))
                self.ops_dict["triggerList="] = trigger_list

            elif label == "--saveDirectory":
                # Specify the directory that the plots will be saved to
                # NOTE: Doesn't work with --Secondary option
                self.ops_dict["saveDirectory="] = str(op)

            elif label == "--useFit":
                # Use a specific fit type as the 'default' fit
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.ops_dict["useFit="] = str(op)

            elif label == "--psFilter":
                # Specify which prescale indicies to use, ex: '--psFilter=1,2,3' will only use PSI 1,2,3
                self.ops_dict["psFilter="] = [int(x) for x in str(op).split(',')]

            elif label == "--lsVeto":
                # Specifiy certain LS to veto/remove from consideration
                ls_veto = self.readLSVetoFile(str(op))
                self.ops_dict["lsVeto="] = ls_veto

            elif label == "--pathVeto":
                # Specify certain paths to veto/remove from consideration
                path_veto_list = self.readTriggerList(str(op))
                self.ops_dict["pathVeto="] = path_veto_list

            elif label == "--Secondary":
                # Set the code to produce certification plots
                # NOTE: Still need to specify --fitFile and --triggerList
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.ops_dict["Secondary"] = True

            elif label == "--datasetRate":
                # Make plots of dataset rates
                self.ops_dict["datasetRate"] = True

            elif label == "--L1ARate":
                # Make plots of the L1A rate
                self.ops_dict["L1ARate"] = True

            elif label == "--streamRate":
                # Make plots of the stream rates
                self.ops_dict["streamRate"] = True

            elif label == "--streamBandwidth":
                # Make plots of the stream bandwidths
                # NEEDS TO BE TESTED
                self.ops_dict["streamBandwidth"] = True

            elif label == "--streamSize":
                # Make plots of stream sizes
                # NEEDS TO BE TESTED
                self.ops_dict["streamSize"] = True

            elif label == "--cronJob":
                # Set the code to produce plots for the cron jobs
                # NOTE: Still need to specify --triggerList, --saveDirectory, and --fitFile
                # NEEDS MORE TESTING
                self.ops_dict["cronJob"] = True

            elif label == "--updateOnlineFits":
                # Creates fits and saves them to the Fits directory
                # NEEDS TO BE IMPLEMENTED/TESTED
                self.ops_dict["updateOnlineFits"] = True

            elif label == "--createFit":
                # Specify that we should create fits
                self.ops_dict["createFit"] = True

            elif label == "--multiFit":
                # Specify that we should plot all of the fit functions on the same plot
                self.ops_dict["multiFit"] = True

            elif label == "--bestFit":
                # Specify that only the best fit is to be used (as opposed to only the default one)
                self.ops_dict["bestFit"] = True

            #elif label == "--vsInstLumi":
            #    # Plot vs the instantaenous luminosity
            #    self.rate_monitor.use_pileup = False
            #    self.rate_monitor.use_lumi = True
            #    self.rate_monitor.use_LS = False

            elif label == "--vsLS":
                # Plot vs the LS
                self.ops_dict["vsLS"] = True

            #elif label == "--useCrossSection":
            #    # Plot the (rate/inst. lumi) vs. <PU>
            #    self.rate_monitor.data_parser.normalize_bunches = False
            #    self.rate_monitor.data_parser.use_cross_section = True

            elif label == "--useFills":
                # Specify that the data should fetched by fill number
                self.ops_dict["useFills"] = True

            elif label == "--useBunches":
                # Don't try to normalize the rates by colliding bunches
                self.ops_dict["useBunches"] = True

            elif label == "--compareFits":
                data_dict = self.readDataListTextFile(str(op))
                self.ops_dict["compareFits"] = data_dict

            elif label == "--showFitRunGroups":
                self.ops_dict["showFitRunGroups"] = True

            elif label == "--dbConfigFile":
                # Already processed in init(), this line is here just to not trigger the 'unimplemented option' fatal error below
                print("DB Configuration file loaded")

            else:
                print("Unimplemented option '%s'." % label)
                return False

        # Process Arguments
        if len(args) > 0: # There are arguments to look at
            arg_list = []
            for item in args:
                arg_list.append(int(item))
            self.usr_input_data_lst = arg_list

        print ("\nOptions dictionary:",self.ops_dict)
        print ("Data list:",self.usr_input_data_lst) 
        if not self.setOptions(self.ops_dict,self.usr_input_data_lst):
            print("\nThere was a problem  while setting options. Raising exception.\n")
            raise Exception
        self.rate_monitor.ops = opt 
        return True

    def readFits(self,fit_file):
        # type: (str) -> Dict[str,Dict[str,List[Any]]]

        fits = {}
        fit_info = {}
        # Try to open the file containing the fit info

        print("Reading fit file: %s" % (fit_file))

        try:
            pkl_file = open(fit_file, 'rb')
            #fits = pickle.load(pkl_file)    # {'obj': fit_params}
            fit_dict = pickle.load(pkl_file)
            if 'run_groups' in fit_dict:
                fit_info = fit_dict
                fits_format = 'multi_info'
            else:
                fits = fit_dict
                for trig in list(fits.keys()):
                    if type(fits[trig]) is list:
                        fits_format = 'dict_of_lists'
                    if type(fits[trig]) is dict:
                        fits_format = 'nested_dict'
            pkl_file.close()

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
            print("Error: could not open fit file: %s" % (fit_file))
            print("Info:",sys.exc_info()[0])
            return {}

    def readTriggerList(self,trigger_file):
        # type: (str) -> List[str]
        path = trigger_file
        f = open(path,'r')

        print("Reading trigger file: %s" % path)

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
            print("No fills specified!")
            return []

        run_list = []
        fill_map = {}   # {run_number: fill_number}
        for fill in sorted(arg_list):
            print("Getting runs from fill %d..." % fill)
            new_runs = self.parser.getFillRuns(fill)
            if len(new_runs) == 0:
                print("\tFill %d has no eligible runs!")
                continue
            for run in new_runs:
                fill_map[run] = fill
            run_list += new_runs
        self.rate_monitor.plotter.fill_map = fill_map
        return run_list

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

    # Use: Runs the rateMonitor object using parameters supplied as command line arguments
    def run(self):
        if self.parseArgs():
            self.rate_monitor.run()

    def runStandalone(self,**kwargs):
        # Fill in self.ops_dict to pass to setOptions
        for k,v in kwargs.items():
            if k in self.ops_dict:
                self.ops_dict[k] = v
            # FIXME: bad workaround
            elif k == "dbConfig":
                self.ops_dict["dbConfigFile="] = v
            elif k == "triggerList":
                self.ops_dict["triggerList="] = v
            elif k == "saveDirectory":
                self.ops_dict["saveDirectory="] = v
            elif k == "data_lst":
                self.usr_input_data_lst = v
            else:
                print("\nError: Unknown option",k,", raising exception.")
                raise Exception
        # print (self.usr_input_data_lst, self.ops_dict)
        self.setOptions(self.ops_dict,self.usr_input_data_lst)
        return self.rate_monitor.run()


## ----------- End of class MonitorController ------------ #

## ----------- Main -----------##
if __name__ == "__main__":
    controller = MonitorController()
    controller.run()

