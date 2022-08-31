#####################################################################
# File: RateMonitor.py
# Author: Charlie Mueller, Nathaniel Rupprecht, Andrew Wightman
# Date Created: June 16, 2015
#
# Dependencies: FitFinder.py, DataParser.py, PlotMaker.py
#
# Data Type Key:
#    ( a, b, c, ... )       -- denotes a tuple
#    [ a, b, c, ... ]       -- denotes a list
#    { key:obj }            -- denotes a dictionary
#    { key1:{ key2:obj } }  -- denotes a nested dictionary
#####################################################################

import os
import sys
import shutil
#import time
import datetime
import copy 
import json

from FitFinder import *
from DataParser import *
from PlotMaker import *
from Exceptions import *

# --- 13 TeV constant values ---
ppInelXsec = 80000.
orbitsPerSec = 11246.

# Use: Writes a string in a fixed length margin string (pads with spaces)
def stringSegment(strng, tot):
    # type: (str,int) -> str
    string = str(strng)
    if len(string) > tot:
        string  = string[:tot-3]
        string += "..."
    for x in range(0, tot-len(str(strng))):
        string += " "
    return string
    
class RateMonitor:
    def __init__(self, cfg=None):
        # type: () -> None
        self.plotter     = PlotMaker()
        self.fitter      = FitFinder()
        if cfg == None:
            self.data_parser = DataParser()
        else:
            self.data_parser = DataParser(cfg)

        self.use_fills          = False
        self.make_fits          = False
        self.use_fit_file       = False     # Currently unused outside of setupCheck
        self.update_online_fits = False
        self.plotter.compare_fits = False   # Compare fits to multiple groups of runs

        self.use_pileup = True      # plot <PU> vs. rate
        self.use_lumi   = False     # plot iLumi vs. rate
        self.use_LS     = False     # plot LS vs. rate

        self.exportJSON = False

        self.use_stream_bandwidth = False
        self.use_stream_size      = False

        self.use_grouping = False   # Creates sub directories to group the outputs, utilizes self.group_map

        # TESTING: START #
        self.certify_mode = False
        # TESTING: END #

        self.all_triggers = False

        self.group_map = {}     # {'group_name': [trigger_name] }

        self.fill_list   = []   # Fills to get data from
        self.run_list    = []   # Runs to get data from
        self.object_list = []   # List of *ALL* objects to plot, except for when using grouping

        self.ops = None         # The options specified at the command line

        self.rate_mon_dir    = os.getcwd()
        self.save_dir        = os.path.join(os.getcwd(),"tmp_rate_plots")
        self.certify_dir     = os.path.join(os.getcwd(),"tmp_certify_dir")
        self.online_fits_dir = os.path.join(os.getcwd(),"Fits")
        self.fit_file = None    # Currently Unused

    # The main function of RateMonitor, handles all the stitching together of the other pieces of code
    # NOTE1: This might be doing to many things --> break up into pieces?
    def run(self):
        # type: () -> None

        if not self.setupCheck():
            print("ERROR: Bad setup")
            return

        print("Using runs:",self.run_list)
        print("Using Prescaled rates:",self.data_parser.use_prescaled_rate)

        ### THIS IS WHERE WE GET ALL OF THE DATA ###
        self.data_parser.parseRuns(self.run_list,self.all_triggers)

        if self.data_parser.use_streams:
            # We want to manually add the streams to the list of objects to plot
            self.object_list += self.data_parser.getObjectList(obj_type="stream")
            if self.use_grouping:
                self.group_map["Streams"] = self.data_parser.getObjectList(obj_type="stream")
        
        if self.data_parser.use_datasets:
            # Same concept, but for datasets
            self.object_list += self.data_parser.getObjectList(obj_type="dataset")
            if self.use_grouping:
                self.group_map["Datasets"] = self.data_parser.getObjectList(obj_type="dataset")

        if self.data_parser.use_L1A_rate:
            # Manually add L1A rates to the list of objects to plot
            self.object_list += self.data_parser.getObjectList(obj_type="L1A")
            if self.use_grouping:
                self.group_map["L1A_Rates"] = self.data_parser.getObjectList(obj_type="L1A")

        bunch_map = self.data_parser.getBunchMap()
        det_status = self.data_parser.getDetectorStatus()
        phys_status = self.data_parser.getPhysStatus()

        # Select the types of data we are going to plot
        if self.use_pileup: # plot PU vs. rate
            x_vals = self.data_parser.getPUData()
        elif self.use_lumi: # plot iLumi vs. rate
            x_vals = self.data_parser.getLumiData()
        elif self.use_LS:   # plot LS vs. rate
            x_vals = self.data_parser.getLSData()

        if self.use_stream_size:
            y_vals = self.data_parser.getSizeData()
        elif self.use_stream_bandwidth:
            y_vals = self.data_parser.getBandwidthData()
        else:
            y_vals = self.data_parser.getRateData()

        # Now we fill plot_data with *ALL* the objects we have data for
        
        #plot_data = {}     # {'object_name': { run_number:  ( [x_vals], [y_vals], [det_status] , [phys_status] ) } }
        #for name in self.data_parser.getNameList():
        #    if not plot_data.has_key(name):
        #        plot_data[name] = {}
        #    for run in sorted(self.data_parser.getRunsUsed()):
        #        if not x_vals[name].has_key(run):
        #            continue
        #        plot_data[name][run] = [x_vals[name][run],y_vals[name][run],det_status[name][run],phys_status[name][run]]

        plot_data = self.getData(x_vals,y_vals,det_status,phys_status,self.fitter.data_dict['user_input'])

        # If no objects are specified, plot everything or raise error:
        if len(self.object_list) == 0:
            if self.all_triggers:
                self.object_list = [x for x in self.data_parser.name_list]
            else:
                raise NoValidTriggersError

        self.setupDirectory()

        ### NOW SETUP PLOTMAKER ###
        self.plotter.setPlottingData(plot_data)
        self.plotter.bunch_map = bunch_map

        normalization = 1
        if self.data_parser.normalize_bunches:
            max_key = max(iter(bunch_map.keys()), key=(lambda key: bunch_map[key]))
            normalization = bunch_map[max_key]
        print("Fit Normalization: %d" % normalization)

        # Make a fit of each object to be plotted, and save it to a .pkl file
        if self.make_fits:
        
            fit_info = {
                'run_groups': copy.deepcopy(self.fitter.data_dict),
                'triggers': {}
            }
            for group,runs in self.fitter.data_dict.items():
                data = self.getData(x_vals,y_vals,det_status,phys_status,runs)
                data_fits = self.fitter.makeFits(data,self.object_list,normalization,group)
                fit_info['triggers'] = self.fitter.mergeFits(fit_info['triggers'],data_fits)
                print(group,runs)

            self.plotter.setFits(fit_info)
            self.fitter.saveFits(self.plotter.fit_info,"fit_file.pkl",self.save_dir)
            #self.fitter.saveFits(fit_info,"fit_file.pkl",self.save_dir)
            #self.plotter.setFits(fit_info)

        elif self.update_online_fits:
            self.updateOnlineFits(plot_data,normalization)
            return  # This keeps us from having to worry about any additional output plots
        elif self.certify_mode:
            self.certifyRuns(plot_data)
            return  # Same as above

        # This is after update_online_fits, so as to ensure the proper save dir is set
        self.plotter.save_dir = self.save_dir
        self.plotter.plot_dir = "png"

        counter = 0
        # Specifies how we want to organize the plots in the output directory
        if self.use_grouping:
            print("Making Plots...")

            # Create plots for *EVERYTHING* we've queried for
            objs_to_plot = set()
            for obj in self.object_list:
                objs_to_plot.add(obj)
            plotted_objects = self.makePlots(list(objs_to_plot))
            counter += len(plotted_objects["plots"])

            # Create index.html files to display specific groups of plots
            # Also fill a dict that we can dump to a json with all the category and plot names
            plotted_obj_dict = {}
            for grp in self.group_map:
                plotted_obj_dict[grp] = []
                grp_path = os.path.join(self.save_dir,grp)
                grp_objs = set()
                for obj in plotted_objects["plots"]:
                    if obj in self.group_map[grp]:
                        grp_objs.add(obj)
                        plotted_obj_dict[grp].append(obj)
                self.printHtml(png_list=grp_objs,save_dir=self.save_dir,index_dir=grp_path,png_dir="..")

            # Save the dictionary of plotted objects into a json file
            plotted_obj_json = os.path.join(self.save_dir, "plotted_objects.json")
            with open (plotted_obj_json,"w") as out_json_file:
                json.dump(plotted_obj_dict, out_json_file, indent=4)

            #for grp in self.group_map:
            #    print "Plotting group: %s..." % grp
            #    grp_path = os.path.join(self.save_dir,grp)
            #    self.plotter.save_dir = grp_path
            #    objs_to_plot = set()
            #    for obj in self.object_list:
            #        # Get the the plot objs associated with this group
            #        if obj in self.group_map[grp]:
            #            objs_to_plot.add(obj)
            #    plotted_objects = self.makePlots(list(objs_to_plot))
            #    self.printHtml(plotted_objects,grp_path)
            #    counter += len(plotted_objects)
        else:
            plotted_objects = self.makePlots(self.object_list)
            self.printHtml(png_list=plotted_objects["plots"].keys(),save_dir=self.save_dir,index_dir=self.save_dir,png_dir=".")
            counter += len(plotted_objects["plots"])
        print("Total plot count: %d" % counter)
        return plotted_objects

    # Makes some basic checks to ensure that the specified options don't create conflicting problems
    def setupCheck(self):
        # type: () -> bool

        ## These two options are mutually exclusive
        #if not (self.use_pileup ^ self.use_lumi): # ^ == XOR
        #    print "ERROR SETUP: Improper selection for self.use_pileup and self.use_lumi"
        #    return False

        # Have to specify triggers to plot data for
        if self.object_list == [] and not self.all_triggers and self.data_parser.use_L1_triggers and self.data_parser.use_HLT_triggers:
            print("ERROR SETUP: A trigger list must be specified.")
            return False

        # Cannot specify some triggers and all triggers at the same time
        if self.object_list != [] and self.all_triggers:
            print("ERROR SETUP: Cannot specify specific triggers when using allTriggers option.")
            return False

        # We can't specify two different x_axis at the same time
        if self.use_pileup and self.use_lumi:
            print("ERROR SETUP: Improper selection for self.use_pileup (" + self.use_pileup + ") and self.use_lumi (" + self.use_lumi  + "). They should never be both enabled")
            return False

        # If we specify a fit file, we don't want to make new fits
        if self.use_fit_file and self.update_online_fits:
            print("ERROR SETUP: Fit file specified while trying updating online fits")
            return False
        elif self.use_fit_file and self.make_fits:
            print("ERROR SETUP: Fit file specified while trying to make fits")
            return False

        # Check to see if the online fits directory exists
        if self.update_online_fits and not os.path.exists(self.online_fits_dir):
            print("ERROR SETUP: Could not find fit directory (" + self.online_fits_dir + ")")
            return False

        # We need to make sure we have the map between the plot objects and directories
        if self.use_grouping and len(list(self.group_map.keys())) == 0:
            print("ERROR SETUP: Grouping selected, but no group map found")
            return False

        # We don't want to accidentally remove all the contents from the current working directory
        if self.save_dir == self.rate_mon_dir:
            print("ERROR SETUP: Save directory (" + self.save_dir + ") is the same as RateMon directory (" + self.rate_mon_dir + ")")
            return False

        # Certify mode doesn't create any fits, so we shouldn't be updating any existing fits
        if self.update_online_fits + self.certify_mode > 1:
            print("ERROR SETUP: Can't update online fits and user certify mode at the same time")
            return False

        # In certify_mode we need to specify pre-made fits to use
        if self.certify_mode and len(list(self.plotter.fits.keys())) == 0:
            print("ERROR SETUP: No fits were found while in certify mode")
            return False

        ## We are configured to only create/display the default fit, so only generate one fit
        #if self.make_fits and not self.fitter.use_best_fit and not self.plotter.use_multi_fit:
        #    print "WARNING: Only creating the default fit, %s" % self.plotter.default_fit
        #    self.fitter.fits_to_try = [self.plotter.default_fit]

        return True

    # Sets up the save directories, will setup the directories based on CLI options
    def setupDirectory(self):
        # type: () -> None
        print("Setting up directories...")

        if self.update_online_fits:
            if self.all_triggers:
                trg_dir = os.path.join(self.online_fits_dir,"All_Triggers")
            else:
                trg_dir = os.path.join(self.online_fits_dir,"Monitor_Triggers")
            if os.path.exists(trg_dir):
                shutil.rmtree(trg_dir)
                print("\tRemoving existing directory: %s " % (trg_dir))
            print("\tCreating directory: %s " % (trg_dir))
            os.mkdir(trg_dir)
            os.chdir(trg_dir)
            os.mkdir("plots")
            os.chdir(self.rate_mon_dir)
            return
        elif self.certify_mode:
            # Ex: Certification_1runs_2016-11-02_13_27
            dir_str = "Certification_%druns_%s" % (len(self.run_list),datetime.datetime.now().strftime("%Y-%m-%d_%H_%M"))
            #dir_str = "Certification_%druns" % (len(self.run_list))
            self.certify_dir = os.path.join(self.rate_mon_dir,dir_str)
            if os.path.exists(self.certify_dir):
                shutil.rmtree(self.certify_dir)
                print("\tRemoving existing directory: %s " % (self.certify_dir))
            print("\tCreating directory: %s " % (self.certify_dir))
            os.mkdir(self.certify_dir)
            os.chdir(self.certify_dir)
            for run in self.run_list:
                run_str = "run%d" % run
                run_dir = os.path.join(self.certify_dir,run_str)
                print("\tCreating directory: %s " % (run_dir))
                os.mkdir(run_dir)
                os.chdir(run_dir)
                os.mkdir("png")
                os.chdir(self.certify_dir)
            return
        else:
            if os.path.exists(self.save_dir):
                shutil.rmtree(self.save_dir)
                print("\tRemoving existing directory: %s " % (self.save_dir))
            os.makedirs(self.save_dir)
            os.chdir(self.save_dir)
            print("\tCreating directory: %s " % (self.save_dir))
            os.mkdir("png")
            if self.use_grouping:
                for grp_dir in list(self.group_map.keys()):
                    os.mkdir(grp_dir)
                    print("\tCreating directory: %s " % (os.path.join(self.save_dir,grp_dir)))
            os.chdir(self.rate_mon_dir)
            return

    # Stiching function that interfaces with the plotter object
    def makePlots(self,plot_list):
        # type: (List[str]) -> List[str]
        if not self.use_grouping:
            print("Making plots...")

        plotted_objects = []
        counter = 1
        prog_counter = 0
        n_skipped = 0
        n_invalid_trg = 0
        n_not_enough_good_data = 0
        rundata = {}
        # self.plotter.plotting_data.keys()
        rundata["plots"] = {}
        for _object in sorted(plot_list):

            if prog_counter % max(1,math.floor(len(plot_list)/10.)) == 0:
                print("\tProgress: %.0f%% (%d/%d)" % (100.*prog_counter/len(plot_list),prog_counter,len(plot_list)))
            prog_counter += 1
            if _object not in self.plotter.plotting_data:
                # No valid data points could be found for _object in any of the runs
                print("\tWARNING: Unknown object - %s" % _object)
                rundata["plots"][_object] = "NODATA"
                n_skipped += 1
                n_invalid_trg += 1
                continue
            self.formatLabels(_object)
            
            # Produces the plot for the selected trigger, returns the raw data
            triggerplotdata = self.plotter.plotAllData(_object)

            if triggerplotdata:
                plotted_objects.append(_object)
                counter += 1
                rundata["plots"][_object] = triggerplotdata

                # Include the fill in the json if querying by fill
                if self.use_fills:
                    rundata["plots"][_object]["fills"] = self.fill_list

                if self.exportJSON:
                    filepath = os.path.join(self.save_dir, _object+".json")
                    with open(filepath, "w") as out_file:
                        json.dump(rundata, out_file)
                    print("Exported JSON:", filepath)

            else:
                n_skipped += 1
                n_not_enough_good_data += 1
                continue

        # Not sure what to do in the case where skip some due to invalid trigger, others due to not enough data..
        # right now just raising noDataError in that case since seems more general
        if n_skipped == len(plot_list):
            if n_invalid_trg == len(plot_list):
                raise NoValidTriggersError
            else:
                runs = list(self.plotter.plotting_data[_object].keys()) # Need runs if raising NoDataError
                raise NoDataError(runs)

        if _object in self.plotter.plotting_data:

            rundata["x_axis"] = self.plotter.var_X_simple
            rundata["y_axis"] = self.plotter.var_Y_simple

        return rundata

    # Formats the plot labels based on the type of object being plotted
    # TODO: Might want to move this (along with makePlots() into PlotMaker.py),
    #       would require specifying a type_map within the plotter object
    def formatLabels(self,_object):
        # type: (str) -> None

        x_axis_label = ""
        y_axis_label = ""

        x_axis_var = ""
        y_axis_var = ""

        x_units = ""
        y_units = "[Hz]"

        if self.use_pileup: # plot PU vs. rate
            x_axis_var = "< PU >"
            x_axis_var_simple = "PU"
        elif self.use_lumi: # plot iLumi vs. rate
            x_axis_var = "instLumi"
            x_axis_var_simple = "il"
        else:               # plot LS vs. rate
            x_axis_var = "lumisection"
            x_axis_var_simple = "ls"

        if self.data_parser.type_map[_object] == "trigger":
            if self.data_parser.correct_for_DT == True:
                y_axis_var = "pre-deadtime "
                y_axis_var_simple = "pre-dt-"

            if self.data_parser.use_prescaled_rate:
                y_axis_var += "prescaled rate"
                y_axis_var_simple += "prescaled-rate"
            else:
                y_axis_var += "unprescaled rate"
                y_axis_var_simple += "unprescaled-rate"
        elif self.data_parser.type_map[_object] == "stream":
            if self.use_stream_size or self.use_stream_bandwidth:
                y_units = "[bytes]"
            y_axis_var = "stream rate"
            y_axis_var_simple = "stream-rate"
        elif self.data_parser.type_map[_object] == "dataset":
            y_axis_var = "dataset rate"
            y_axis_var_simple = "dataset-rate"
        elif self.data_parser.type_map[_object] == "L1A":
            y_axis_var = "L1A rate"
            y_axis_var_simple = "L1A-rate"

        x_axis_label += x_axis_var
        y_axis_label += y_axis_var

        # Format the y_axis_label denominator
        if self.data_parser.normalize_bunches and self.data_parser.use_cross_section:
            y_axis_label += " / (num bx*iLumi)"
        elif self.data_parser.normalize_bunches:
            y_axis_label += " / num colliding bx"
        elif self.data_parser.use_cross_section:
            y_axis_label += " / iLumi"

        y_axis_label += " " + y_units

        self.plotter.var_X = x_axis_var
        self.plotter.var_Y = y_axis_var
        self.plotter.var_X_simple = x_axis_var_simple
        self.plotter.var_Y_simple = y_axis_var_simple
        self.plotter.label_X = x_axis_label
        self.plotter.label_Y = y_axis_label
        self.plotter.units_X = x_units
        self.plotter.units_Y = y_units

    def updateOnlineFits(self,plot_data,normalization):
        # type: (Dict[str,Dict[int,object]]) -> None

        # NOTE: self.object_list, contains *ONLY* the list of triggers from 'monitorlist_COLLISIONS.list'
        if self.all_triggers:
            trg_dir = os.path.join(self.online_fits_dir,"All_Triggers")
        else:
            trg_dir = os.path.join(self.online_fits_dir,"Monitor_Triggers")

        self.plotter.plot_dir = "plots"

        print("Updating trigger fits...")
        print("Total Triggers: %d" % (len(self.object_list)))
        self.plotter.save_dir = trg_dir
        #fits = self.fitter.makeFits(plot_data,self.object_list,normalization)
        #self.plotter.setFits(fits)
        #self.fitter.saveFits(fits,"FOG.pkl",mon_trg_dir)
        #fit_info = self.fitter.makeFits(plot_data,self.object_list,normalization)
        fit_info = {
            'run_groups': copy.deepcopy(self.fitter.data_dict),
            'triggers': self.fitter.makeFits(plot_data,list(plot_data.keys()),normalization)
        }
        self.plotter.setFits(fit_info)
        self.fitter.saveFits(self.plotter.fit_info,"FOG.pkl",trg_dir)
        plotted_objects = self.makePlots(self.object_list)

        command_line_str  = "Results produced with:\n"
        command_line_str += "python plotTriggerRates.py "
        for tup in self.ops:
            #if tup[0].find('--updateOnlineFits') > -1:
            #    # never record when we update online fits
            #    continue
            #elif tup[0].find('--lsVeto') > -1:
            #    continue
            if len(tup[1]) == 0:
                command_line_str += "%s " % (tup[0])
            else:
                command_line_str += "%s=%s " % (tup[0],tup[1])
        for run in self.run_list:
            command_line_str += "%d " % (run)
        command_line_str +="\n"
        
        command_line_file_name = os.path.join(trg_dir,"command_line.txt")
        log_file_mon = open(command_line_file_name, "w")
        log_file_mon.write(command_line_str)
        log_file_mon.close()

    def certifyRuns(self,plot_data):
        # type: (Dict[str,Dict[int,object]]) -> None

        #self.plotter.save_dir = self.certify_dir
        #self.plotter.root_file_name = "CertificationSumaries.root"

        # {'name': {run: [ (LS,pred,err) ] } }


        lumi_info = self.data_parser.getLumiInfo()
        sorted_run_list = sorted(self.run_list)

        log_file_name = "CertificationSummary_run"+str(sorted_run_list[0])+"_run"+str(sorted_run_list[-1])+".txt"
        log_file = open(self.certify_dir+"/"+log_file_name,'w')

        for run in self.run_list:
            log_file.write("Run Number: %s\n" % (run))

            self.plotter.save_dir = self.certify_dir
            self.plotter.root_file_name = "CertificationSummaries.root"

            #pred_data = self.getPredictionData(run)     # {'trg name': { 'group name': [ (LS,pred,err) ] } }
            pred_data = self.getPredictionData(run)     # {'trg name': { 'group name': { 'fit_type': [ (LS,pred,err) ] } } }

            ## Check if there are multiple fit types to plot
            #multi_fit_types = False
            #for trg in pred_data:
            #    for grp in pred_data[trg]:
            #        if len(pred_data[trg][grp].keys()) > 1:
            #            multi_fit_types = True

            for group in self.plotter.run_groups:
                ## We have multiple fit types per trg: separate histograms and summary text file by fit type
                #if self.plotter.use_multi_fit and multi_fit_types:
                #    for fit_type in self.fitter.fits_to_try:
                #        log_file.write("\n")
                #        log_file.write("Group: %s\n" % (group))
                #        log_file.write("Fit type: %s\n" % (fit_type))
                #        self.plotter.makeCertifySummary(run,pred_data,log_file,group,multi_fit_types,fit_type)
                # We have only one fit type per trg: do not separate histograms and summary text file by fit type
                log_file.write("\n")
                log_file.write("Group: %s\n" % (group))
                self.plotter.makeCertifySummary(run,pred_data,log_file,group)

            print("Making certification plots for run %d..." % run)
            run_dir = os.path.join(self.certify_dir,"run%d" % run)
            self.plotter.save_dir = run_dir
            self.plotter.plot_dir = "png"
            self.plotter.root_file_name = "HLT_LS_vs_rawRate_Fitted_Run%d_CERTIFICATION.root" % run
            plotted_objects = []
            for obj in self.object_list:
                if not obj in self.data_parser.name_list:
                    print("Skipping missing trigger: %s" % (obj))
                    continue
                self.formatLabels(obj)
                if self.plotter.makeCertifyPlot(obj,run,lumi_info[run]):
                    print("Plotting %s..." % obj)
                    plotted_objects.append(obj)
            self.printHtml(png_list=plotted_objects,save_dir=run_dir,index_dir=self.save_dir,png_dir=".")

    # We create a prediction dictionary on a per run basis, which covers all triggers in that run
    # TODO: Should move this to DataParser.py
    def getPredictionData(self,run):
        # UNFINISHED
        # We need to disable converting the output
        prev_state = self.data_parser.convert_output
        self.data_parser.convert_output = False

        #lumi_info = self.data_parser.parser.getLumiInfo(runNumber=run)  # {run_number: [ (LS,ilum,psi,phys,cms_ready) ] }
        lumi_info = self.data_parser.getLumiInfo()  # {run_number: [ (LS,ilum,psi,phys,cms_ready) ] }
        ls_data = self.data_parser.getLSData()      # {'name': { run_number: [ LS ] } }
        pu_data = self.data_parser.getPUData()      # {'name': { run_number: { LS: PU } } }
        bunch_map = self.data_parser.getBunchMap()  # {run_number: bunches}

        plotter_sigmas = self.plotter.sigmas

        #pred_dict = {}  # {'name': [ (LS,pred,err) ] }
        #pred_dict = {}  # {'trg name': {'group name': [ (LS,pred,err) ] } }
        pred_dict = {}  # {'trg name': {'group name': { 'fit_type': [ (LS,pred,err) ] } } }


        for obj in self.plotter.fits:
            if obj not in pu_data:
                continue
            elif run not in pu_data[obj]:
                continue

            pred_dict[obj] = {}

            for group in self.plotter.fits[obj]:

                pred_dict[obj][group] = {}

                # Find the best fit
                best_fit_type,best_fit = self.fitter.getBestFit(self.plotter.fits[obj][group])

                lsVals = []
                puVals = []
                for LS, ilum, psi, phys, cms_ready in lumi_info[run]:
                    if not ilum is None and phys:
                        if LS not in pu_data[obj][run]:
                            continue
                        lsVals.append(LS)
                        puVals.append(pu_data[obj][run][LS])
                lumisecs,predictions,ls_error,pred_error = self.fitter.getPredictionPoints(best_fit,lsVals,puVals,bunch_map[run],0)
                pred_dict[obj][group][best_fit_type] = list(zip(lumisecs,predictions,pred_error))




                ##############################################################################################

        # --- 13 TeV constant values ---
        #ppInelXsec = 80000.
        #orbitsPerSec = 11246.

            ## Initialize our point arrays
            #lumisecs    = array.array('f')
            #predictions = array.array('f')
            #ls_error    = array.array('f')
            #pred_error  = array.array('f')

                ## Unpack values
                #fit_type, X0, X1, X2, X3, sigma, meanraw, X0err, X1err, X2err, X3err, ChiSqr = best_fit

                ## Create our point arrays
                #for LS, ilum, psi, phys, cms_ready in lumi_info[run]:
                #    if not ilum is None and phys:
                #        if not pu_data[obj][run].has_key(LS):
                #            continue
                #        lumisecs.append(LS)
                #        #pu = (ilum * ppInelXsec) / ( self.bunch_map[run] * orbitsPerSec )
                #        pu = pu_data[obj][run][LS]
                #        # Either we have an exponential fit, or a polynomial fit
                #        if fit_type == "exp":
                #            rr = bunch_map[run] * (X0 + X1*math.exp(X2+X3*pu))
                #        elif fit_type == "sinh":
                #            #val = 0
                #            #val += math.pow(X0*pu,11)/39916800.
                #            #val += math.pow(X0*pu,9)/362880.
                #            #val += math.pow(X0*pu,7)/5040.
                #            #val += math.pow(X0*pu,5)/120.
                #            #val += math.pow(X0*pu,3)/6.
                #            #val += math.pow(X0*pu,1)
                #            #val = X1*val + X2
                #            #rr = bunch_map[run] * (val)
                #            rr = bunch_map[run] * (X1*math.sinh(X0*pu) + X2) # ???
                #        else:
                #            rr = bunch_map[run] * (X0 + pu*X1 + (pu**2)*X2 + (pu**3)*X3)
                #        if rr < 0: rr = 0 # Make sure prediction is non negative
                #        predictions.append(rr)
                #        ls_error.append(0)
                #        pred_error.append(bunch_map[run]*plotter_sigmas*sigma)

                ##############################################################################################


        # Revert back to the previous convert_output setting
        self.data_parser.convert_output = prev_state
        return pred_dict

    ## NOTE1: This requires the .png file to be in the proper directory, as specified by self.group_map
    ## NOTE2: This function assumes that the sub-directory where the plots are located is named 'png'
    ##def printHtml(self,png_list,save_dir):
    ##    # type: (List[str],str) -> None
    ##    try:
    ##        htmlFile = open(save_dir+"/index.html", "wb")
    ##        htmlFile.write("<!DOCTYPE html>\n")
    ##        htmlFile.write("<html>\n")
    ##        htmlFile.write("<style>.image { float:right; margin: 5px; clear:justify; font-size: 6px; font-family: Verdana, Arial, sans-serif; text-align: center;}</style>\n")
    ##        for path_name in sorted(png_list):  # This controls the order that the images will be displayed in
    ##            file_name = "%s/png/%s.png" % (save_dir,path_name)
    ##            if os.access(file_name,os.F_OK):
    ##                htmlFile.write("<div class=image><a href=\'png/%s.png\' target='_blank'><img width=398 height=229 border=0 src=\'png/%s.png\'></a><div style=\'width:398px\'>%s</div></div>\n" % (path_name,path_name,path_name))
    ##        htmlFile.write("</html>\n")
    ##        htmlFile.close
    ##    except:
    ##        print "Unable to write index.html file"

    # For this we want to be able to specify where the images are located, relative to the index.html file
    def printHtml(self,png_list,save_dir,index_dir,png_dir="."):
        # save_dir:  The full path to the save directory
        # index_dir: The full path to the index.html file
        # png_dir:   The relative path from the index.html file to the png_dir
        try:
            htmlFile = open(index_dir+"/index.html","w")
            htmlFile.write("<!DOCTYPE html>\n")
            htmlFile.write("<html>\n")
            htmlFile.write("<style>.image { float:left; margin: 5px; clear:justify; font-size: 6px; font-family: Verdana, Arial, sans-serif; text-align: center;}</style>\n")
            for path_name in sorted(png_list):  # This controls the order that the images will be displayed in
                file_name = "%s/png/%s.png" % (save_dir,path_name)
                if os.access(file_name,os.F_OK):
                    rel_dir = os.path.join(png_dir,"png/%s.png" % path_name)
                    html_str = ""
                    html_str += "<div class=image>"
                    html_str += "<a href=\'%s\' target='_blank'>" % rel_dir
                    html_str += "<img width=398 height=229 border=0 src=\'%s\'>" % rel_dir
                    html_str += "</a><div style=\'width:398px\'>%s</div></div>\n" % path_name
                    htmlFile.write(html_str)
            htmlFile.write("</html>\n")
        except:
            print("Unable to write index.html file")
    
    # Returns {'object_name': { run_number:  ( [x_vals], [y_vals], [det_status] , [phys_status] ) } }
    def getData(self,x_vals,y_vals,det_status,phys_status,runs=[]):
        data = {}
        for name in self.data_parser.getNameList():
                if name not in data:
                        data[name] = {}
                for run in sorted(self.data_parser.getRunsUsed()):
                        if run not in x_vals[name]:
                                continue
                        if len(runs) > 0 and run not in runs:
                                continue
                        data[name][run] = [x_vals[name][run],y_vals[name][run],det_status[name][run],phys_status[name][run]]
        return data


        
# --- End --- #

