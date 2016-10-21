import os
import sys
import shutil
import time

#from DBParser_rewrite import *

from FitFinder_rewrite import *
from DataParser_rewrite import *
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
        #self.parser = DBParser()

        self.plotter     = PlotMaker()
        self.fitter      = FitFinder()
        self.data_parser = DataParser()

        self.use_fills          = False
        self.make_fits          = False
        self.use_fit_file       = False
        self.update_online_fits = False

        self.use_pileup = True      # plot <PU> vs. rate
        self.use_lumi   = False     # plot iLumi vs. rate

        self.use_grouping = False   # Creates sub directories to group the outputs, utilizes self.group_map

        # TESTING: START #

        self.certify_mode = False

        self.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
        self.plotter.label_Y = "dataset rate / num colliding bx [Hz]"
        self.plotter.label_Y = "L1A rate / num colliding bx [Hz]"
        self.plotter.label_Y = "stream rate / num colliding bx [Hz]"

        # TESTING: END #

        self.bunch_map = {}     # {run: bunches}
        self.group_map = {}     # {'group_name': [trigger_names] }

        self.fill_list   = []   # Fills to get data from
        self.run_list    = []   # Runs to get data from
        self.object_list = []   # List of *ALL* Objects to plot

        self.ops = None         # The options specified at the command line

        self.rate_mon_dir    = os.getcwd()
        self.save_dir        = os.path.join(os.getcwd(),"tmp_rate_plots")
        self.online_fits_dir = os.path.join(os.getcwd(),"2016/Fits")
        self.fit_file = None

    def run(self):
        if not self.setup():
            print "ERROR: Bad setup"
            return
        
        print "Using runs:",self.run_list

        ### THIS IS WHERE WE GET ALL OF THE DATA ###
        self.data_parser.parseRuns(self.run_list)

        # We want to manually add the streams/datasets to the list of objects to plot
        if self.data_parser.use_streams:
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
            self.data_parser.sumObjects("Combined_Physics_Streams",sum_list)
            self.object_list.append("Combined_Physics_Streams")
            # WARNING: This is just a crude work-around --> will want to implement this better
            if self.use_grouping:
                # We add the Streams and 'Combined_Physics_Streams' to the Streams directory here
                self.group_map["Streams"] = []
                self.group_map["Streams"] += list(stream_objs)
                self.group_map["Streams"].append("Combined_Physics_Streams")
        elif self.data_parser.use_datasets:
            sum_list = []
            dataset_objs = set()
            for obj in self.data_parser.getNameList():
                if self.data_parser.type_map[obj] == "dataset":
                    dataset_objs.add(obj)
            # We add ALL objs of this type to the list of objects to plot
            self.object_list += list(dataset_objs)
            self.data_parser.sumObjects("Combined_Physics_Datasets",sum_list)
            self.object_list.append("Combined_Physics_Datasets")
            # WARNING: This is just a crude work-around --> will want to implement this better
            if self.use_grouping:
                self.group_map["Datasets"] = []
                self.group_map["Datasets"] += list(dataset_objs)
                self.group_map["Datasets"].append("Combined_Physics_Datasets")

        # Select the types of data we are going to plot
        bunch_map = self.data_parser.getBunchMap()
        det_status = self.data_parser.getDetectorStatus()
        if self.use_pileup: # plot PU vs. rate
            x_vals = self.data_parser.getPUData()
            y_vals = self.data_parser.getRateData()
        elif self.use_lumi: # plot iLumi vs. rate
            x_vals = self.data_parser.getLumiData()
            y_vals = self.data_parser.getRateData()
        else:   # plot LS vs. rate
            x_vals = self.data_parser.getLSData()
            y_vals = self.data_parser.getRateData()

        # Now we fill plot_data with all the objects we have data for
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
            fits = self.makeFits(plot_data,self.object_list)
            self.saveFits(fits,"fit_file.pkl",self.save_dir)
            self.plotter.setFits(fits)

        # We want fits and no fits were specified --> make some
        if self.plotter.use_fit and len(self.plotter.fits.keys()) == 0:
            fits = self.makeFits(plot_data,plot_data.keys())
            self.plotter.setFits(fits)
        
        if self.update_online_fits:
            self.updateOnlineFits()

        # This is after update_online_fits, so as to ensure the proper save dir is set
        self.plotter.save_dir = self.save_dir
        counter = 0
        # Specifies how we want to organize the plots in the output directory
        if self.use_grouping:
            for grp in self.group_map:
                print "Plotting group: %s..." % grp

                # WARNING: This is just a crude work-around --> will want to implement this better
                if grp == "Streams":
                    self.plotter.label_Y = "stream rate / num colliding bx [Hz]"
                elif grp == "Datasets":
                    self.plotter.label_Y = "dataset rate / num colliding bx [Hz]"
                else:
                    self.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"

                grp_path = os.path.join(self.save_dir,grp)
                self.plotter.save_dir = grp_path

                objs_to_plot = []
                for obj in self.object_list:
                    if obj in self.group_map[grp]:
                        objs_to_plot.append(obj)

                plotted_objects = self.makePlots(set(objs_to_plot))
                self.printHtml(plotted_objects,grp_path)
                counter += len(plotted_objects)

        else:
            print "Making plots..."
            plotted_objects = self.makePlots(self.object_list)
            self.printHtml(plotted_objects,self.plotter.save_dir)
            counter += len(plotted_objects)
        print "Total plot count: %d" % counter

    def setup(self):
        if not self.setupCheck():
            return False
        #self.setupDirectory()
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

    def setupCheck(self):
        # These two options are mutually exclusive
        if self.use_pileup and self.use_lumi:
            return False

        ## Kind of useless check here, but w/e
        #if not self.data_parser.checkMode():
        #    return False

        # If we specify a fit file, we don't want to make new fits
        if self.use_fit_file and self.update_online_fits:
            return False
        elif self.use_fit_file and self.make_fits:
            return False

        # Check to see if the online fits directory exists
        if self.update_online_fits and not os.path.exists(self.online_fits_dir):
            return False

        # We need to make sure we have the map between the plot objects and directories
        if self.use_grouping and len(self.group_map.keys()) == 0:
            return False

        # We don't want to accidentally remove all the contents from the current working directory
        if self.save_dir == self.rate_mon_dir:
            return False

        return True

    def makePlots(self,plot_list):
        plotted_objects = []
        counter = 1
        for _object in plot_list:
            if not self.plotter.plotting_data.has_key(_object):
                print "\tWARNING: Unknown object, %s" % _object
                continue
            #print "\t%d: Plotting - %s" % (counter,_object)
            #time.sleep(3)
            plotted_objects.append(_object)
            self.plotter.plotAllData(_object)
            counter += 1

        return plotted_objects

    # Returns: {'trigger': fit_params}
    # data: {'trigger': { run_number:  ( [x_vals], [y_vals], [status] ) } }
    # NOTE1: This has a lot of 'if' statements, would like to see if we can remedy this
    # NOTE2: Need to figure out why the fitter is generating NaN's for the fits
    def makeFits(self,data,object_list):
        fits = {}   # {'trigger': fit_params}
        skipped_fits = []
        min_plot_pts = 10

        print "Making fits..."
        for trigger in object_list:
            if not data.has_key(trigger):
                continue
            x_fit_vals = array.array('f')
            y_fit_vals = array.array('f')
            for run in sorted(data[trigger]):
                for x,y,status in zip(data[trigger][run][0],data[trigger][run][1],data[trigger][run][2]):
                    if status: # only fit data points when ALL subsystems are IN.
                        x_fit_vals.append(x)
                        y_fit_vals.append(y)

            x_fit_vals, y_fit_vals = self.fitter.removePoints(x_fit_vals,y_fit_vals,0)   # Don't use points with 0 rate
            if len(x_fit_vals) > min_plot_pts:
                new_fit = []
                try:
                    new_fit = self.fitter.findFit(x_fit_vals,y_fit_vals,trigger)
                except KeyError:
                    print "\tUnable to create fit for: %s" % trigger
                    skipped_fits.append(trigger)
                    continue
                for i in range(len(new_fit)):
                    if i == 0:
                        continue
                    elif math.isnan(new_fit[i]):
                        new_fit[i] = 0.0
                fits[trigger] = new_fit
            else:
                skipped_fits.append(trigger)

        if len(skipped_fits) > 0:
            print "Skipped fits:"
            for item in sorted(skipped_fits):
                print "\t%s" % item

        #print "Sleeping..."
        #time.sleep(2)

        return fits

    def saveFits(self,fits,fname,fdir):
        path = os.path.join(fdir,fname)
        f = open(path, "wb")
        pickle.dump(fits,f, 2)
        f.close()
        print "Fit file saved to %s" % path

    ### UNFINISHED
    def updateOnlineFits(self,fits):
        mon_trg_dir = os.path.join(self.online_fits_dir,"Monitor_Triggers")
        all_trg_dir = os.path.join(self.online_fits_dir,"All_Triggers")

        all_triggers = [x for x in self.data_parser.name_list]

        # Plots the monitored paths
        plotted_objects = self.makePlots(self.object_list)

        # Plots all trigger paths
        plotted_objects = self.makePlots(all_triggers)


    # NOTE: This requires the .png file to be in the proper directory, as specified by self.group_map
    def printHtml(self,png_list,save_dir):
        try:
            htmlFile = open(save_dir+"/index.html", "wb")
            htmlFile.write("<!DOCTYPE html>\n")
            htmlFile.write("<html>\n")
            htmlFile.write("<style>.image { float:right; margin: 5px; clear:justify; font-size: 6px; font-family: Verdana, Arial, sans-serif; text-align: center;}</style>\n")
            for path_name in sorted(png_list):
                file_name = "%s/png/%s.png" % (save_dir,path_name)
                if os.access(file_name,os.F_OK):
                    htmlFile.write("<div class=image><a href=\'png/%s.png\' target='_blank'><img width=398 height=229 border=0 src=\'png/%s.png\'></a><div style=\'width:398px\'>%s</div></div>\n" % (path_name,path_name,path_name))
            htmlFile.write("</html>\n")
            htmlFile.close
        except:
            print "Unable to write index.html file"


# --- End --- #