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
import time

from FitFinder import *
from DataParser import *
from PlotMaker import *

# --- 13 TeV constant values ---
ppInelXsec = 80000.
orbitsPerSec = 11246.

# Use: Writes a string in a fixed length margin string (pads with spaces)
def stringSegment(strng, tot):
    string = str(strng)
    if len(string) > tot:
        string  = string[:tot-3]
        string += "..."
    for x in range(0, tot-len(str(strng))):
        string += " "
    return string

class RateMonitor:
    def __init__(self):
        self.plotter     = PlotMaker()
        self.fitter      = FitFinder()
        self.data_parser = DataParser()

        self.use_fills          = False
        self.make_fits          = False
        self.use_fit_file       = False
        self.update_online_fits = False

        self.use_pileup = True      # plot <PU> vs. rate
        self.use_lumi   = False     # plot iLumi vs. rate

        self.use_stream_bandwidth = False
        self.use_stream_size      = False

        self.use_grouping = False   # Creates sub directories to group the outputs, utilizes self.group_map

        # TESTING: START #

        self.certify_mode = False

        # TESTING: END #

        self.bunch_map = {}     # {run: bunches}
        self.group_map = {}     # {'group_name': [trigger_names] }

        self.fill_list   = []   # Fills to get data from --> might remove this, as it is properly owned by DataParser
        self.run_list    = []   # Runs to get data from --> might remove this, b/c same as above
        self.object_list = []   # List of *ALL* objects to plot

        self.ops = None         # The options specified at the command line

        self.rate_mon_dir    = os.getcwd()
        self.save_dir        = os.path.join(os.getcwd(),"tmp_rate_plots")
        self.online_fits_dir = os.path.join(os.getcwd(),"Fits/2016")
        self.fit_file = None

    # The main function of RateMonitor, handles all the stitching together of the other pieces of code
    def run(self):
        if not self.setupCheck():
            print "ERROR: Bad setup"
            return
        
        print "Using runs:",self.run_list

        ### THIS IS WHERE WE GET ALL OF THE DATA ###
        self.data_parser.parseRuns(self.run_list)

        # We want to manually add the streams/datasets to the list of objects to plot
        # NOTE1: We might want to move this entire 'if' structure into DataParser.py
        # NOTE2: We will still need to 'manually' add Combined_Physics_Streams/Datasets to their respective grps
        if self.data_parser.use_streams:
            # WARNING: This blacklist is a temporary solution
            blacklist = ["PhysicsEndOfFill","PhysicsMinimumBias0","PhysicsMinimumBias1","PhysicsMinimumBias2"]
            sum_list = []
            stream_objs = set()
            for obj in self.data_parser.getNameList():
                if self.data_parser.type_map[obj] == "stream":
                    stream_objs.add(obj)
                if obj[:7] == "Physics" and not obj in blacklist:
                    sum_list.append(obj)
            # We add ALL objs of this type to the list of objects to plot
            self.object_list += list(stream_objs)
            self.data_parser.sumObjects("Combined_Physics_Streams",sum_list,"stream")
            self.object_list.append("Combined_Physics_Streams")
            if self.use_grouping:
                # We add the Streams and 'Combined_Physics_Streams' to the Streams directory here
                self.group_map["Streams"] = list(stream_objs)
                self.group_map["Streams"].append("Combined_Physics_Streams")
        
        if self.data_parser.use_datasets:
            # Same concept, but for datasets
            sum_list = []
            dataset_objs = set()
            for obj in self.data_parser.getNameList():
                if self.data_parser.type_map[obj] == "dataset":
                    dataset_objs.add(obj)
            self.object_list += list(dataset_objs)
            #self.data_parser.sumObjects("Combined_Physics_Datasets",sum_list,"dataset")
            #self.object_list.append("Combined_Physics_Datasets")
            if self.use_grouping:
                self.group_map["Datasets"] = list(dataset_objs)
                #self.group_map["Datasets"].append("Combined_Physics_Datasets")

        bunch_map = self.data_parser.getBunchMap()
        det_status = self.data_parser.getDetectorStatus()

        # Select the types of data we are going to plot
        if self.use_pileup: # plot PU vs. rate
            x_vals = self.data_parser.getPUData()
        elif self.use_lumi: # plot iLumi vs. rate
            x_vals = self.data_parser.getLumiData()
        else:               # plot LS vs. rate
            x_vals = self.data_parser.getLSData()

        if self.use_stream_size:
            y_vals = self.data_parser.getSizeData()
        elif self.use_stream_bandwidth:
            y_vals = self.data_parser.getBandwidthData()
        else:
            y_vals = self.data_parser.getRateData()

        # Now we fill plot_data with *ALL* the objects we have data for
        plot_data = {}     # {'object': { run_number:  ( [iLumi], [raw_rates], [det_status] ) } }
        for name in self.data_parser.getNameList():
            if not plot_data.has_key(name):
                plot_data[name] = {}
            for run in sorted(self.data_parser.getRunsUsed()):
                if not x_vals[name].has_key(run):    # Might want to check y_vals and det_status as well...
                    continue
                good_x, good_y = self.fitter.getGoodPoints(x_vals[name][run], y_vals[name][run])
                plot_data[name][run] = [good_x,good_y, det_status[name][run] ]

        # If no objects are specified, plot everything!
        if len(self.object_list) == 0:
            self.object_list = [x for x in self.data_parser.name_list]

        self.setupDirectory()

        ### NOW SETUP PLOTMAKER ###
        self.plotter.setPlottingData(plot_data)
        self.plotter.bunch_map = bunch_map

        # Make a fit of each object to be plotted, and save it to a .pkl file
        if self.make_fits:
            #fits = self.makeFits(plot_data,self.object_list)
            fits = self.fitter.makeFits(plot_data,self.object_list)
            self.fitter.saveFits(fits,"fit_file.pkl",self.save_dir)
            self.plotter.setFits(fits)
        elif self.update_online_fits:
            self.updateOnlineFits(plot_data)
            return  # This keeps us from having to worry about any additional output plots

        # We want fits and no fits were specified --> make some
        # NOTE: This 'if' is true only when ZERO fits exist
        if self.plotter.use_fit and len(self.plotter.fits.keys()) == 0:
            fits = self.fitter.makeFits(plot_data,plot_data.keys())
            self.plotter.setFits(fits)

        # This is after update_online_fits, so as to ensure the proper save dir is set
        self.plotter.save_dir = self.save_dir
        self.plotter.plot_dir = "png"

        counter = 0
        # Specifies how we want to organize the plots in the output directory
        if self.use_grouping:
            for grp in self.group_map:
                print "Plotting group: %s..." % grp

                grp_path = os.path.join(self.save_dir,grp)
                self.plotter.save_dir = grp_path

                objs_to_plot = set()
                for obj in self.object_list:
                    if obj in self.group_map[grp]:
                        objs_to_plot.add(obj)

                plotted_objects = self.makePlots(list(objs_to_plot))
                self.printHtml(plotted_objects,grp_path)
                counter += len(plotted_objects)
        else:
            print "Making plots..."
            plotted_objects = self.makePlots(self.object_list)
            self.printHtml(plotted_objects,self.plotter.save_dir)
            counter += len(plotted_objects)
        print "Total plot count: %d" % counter

    def setupCheck(self):
        # These two options are mutually exclusive
        if not (self.use_pileup ^ self.use_lumi): # ^ == XOR
            print "ERROR SETUP: Improper selection for self.use_pileup and self.use_lumi"
            return False

        # If we specify a fit file, we don't want to make new fits
        if self.use_fit_file and self.update_online_fits:
            print "ERROR SETUP: Fit file specified while trying updating online fits"
            return False
        elif self.use_fit_file and self.make_fits:
            print "ERROR SETUP: Fit file specified while trying to make fits"
            return False

        # Check to see if the online fits directory exists
        if self.update_online_fits and not os.path.exists(self.online_fits_dir):
            print "ERROR SETUP: Could not find fit directory"
            return False

        # We need to make sure we have the map between the plot objects and directories
        if self.use_grouping and len(self.group_map.keys()) == 0:
            print "ERROR SETUP: Grouping selected, but no group map found"
            return False

        # We don't want to accidentally remove all the contents from the current working directory
        if self.save_dir == self.rate_mon_dir:
            print "ERROR SETUP: Save directory is the same as RateMon directory"
            return False

        return True

    # Sets up the save directories
    def setupDirectory(self):
        print "Setting up directories..."

        if self.update_online_fits:
            shift_mon_dir = os.path.join(self.online_fits_dir,"Monitor_Triggers")   # $rate_mon_dir/Fits/Monitor_Triggers
            all_trg_dir = os.path.join(self.online_fits_dir,"All_Triggers")         # $rate_mon_dir/Fits/All_Triggers
            if os.path.exists(shift_mon_dir):
                shutil.rmtree(shift_mon_dir)
                print "\tRemoving existing directory: %s " % (shift_mon_dir)
            if os.path.exists(all_trg_dir):
                shutil.rmtree(all_trg_dir)
                print "\tRemoving existing directory: %s " % (all_trg_dir)
            print "\tCreating directory: %s " % (shift_mon_dir)
            os.mkdir(shift_mon_dir)
            os.chdir(shift_mon_dir)
            os.mkdir("plots")
            os.chdir(self.rate_mon_dir)
            print "\tCreating directory: %s " % (all_trg_dir)
            os.mkdir(all_trg_dir)
            os.chdir(all_trg_dir)
            os.mkdir("plots")
            os.chdir(self.rate_mon_dir)
            return

        if os.path.exists(self.save_dir):
            shutil.rmtree(self.save_dir)
            print "\tRemoving existing directory: %s " % (self.save_dir)
        os.mkdir(self.save_dir)
        os.chdir(self.save_dir)
        print "\tCreating directory: %s " % (self.save_dir)
        if self.use_grouping:
            for grp_dir in self.group_map.keys():
                os.mkdir(grp_dir)
                print "\tCreating directory: %s " % (os.path.join(self.save_dir,grp_dir))
                os.chdir(grp_dir)
                os.mkdir("png")
                os.chdir("../")
        else:
            os.mkdir("png")
        os.chdir("../")
        return

    def makePlots(self,plot_list):
        plotted_objects = []
        counter = 1
        for _object in sorted(plot_list):
            if not self.plotter.plotting_data.has_key(_object):
                print "\tWARNING: Unknown object - %s" % _object
                continue
            self.formatLabels(_object)
            if self.plotter.plotAllData(_object):
                plotted_objects.append(_object)
                counter += 1
        return plotted_objects

    # Formats the plot labels based on the type of object being plotted
    # TODO: This seems like a bit of a mess of 'if' statements --> might want to re-work it
    def formatLabels(self,_object):
        x_axis_label = ""
        y_axis_label = ""

        x_axis_var = ""
        y_axis_var = ""

        x_units = ""
        y_units = "[Hz]"

        if self.use_pileup: # plot PU vs. rate
            x_axis_var = "< PU >"
        elif self.use_lumi: # plot iLumi vs. rate
            x_axis_var = "instLumi"
        else:               # plot LS vs. rate
            x_axis_var = "LS"

        if self.data_parser.type_map[_object] == "trigger":
            if self.data_parser.correct_for_DT == True:
                y_axis_var = "pre-deadtime "
            y_axis_var += "unprescaled rate"
        elif self.data_parser.type_map[_object] == "stream":
            if self.use_stream_size or self.use_stream_bandwidth:
                y_units = "[bytes]"
            y_axis_var = "stream rate"
        elif self.data_parser.type_map[_object] == "dataset":
            y_axis_var = "dataset rate"
        elif self.data_parser.type_map[_object] == "L1A":
            y_axis_var = "L1A rate"

        x_axis_label += x_axis_var
        y_axis_label += y_axis_var

        if self.data_parser.normalize_bunches:
            y_axis_label += " / num colliding bx"

        y_axis_label += " "+y_units

        self.plotter.var_X = x_axis_var
        self.plotter.var_Y = y_axis_var
        self.plotter.label_X = x_axis_label
        self.plotter.label_Y = y_axis_label
        self.plotter.units_X = x_units
        self.plotter.units_Y = y_units

    def updateOnlineFits(self,plot_data):
        # NOTE: self.object_list, contains *ONLY* the list of triggers from 'monitorlist_COLLISIONS.list'
        mon_trg_dir = os.path.join(self.online_fits_dir,"Monitor_Triggers")
        all_trg_dir = os.path.join(self.online_fits_dir,"All_Triggers")

        all_triggers = set()
        for obj in self.data_parser.getNameList():
            all_triggers.add(obj)
        all_triggers = list(all_triggers)

        self.plotter.plot_dir = "plots"

        # Plots the monitored paths
        print "Updating monitored trigger fits..."
        self.plotter.save_dir = mon_trg_dir
        fits = self.fitter.makeFits(plot_data,self.object_list)
        self.plotter.setFits(fits)
        self.fitter.saveFits(fits,"FOG.pkl",mon_trg_dir)
        print "Making plots..."
        plotted_objects = self.makePlots(self.object_list)

        # Plots all trigger paths
        print "Updating all trigger fits..."
        self.plotter.save_dir = all_trg_dir
        fits = self.fitter.makeFits(plot_data,all_triggers)
        self.plotter.setFits(fits)
        self.fitter.saveFits(fits,"FOG.pkl",all_trg_dir)
        print "Making plots..."
        plotted_objects = self.makePlots(all_triggers)

    # NOTE1: This requires the .png file to be in the proper directory, as specified by self.group_map
    # NOTE2: This function assumes that the sub-directory where the plots are located is named 'png'
    def printHtml(self,png_list,save_dir):
        try:
            htmlFile = open(save_dir+"/index.html", "wb")
            htmlFile.write("<!DOCTYPE html>\n")
            htmlFile.write("<html>\n")
            htmlFile.write("<style>.image { float:right; margin: 5px; clear:justify; font-size: 6px; font-family: Verdana, Arial, sans-serif; text-align: center;}</style>\n")
            for path_name in sorted(png_list):  # This controls the order that the images will be displayed in
                file_name = "%s/png/%s.png" % (save_dir,path_name)
                if os.access(file_name,os.F_OK):
                    htmlFile.write("<div class=image><a href=\'png/%s.png\' target='_blank'><img width=398 height=229 border=0 src=\'png/%s.png\'></a><div style=\'width:398px\'>%s</div></div>\n" % (path_name,path_name,path_name))
            htmlFile.write("</html>\n")
            htmlFile.close
        except:
            print "Unable to write index.html file"


# --- End --- #