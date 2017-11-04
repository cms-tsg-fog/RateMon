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

from ROOT import TLatex, TH1D, TLine

from FitFinder import *

# Generates ROOT based plots
class PlotMaker:
    def __init__(self):
        # Set ROOT properties
        gROOT.SetBatch(True)            # Use batch mode so plots are not spit out in X11 as we make them
        gStyle.SetPadRightMargin(0.2)   # Set the canvas right margin so the legend can be bigger
        ROOT.gErrorIgnoreLevel = 7000   # Suppress info message from TCanvas.Print

        self.plotting_data = {}     #    {'trigger': { run_number:  ( [x_vals], [y_vals], [det_status], [phys_status] ) } }

        self.fits = {}              # {'trigger': { 'fit_type': fit_params } }
        self.bunch_map = {}         # {run_number:  bunches }
        self.fill_map = {}          # {run_number: fill_number }

        self.fitFinder = FitFinder()

        self.sigmas = 3.0
        # Fix: [8,9,10,12]
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

        self.root_file_name = "a.root"
        self.save_dir = "."
        self.plot_dir = "png"

        self.default_fit = "quad"

        self.color_by_fill = False
        self.use_fit = False
        self.use_multi_fit = False
        self.show_errors = False
        self.show_eq = False
        self.save_png = False
        self.save_root_file = False

        self.ls_options = {
            'show_bad_ls':  True,       # Flag to display the removed LS (in a separate color)
            'rm_bad_beams': True,       # Remove LS which did not have stable beams
            'rm_bad_det':   False,      # Remove LS which had 'bad' sub-systems
            'bad_marker_style': 21,     # Marker style for the bad LS
            'bad_marker_size':  0.6,    # Marker size for the bad LS
            'bad_marker_color': 1,      # Marker color for the bad LS
        }

    def setPlottingData(self,data):
        self.plotting_data = data

    # Sets the fits to be used in the plot making
    # TODO: Instead of just using a default_fit, could instead make use of self.fitFinder.getBestFit()
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
                        print "WARNING: %s doesn't have the default fit type, %s. Skipping this fit" % (trigger,self.default_fit)
                        continue
                else:
                    # If only 1 fit is available use it
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
        
        if len(self.fill_map.keys()) == 0 and self.color_by_fill:
            print "WARNING: Unable to find fill map, will color by runs instead"
            self.color_by_fill = False

        old_fill = -1
        counter = 0
        for run in sorted(run_list):    # Ensures that runs will be grouped by fill_number
            if self.color_by_fill:
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
             plotFuncStr = "%.15f + %.5f*exp( %.15f+%.15f*x )" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])
             funcStr = "%.5f + %.5f*exp( %.5f+%.5f*x )" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])
        elif fit_params[0] == "linear":     # Linear
            plotFuncStr = "%.15f + x*%.15f" % (fit_params[1], fit_params[2])
            funcStr = "%.5f + x*%.5f" % (fit_params[1], fit_params[2])
        elif fit_params[0] == "sinh":
            plotFuncStr = "%.15f + %.15f*sinh(%.15f*x)" % (fit_params[3], fit_params[2], fit_params[1])
            funcStr = "%.5f + %.5f*sinh(%.5f*x)" % (fit_params[3], fit_params[2], fit_params[1])
        else:                               # Polynomial
            plotFuncStr = "%.15f+x*(%.15f+ x*(%.15f+x*%.15f))" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])
            funcStr = "%.5f+x*(%.5f+ x*(%.5f+x*%.5f))" % (fit_params[1], fit_params[2], fit_params[3], fit_params[4])

        return plotFuncStr,funcStr

    # Merges all the points from all the runs in the trigger data
    def combinePoints(self,data):
        xVals = array.array('f')
        yVals = array.array('f')
        for run in data:
            xVals += data[run][0]
            yVals += data[run][1]
        return xVals,yVals

    # plots all the data for a given trigger
    def plotAllData(self,trigger):
        # paramlist == fits
        missing_fit = False
        if not self.plotting_data.has_key(trigger):
            print "\tERROR: Trigger not found in plotting data - %s" % trigger
            return False
        else:
            data = self.plotting_data[trigger]  # { run_number: ( [x_vals], [y_vals], [det_status], [phys_status] ) }

        bad_ls_x = array.array('f')
        bad_ls_y = array.array('f')

        # Separate the good and bad LS points
        if self.ls_options['rm_bad_beams']:
            # Remove 'non-stable' beams LS
            for run in data:
                res = self.fitFinder.removeBadLS(data[run][0],data[run][1],data[run][3])
                data[run][0] = res[0]
                data[run][1] = res[1]
                bad_ls_x += res[2]
                bad_ls_y += res[3]
        elif self.ls_options['rm_bad_det']:
            # Remove 'bad' detector LS
            # NOTE: These LS are a super-set of the 'non-stable' LS
            for run in data:
                res = self.fitFinder.removeBadLS(data[run][0],data[run][1],data[run][2])
                data[run][0] = res[0]
                data[run][1] = res[1]
                bad_ls_x += res[2]
                bad_ls_y += res[3]

        skip_bad_ls_plot = (len(bad_ls_x) == 0 or len(bad_ls_y) == 0 or not self.ls_options['show_bad_ls'])

        run_count = 0
        num_pts = 0
        for run in data:
            x_pts,y_pts = self.fitFinder.removePoints(data[run][0],data[run][1])
            x_pts,y_pts = self.fitFinder.getGoodPoints(x_pts,y_pts)
            num_pts += len(y_pts)
            if len(data[run][0]) > 0:
                run_count += 1

        if num_pts < self.min_plot_pts:
            #print "\tSkipping %s: Not enough plot points, %d" % (trigger,num_pts)
            return False

        if self.use_fit and not self.fits.has_key(trigger):
            # No fit found for this plot
            print "\tWARNING: Missing fit - %s" % trigger
            missing_fit = True

        # Find max and min values
        maximumRR = array.array('f')
        maximumVals = array.array('f')
        minimumVals = array.array('f')

        max_xaxis_val = 0
        min_xaxis_val = 9999
        max_yaxis_val = 0

        xVals,yVals = self.combinePoints(data)
        avg_y,std_y = self.fitFinder.getSD(yVals)

        # Remove points that are extremely far outside of the avg
        for run in data:
            data[run][0],data[run][1] = self.fitFinder.getGoodPoints(data[run][0],data[run][1],avg_y,std_y,6)

        # Recalculate the avg and std dev
        xVals,yVals = self.combinePoints(data)
        avg_y,std_y = self.fitFinder.getSD(yVals)

        # Find minima and maxima so we create graphs of the right size
        for run in data:
            if len(data[run][0]) > 0:
                maximumVals.append(max(data[run][0]))
                minimumVals.append(min(data[run][0]))

                tmp_max_y = max(data[run][1])
                if abs(tmp_max_y - avg_y) < std_y*4:
                    # Don't let the maximum be set by rate 'spikes'
                    maximumRR.append(max(data[run][1]))

        if not skip_bad_ls_plot:
            # TODO: Possibly apply same 'spike' check to the bad LS lists
            maximumVals.append(max(bad_ls_x))
            minimumVals.append(min(bad_ls_x))
            maximumRR.append(max(bad_ls_y))

        if len(maximumRR) > 0:
            max_yaxis_val = max(maximumRR)
        else:
            print "\tERROR: Invalid boundary for plot axis!"
            return False
        if len(maximumVals) > 0:
            max_xaxis_val = max(maximumVals)
            min_xaxis_val = min(minimumVals)
        else:
            print "\tERROR: Invalid boundary for plot axis!"
            return False

        if max_xaxis_val == 0 or max_yaxis_val == 0:
            print "\tERROR: Invalid boundary for plot axis!"
            return False

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
        if self.color_by_fill:
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
            #data[run][0],data[run][1] = self.fitFinder.getGoodPoints(data[run][0],data[run][1])
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
            graphList[-1].SetMaximum(1.2*max_yaxis_val)
            graphList[-1].SetTitle(trigger)

            if counter == 0: graphList[-1].Draw("AP")
            else: graphList[-1].Draw("P")
            canvas.Update()

            if self.bunch_map.has_key(run):
                bunches = str(self.bunch_map[run])
            else:
                bunches = "-"

            legendStr = ""
            if self.color_by_fill:
                new_fill = self.fill_map[run]
                if new_fill != old_fill:
                    old_fill = new_fill
                    legendStr = "%s (%s b)" % (new_fill,bunches)
                    legend.AddEntry(graphList[-1],legendStr,"f")
            else:
                legendStr = "%s (%s b)" % (run,bunches)
                legend.AddEntry(graphList[-1],legendStr,"f")
            counter += 1

        if self.use_fit and not missing_fit: # Display all the fit functions
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
                    #func_leg.SetFillColorAlpha(0,0.5)
                    func_leg.Draw()
                    canvas.Update()

        if not skip_bad_ls_plot:
            bad_ls_graph = TGraph(len(bad_ls_x),bad_ls_x,bad_ls_y)

            bad_ls_graph.SetMarkerStyle(self.ls_options['bad_marker_style'])
            bad_ls_graph.SetMarkerSize(self.ls_options['bad_marker_size'])
            bad_ls_graph.SetMarkerColor(self.ls_options['bad_marker_color'])
            bad_ls_graph.SetLineWidth(2)
            bad_ls_graph.GetXaxis().SetTitle(self.label_X)
            bad_ls_graph.GetXaxis().SetLimits(0, 1.1*max_xaxis_val)
            bad_ls_graph.GetYaxis().SetTitle(self.label_Y)
            bad_ls_graph.SetMinimum(0)
            bad_ls_graph.SetMaximum(1.2*max_yaxis_val)
            bad_ls_graph.SetTitle(trigger)

            bad_ls_graph.Draw("P")
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
        if self.color_by_fill:
            legend.SetHeader("%s fills (%s runs):" % (self.fill_count,run_count))
        else:
            legend.SetHeader("%s runs:" % (run_count) )
        legend.SetFillColor(0)
        legend.Draw() 
        canvas.Update()

        if self.save_root_file:
            self.saveRootFile(canvas)

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

    # Note1: This function will also modify the value of max_y_val
    def getPredictionGraph(self,paramlist,min_x_val,max_x_val,max_y_val,trigger_name,run,lumi_info):
        # {'name': {run: [ (LS,pred,err) ] } }
        prediction_rec = {}  # A dict used to store predictions and prediction errors: [ 'name' ] { (LS), (pred), (err) }

        # --- 13 TeV constant values ---
        ppInelXsec = 80000.
        orbitsPerSec = 11246.

        # Initialize our point arrays
        lumisecs    = array.array('f')
        predictions = array.array('f')
        ls_error    = array.array('f')
        pred_error  = array.array('f')
        # Unpack values
        fit_type, X0, X1, X2, X3, sigma, meanraw, X0err, X1err, X2err, X3err, ChiSqr = paramlist
        # Create our point arrays
        for LS, ilum, psi, phys, cms_ready in lumi_info:
            if not ilum is None and phys:
                lumisecs.append(LS)
                pu = (ilum * ppInelXsec) / ( self.bunch_map[run] * orbitsPerSec )
                # Either we have an exponential fit, or a polynomial fit
                if fit_type == "exp":
                    rr = self.bunch_map[run] * (X0 + X1*math.exp(X2+X3*pu))
                else:
                    rr = self.bunch_map[run] * (X0 + pu*X1 + (pu**2)*X2 + (pu**3)*X3)
                if rr < 0: rr = 0 # Make sure prediction is non negative
                predictions.append(rr)
                ls_error.append(0)
                pred_error.append(self.bunch_map[run]*self.sigmas*sigma)
        # Record for the purpose of doing checks
        prediction_rec.setdefault(trigger_name,{})[run] = zip(lumisecs, predictions, pred_error)
        # Set some graph options
        fit_graph = TGraphErrors(len(lumisecs), lumisecs, predictions, ls_error, pred_error)
        fit_graph.SetTitle("Fit (%s sigma)" % (self.sigmas)) 
        fit_graph.SetMarkerStyle(8)
        fit_graph.SetMarkerSize(0.8)
        fit_graph.SetMarkerColor(2) # Red
        fit_graph.SetFillColor(4)
        fit_graph.SetFillStyle(3003)
        fit_graph.GetXaxis().SetLimits(min_x_val, 1.1*max_x_val)

        max_pred = prediction_rec[trigger_name][run][0][1]
        if max_pred > max_y_val: max_y_val = max_pred

        return fit_graph

    # Note1: I would like to remove the dependance on lumi_info from this function, but for now this works
    # lumi_info - [ (LS,ilum,psi,phys,cms_ready) ]
    def makeCertifyPlot(self,trigger,run,lumi_info):
        if not self.fits.has_key(trigger):
            # Missing the fit for this trigger, so skip it
            return False
        elif not self.plotting_data.has_key(trigger):
            print "\tERROR: Trigger not found in plotting data, %s" % trigger
            return False
        elif not self.plotting_data[trigger].has_key(run):
            print "\tERROR: Trigger is missing run, %s" % run
            return False
        else:
            data = self.plotting_data[trigger][run]  # ([x_vals], [y_vals], [status])

        maximumRR = array.array('f')
        maximumVals = array.array('f')
        minimumVals = array.array('f')

        yVals = array.array('f')
        xVals = array.array('f')

        xVals, yVals = self.fitFinder.getGoodPoints(data[0], data[1]) 
        if len(xVals) > 0:
            maximumRR.append(max(yVals))
            maximumVals.append(max(xVals))
            minimumVals.append(min(xVals))

        if len(maximumRR) > 0: max_yaxis_val = max(maximumRR)
        else: return False
        
        if len(maximumVals) > 0:
            max_xaxis_val = max(maximumVals)
            min_xaxis_val = min(minimumVals)
        else: return False

        if max_xaxis_val == 0 or max_yaxis_val == 0: return

        canvas = TCanvas(self.var_X, self.var_Y, 1000, 600)
        canvas.SetName(trigger+"_"+self.var_X+"_vs_"+self.var_Y)

        best_fit_type,best_fit = self.fitFinder.getBestFit(self.fits[trigger])
        predictionTGraph = self.getPredictionGraph( best_fit,
                                                    min_xaxis_val,
                                                    max_xaxis_val,
                                                    max_yaxis_val,
                                                    trigger,
                                                    run,
                                                    lumi_info)
        num_LS = len(data[0])
        legend = self.getLegend(num_entries=2)
        plotTGraph = TGraph(num_LS, data[0], data[1])

        graph_color = self.getColorMap()[run]

        plotTGraph.SetMarkerStyle(7)
        plotTGraph.SetMarkerSize(1.0)
        plotTGraph.SetLineColor(graph_color)
        plotTGraph.SetFillColor(graph_color)
        plotTGraph.SetMarkerColor(graph_color)
        plotTGraph.SetLineWidth(2)
        #plotTGraph.GetXaxis().SetTitle(self.name_X+" "+self.units_X)
        plotTGraph.GetXaxis().SetTitle(self.label_X)
        plotTGraph.GetXaxis().SetLimits(0, 1.1*max_xaxis_val)
        plotTGraph.GetYaxis().SetTitle(self.label_Y)
        plotTGraph.GetYaxis().SetTitleOffset(1.2)
        plotTGraph.SetMinimum(0)
        plotTGraph.SetMaximum(1.2*max_yaxis_val)
        plotTGraph.SetTitle(trigger)

        plotTGraph.Draw("AP")
        canvas.Update()

        if self.bunch_map.has_key(run):
            bunches = str(self.bunch_map[run])
        else:
            bunches = "-"

        legend_str = ""
        legend_str = "%s (%s b)" % (run,bunches)
        legend.AddEntry(plotTGraph,legend_str,"f")

        legend.SetHeader("%s runs:" % 1 )

        predictionTGraph.Draw("PZ3")
        canvas.Update()
        legend.AddEntry(predictionTGraph, "Fit ( %s \sigma )" % (self.sigmas))

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

        legend.SetFillColor(0)
        legend.Draw() 
        canvas.Update()

        if self.save_root_file:
            self.saveRootFile(canvas)

        if self.save_png:
            self.savePlot(trigger,canvas)

        return True

    # Note1: This function assumes the x_vals correspond to LS
    # Note2: Some of this function might be better placed elsewhere
    # Note3: Searching for the bad LS would be made significantly easier if we switched to dictionaries
    # pred_data - {'trigger name': [ (LS,pred,err) ] }
    def makeCertifySummary(self,run,pred_data,log_file):
        # NOTE: pred_data should have keys that only corresponds to triggers in the monitorlist, but self.plotting_data should have *ALL* trigger data
        # UNFINISHED

        gStyle.SetOptStat(0)

        ls_set = set()
        bad_ls = {}         # The total number of bad paths in a given LS, {LS: int}
        trg_bad_ls = {}     # List of bad LS for each trigger
        for trigger in pred_data:
            # data - ( [x_vals], [y_vals], [status] )
            data = self.plotting_data[trigger][run]
            ls_set.update(data[0])
            for LS,pred,err in pred_data[trigger]:
                for data_ls,data_rate in zip(data[0],data[1]):
                    if data_ls != LS:
                        continue
                    for pred_ls,pred_rate,pred_err in pred_data[trigger]:
                        if pred_ls != data_ls:
                            continue
                        if abs(data_rate - pred_rate) > pred_err:
                            if not trg_bad_ls.has_key(trigger):
                                trg_bad_ls[trigger] = []
                            trg_bad_ls[trigger].append(int(LS))

                            if bad_ls.has_key(LS):
                                bad_ls[LS] += 1
                            else:
                                bad_ls[LS] = 1

        max_bad_paths = 1
        bad_ls_inverted = {}    # {int: [LS]}
        for LS in bad_ls:
            count = bad_ls[LS]
            if count > max_bad_paths:
                max_bad_paths = count
                
            if not bad_ls_inverted.has_key(count):
                bad_ls_inverted[count] = []
            bad_ls_inverted[count].append(int(LS))

        ### MAKE THE SUMMARY TEXT FILE ###
        log_file.write("\n")
        log_file.write("     TRIGGERS: BAD LUMIECTION(S)\n")
        log_file.write("\n")

        for trigger in sorted(trg_bad_ls.keys()):
            log_file.write("     %s: " % trigger)
            formatted_list = "["
            sorted_ls = sorted(trg_bad_ls[trigger])
            min_ls = sorted_ls[0]
            max_ls = sorted_ls[-1]
            for LS in sorted_ls:
                if LS == max_ls + 1 or LS == min_ls:
                    max_ls = LS
                    continue
                else:
                    formatted_list += "[%d,%d], " % (min_ls,max_ls)
                    min_ls = LS
                    max_ls = LS
            if formatted_list == "[":
                # Only possible for ls lists of length 1 or a single contigous block of bad ls
                formatted_list = "[[%d,%d]]" % (min_ls,max_ls)
            else:
                formatted_list += "[%d,%d]]" % (min_ls,max_ls)

            log_file.write(formatted_list+"\n")

        log_file.write("\n")
        log_file.write("     # OF BAD PATHS : LUMISECTION(S)\n")
        log_file.write("\n")

        min_ls = min(ls_set)
        max_ls = max(ls_set)
        tot_ls = len(ls_set)

        for count in sorted(bad_ls_inverted.keys(),reverse=True):
            log_file.write("     %d : %s\n" % (count,str(bad_ls_inverted[count])))

        log_file.write("\n")
        log_file.write("BAD LS SUMMARY:\n")
        log_file.write("\n")

        #bad_count = sum([bad_ls[x] for x in bad_ls.keys()])
        bad_count = len(bad_ls.keys())
        total_count = len(ls_set)

        log_file.write("---- Total bad LS: %d ( bad LS: >= 1 trigger(s) deviating more than 3 sigma from prediction )\n" % bad_count)
        log_file.write("---- Total LS: %d\n" % total_count)
        log_file.write("---- Fraction bad LS: %.2f\n" % (100.*float(bad_count)/float(total_count)))

        log_file.write("\n")
        log_file.write("BAD PATH SUMMARY:\n")
        log_file.write("\n")

        bad_count = len(trg_bad_ls.keys())
        total_count = len(pred_data.keys())

        log_file.write("---- Total Bad Paths: %d\n" % bad_count)
        log_file.write("---- Total Possible Paths: %d\n" % total_count)
        log_file.write("---- Fraction that are Bad Paths: %.2f\n" % (100.*float(bad_count)/float(total_count)))

        ### MAKE THE SUMMARY HISTOGRAM ###

        canvas = TCanvas("canv", "canv", 1000, 600)
        canvas.SetName("Certification Summary of Run %s" % run)
        canvas.SetGridx(1)
        canvas.SetGridy(1)

        summary_hist = TH1D("Certification_Summary_of_Run%s" % (run), "Run %s" % (run), (tot_ls+2), (min_ls-1), (max_ls+1))
        summary_hist.GetXaxis().SetTitle("LS")
        summary_hist.GetYaxis().SetTitle("Number of bad paths")
        summary_hist.SetMaximum(1.2 * max_bad_paths)

        for LS in bad_ls:
            summary_hist.Fill(LS,bad_ls[LS])

        max_line = TLine(min_ls - 1, max_bad_paths, max_ls + 1, max_bad_paths)
        max_line.SetLineStyle(9)
        max_line.SetLineColor(2)
        max_line.SetLineWidth(2)

        summary_hist.Draw("hist")
        summary_hist.SetLineColor(4)
        summary_hist.SetFillColor(4)
        summary_hist.SetFillStyle(3004)

        canvas.Update()

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

        canvas.Update()

        max_line.Draw("same")

        canvas.Update()

        #canvas.Modified()
        #canvas.Write()
        
        if self.save_root_file:
            self.saveRootFile(canvas)

        if self.save_png:
            canvas.Print(self.save_dir + "/" + "CertificationSummary_run%d" % run + ".png","png")
            #self.savePlot("CertificationSummary_run%d" % run,canvas)

        gStyle.SetOptStat(1)

    def saveRootFile(self,canvas):
        # Update root file
        path = self.save_dir + "/" + self.root_file_name
        file = TFile(path,"UPDATE")
        canvas.Modified()
        canvas.Write()

    def savePlot(self,name,canvas):
        canvas.Print(self.save_dir + "/" + self.plot_dir + "/" + name + ".png", "png")

