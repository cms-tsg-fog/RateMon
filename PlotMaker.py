#####################################################################
# File: PlotMaker.py
# Author: Andrew Wightman
# Date Created: September 15, 2016
#
# Dependencies: FitFinder
#
# Data Type Key:
#    ( a, b, c, ... )        -- denotes a tuple
#    [ a, b, c, ... ]        -- denotes a list
#    { key:obj }             -- denotes a dictionary
#    { key1: { key2:obj } }  -- denotes a nested dictionary
#####################################################################
import math
import array
import ROOT

from ROOT import TLatex

from FitFinder import *


# Generates ROOT based plots
class PlotMaker:
    def __init__(self):
        # Set ROOT properties
        gROOT.SetBatch(True)            # Use batch mode so plots are not spit out in X11 as we make them
        gStyle.SetPadRightMargin(0.2)   # Set the canvas right margin so the legend can be bigger
        ROOT.gErrorIgnoreLevel = 7000   # Suppress info message from TCanvas.Print

        self.plotting_data = {}     #    {'trigger': { run_number:  ( [x_vals], [y_vals], [status] ) } }

        #self.fits = {}              # {'trigger': fit_params }
        self.fits = {}              # {'trigger': { 'fit_type': fit_params } }
        self.bunch_map = {}         # {run_number:  bunches }
        self.fill_map = {}          # {run_number: fill_number }

        self.fitFinder = FitFinder()

        self.sigmas = 3.0
        self.color_list = [4,6,8,7,9,419,46,20,28,862,874,38,32,40,41,5,3]  # List of colors that we can use for graphing
        self.fit_color_list = [2,1,3,5]                                     # List of colors to use for the fits
        self.fill_count = 0
        self.min_plot_pts = 10

        self.label_X = "X-axis"
        self.label_Y = "Y-axis"
        self.var_X = "X variable"
        self.var_Y = "Y variable"
        #self.name_X = "name"
        self.units_X = "[unit]"
        self.units_Y = "[unit]"

        self.file_name = "a.root"
        self.save_dir = "."
        self.plot_dir = "png"

        self.default_fit = "quad"

        self.use_fills = False
        self.use_fit = False
        self.use_multi_fit = False
        self.show_errors = False
        self.show_eq = False
        self.save_png = False
        self.save_root_file = False

    def setPlottingData(self,data):
        self.plotting_data = data

    def setFits(self,fits):
        if self.use_multi_fit:
            # We want to plot all the fits
            self.fits = fits
        else:
            # We select only a single fit_type to plot
            for trigger in fits:
                if len(fits[trigger].keys()) > 1:
                    # This is kind of an edge case, but I would like to find a better solution for selecting from multiple fits
                    try:
                        self.fits[trigger] = {}
                        self.fits[trigger][self.default_fit] = fits[trigger][self.default_fit]
                    except KeyError:
                        print "WARNING: %s doesn't have the default fit type, %s. Skipping this fit" % self.default_fit
                        continue
                else:
                    fit_type = fits[trigger].keys()[0]
                    self.fits[trigger] = {}
                    self.fits[trigger][fit_type] = fits[trigger][fit_type]

    # Gets the list of runs
    def getRunList(self):
        src_list = []
        for trigger in self.plotting_data:
            for item in self.plotting_data[trigger].keys():
                if not item in src_list:
                    src_list.append(item)
        return src_list 

    # Maps certain colors to certain runs
    def getColorMap(self):
        color_map = {}  # {run_number: color}

        run_list = self.getRunList()
        
        if len(self.fill_map.keys()) == 0 and self.use_fills:
            print "WARNING: Unable to find fill map, will color by runs instead"
            self.use_fills = False

        old_fill = -1
        counter = 0
        for run in sorted(run_list):    # Ensures that runs will be grouped by fill_number
            if self.use_fills:
                new_fill = self.fill_map[run]
                if new_fill != old_fill:    # Only increment based on fill_numbers
                    old_fill = new_fill
                    counter += 1
                    self.fill_count = counter
            else:
                counter += 1
            color_map[run] = self.color_list[(counter - 1) % len(self.color_list)]
        return color_map

    def getFuncStr(self,fit_params):
        if fit_params[0] == "exp":          # Exponential
             plotFuncStr = "%.5f + %.5f*exp( %.5f+%.5f*x )" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])
             funcStr = "%.5f + %.5f*exp( %.5f+%.5f*x )" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])
        elif fit_params[0] == "linear":     # Linear
            plotFuncStr = "%.15f + x*%.15f" % (fit_params[1], fit_params[2])
            funcStr = "%.5f + x*%.5f" % (fit_params[1], fit_params[2])                   
        else:                               # Polynomial
            plotFuncStr = "%.15f+x*(%.15f+ x*(%.15f+x*%.15f))" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])
            funcStr = "%.5f+x*(%.5f+ x*(%.5f+x*%.5f))" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])

        return plotFuncStr,funcStr

    # plots all the data for a given trigger
    def plotAllData(self,trigger):
        # paramlist == fits
        missing_fit = False
        if not self.plotting_data.has_key(trigger):
            print "\tERROR: Trigger not found in plotting data, %s" % trigger
            return False
        else:
            data = self.plotting_data[trigger]  # { run_number: ( [x_vals], [y_vals], [status] ) }

        run_count = 0
        num_pts = 0
        for run in data:
            #num_pts += len(data[run][0])
            x_pts,y_pts = self.fitFinder.removePoints(data[run][0],data[run][1])
            x_pts,y_pts = self.fitFinder.getGoodPoints(x_pts,y_pts)
            num_pts += len(y_pts)
            if len(data[run][0]) > 0:
                run_count += 1

        if num_pts < self.min_plot_pts:
            #print "\tSkipping %s: Not enough plot points" % trigger
            return False

        if self.use_fit and not self.fits.has_key(trigger):
            # No fit found for this plot
            print "\tWARNING: Missing fit - %s" % trigger
            missing_fit = True

        # Find max and min values
        maximumRR = array.array('f')
        maximumVals = array.array('f')
        minimumVals = array.array('f')

        xVals = array.array('f')
        yVals = array.array('f')

        # Find minima and maxima so we create graphs of the right size
        for run in data:
            xVals, yVals = self.fitFinder.getGoodPoints(data[run][0], data[run][1]) 
            if len(xVals) > 0:
                maximumRR.append(max(yVals))
                maximumVals.append(max(xVals))
                minimumVals.append(min(xVals))

        if len(maximumRR) > 0: max_yaxis_value = max(maximumRR)
        else: return

        if len(maximumVals) > 0:
            max_xaxis_val = max(maximumVals)
            min_xaxis_val = min(minimumVals)
        else: return

        if max_xaxis_val == 0 or max_yaxis_value == 0: return

        canvas = TCanvas(self.var_X, self.var_Y, 1000, 600)
        canvas.SetName(trigger+"_"+self.var_X+"_vs_"+self.var_Y)

        if self.use_fit and not missing_fit:
            plot_func_str = {}
            func_str = {}
            fit_func = {}
            fit_mse = {}
            for fit_type in self.fits[trigger]:
                fit_params = self.fits[trigger][fit_type]

                plot_func_str[fit_type],func_str[fit_type] = self.getFuncStr(fit_params)
                fit_func[fit_type] = TF1("Fit_"+trigger, plot_func_str[fit_type], 0., 1.1*max_xaxis_val)
                fit_mse[fit_type] = fit_params[5]

        graphList = []
        color_map = self.getColorMap()

        leg_entries = 0
        if self.use_fills:
            leg_entries += self.fill_count
        else:
            leg_entries += run_count

        if self.use_fit and not missing_fit:
            if self.use_multi_fit:
                leg_entries += len(self.fits[trigger].keys())
            else:
                leg_entries += 1

        legend = self.getLegend(num_entries=leg_entries)

        old_fill = -1
        counter = 0
        for run in sorted(data):
            data[run][0],data[run][1] = self.fitFinder.getGoodPoints(data[run][0],data[run][1])
            
            num_LS = len(data[run][0])
            if num_LS == 0: continue
            graphList.append(TGraph(num_LS, data[run][0], data[run][1]))

            graphColor = color_map[run]

            graphList[-1].SetMarkerStyle(7)
            graphList[-1].SetMarkerSize(1.0)
            graphList[-1].SetLineColor(graphColor)
            graphList[-1].SetFillColor(graphColor)
            graphList[-1].SetMarkerColor(graphColor)
            graphList[-1].SetLineWidth(2)
            #graphList[-1].GetXaxis().SetTitle(self.name_X+" "+self.units_X)
            graphList[-1].GetXaxis().SetTitle(self.label_X)
            graphList[-1].GetXaxis().SetLimits(0, 1.1*max_xaxis_val)
            graphList[-1].GetYaxis().SetTitle(self.label_Y)
            graphList[-1].GetYaxis().SetTitleOffset(1.2)
            graphList[-1].SetMinimum(0)
            graphList[-1].SetMaximum(1.2*max_yaxis_value)
            graphList[-1].SetTitle(trigger)

            if counter == 0: graphList[-1].Draw("AP")
            else: graphList[-1].Draw("P")
            canvas.Update()

            if self.bunch_map.has_key(run):
                bunches = str(self.bunch_map[run])
            else:
                bunches = "-"

            legendStr = ""
            if self.use_fills:
                new_fill = self.fill_map[run]
                if new_fill != old_fill:
                    old_fill = new_fill
                    legendStr = "%s (%s b)" % (new_fill,bunches)
                    legend.AddEntry(graphList[-1],legendStr,"f")
            else:
                legendStr = "%s (%s b)" % (run,bunches)
                legend.AddEntry(graphList[-1],legendStr,"f")
            counter += 1

        if self.use_fit and not missing_fit: # Display the fit function
            color_counter = 0
            for fit_type in sorted(self.fits[trigger]):
                legend.AddEntry(fit_func[fit_type], "%s Fit ( %s \sigma )" % (fit_type,self.sigmas))
                fit_func[fit_type].SetLineColor(self.fit_color_list[color_counter % len(self.fit_color_list)])
                fit_func[fit_type].Draw("same")
                color_counter += 1
            
                if self.show_errors and not self.use_multi_fit: # Display the error band
                    fit_error_band = self.getErrorGraph(fit_func[fit_type],fit_mse[fit_type])
                    fit_error_band.Draw("3")

                if self.show_eq and not self.use_multi_fit: # Display the fit equation
                    func_leg = TLegend(.146, .71, .47, .769)
                    func_leg.SetHeader("f(x) = " + func_str[fit_type])
                    func_leg.SetFillColor(0)
                    func_leg.Draw()
                    canvas.Update()

        # draw text
        latex = TLatex()
        latex.SetNDC()
        latex.SetTextColor(1)
        latex.SetTextAlign(11)
        latex.SetTextFont(62)
        latex.SetTextSize(0.05)
        latex.DrawLatex(0.15, 0.84, "CMS")
        latex.SetTextSize(0.035)
        latex.SetTextFont(52)
        latex.DrawLatex(0.15, 0.80, "Rate Monitoring")

        canvas.SetGridx(1);
        canvas.SetGridy(1);
        canvas.Update()

        # Draw Legend
        if self.use_fills:
            legend.SetHeader("%s fills (%s runs):" % (self.fill_count,run_count))
        else:
            legend.SetHeader("%s runs:" % (run_count) )
        legend.SetFillColor(0)
        legend.Draw() 
        canvas.Update()

        if self.save_root_file:
            self.saveRootFile(trigger,canvas)

        if self.save_png:
            self.savePlot(trigger,canvas)

        return True

    # Create legend
    def getLegend(self,num_entries):
        left = 0.81; right = 0.98; top = 0.9; scaleFactor = 0.05; minimum = 0.1
        bottom = max([top-scaleFactor*(num_entries+1), minimum])
        legend = TLegend(left,top,right,bottom)

        return legend

    # Returns a TGraphErrors for the given fit function
    def getErrorGraph(self,fit_func,fit_mse):
        x_val = array.array('f')
        y_val = array.array('f')
        ye_val = array.array('f')
        xe_val = array.array('f')
        x_min = fit_func.GetXmin()
        x_max = fit_func.GetXmax()
        x_range = x_max - x_min
        n_points = 1000
        step_size = x_range/n_points

        x_coord = x_min
        while x_coord <= x_max:
            x_val.append(x_coord)
            y_val.append(fit_func.Eval(x_coord))
            ye_val.append(self.sigmas*fit_mse)
            xe_val.append(0)
            x_coord += step_size

        err_graph = TGraphErrors(len(x_val),x_val,y_val,xe_val,ye_val)
        err_graph.SetFillColor(2)
        err_graph.SetFillStyle(3003)

        return err_graph

    def getPredictionGraph(self):
        # This is for Certify Mode
        xkcd = ""

    def getCertifyPlots(self):
        # Maybe
        xkcd = ""

    def saveRootFile(self,name,canvas):
        # Update root file
        path = self.save_dir + "/" + self.file_name
        file = TFile(path,"UPDATE")
        canvas.Modified()
        canvas.Write()

    def savePlot(self,name,canvas):
        canvas.Print(self.save_dir + "/" + self.plot_dir + "/" + name + ".png", "png")