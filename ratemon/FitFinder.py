#####################################################################
# File: FitFinder.py
# Author: Charlie Mueller, Nathaniel Rupprecht, Andrew Wightman
# Date Created: August 31, 2016
#
# Dependencies: None
#
# Data Type Key:
#    ( a, b, c, ... )       -- denotes a tuple
#    [ a, b, c, ... ]       -- denotes a list
#    { key:obj }            -- denotes a dictionary
#    { key1: { key2:obj } }  -- denotes a nested dictionary
#####################################################################

import pickle as pickle
import math
import array
import os
import copy

from ROOT import gROOT, TCanvas, TF1, TGraph, TGraphErrors, TPaveStats, gPad, gStyle, TLegend
from ROOT import TFile, TPaveText, TBrowser, TString

#gROOT.ProcessLine(".L %s/functions.cc+" % os.getcwd())
#from ROOT import mySinh


class FitFinder:
    def __init__(self):
        #self.fits_to_try = ["linear","quad"]
        #self.fits_to_try = ["sinh"]
        self.fits_to_try = ["linear","quad","sinh"]
        #self.fits_to_try = ["cube","exp","sinh"]
        #self.fits_to_try = ["linear"]
        #self.fits_to_try = ["quad","cube","exp"]

        self.min_plot_pts = 10

        self.weight_map = {
            'linear': 0.00,
            'quad': 0.03,
            'sinh': 0.03,
        }

        self.use_point_selection = True
        self.use_best_fit = False
        self.use_weighted_fit = True

        self.data_dict = {}

    # Returns: {'trigger': fit_params}
    # data: {'trigger': { run_number:  ( [x_vals], [y_vals], [status] ) } }
    # NOTE1: Need to figure out why the fitter is generating NaN's for the fits
    def makeFits(self,data,object_list,normalization,group='user_input'):
        fits = {}           # {'trigger': { 'fit_type': fit_params } }
        skipped_fits = {}   # {'trigger': 'reason'}
        nan_fits = {}       # {'trigger': { 'fit_type': param_index } }

        print("Making fits...")
        counter = 0
        for trigger in object_list:
            if counter % max(1,math.floor(len(object_list)/10.)) == 0:
                print("\tProgress: %.0f%% (%d/%d)" % (100.*counter/len(object_list),counter,len(object_list)))
            counter += 1

            if trigger not in data:
                continue
            x_fit_vals = array.array('f')
            y_fit_vals = array.array('f')
            for run in sorted(data[trigger]):
                for x,y,status in zip(data[trigger][run][0],data[trigger][run][1],data[trigger][run][2]):
                    if status: # only fit data points when ALL subsystems are IN.
                        x_fit_vals.append(x)
                        # Remove the normalization during fitting (to avoid excessively small y-vals)
                        y_fit_vals.append(y*normalization)

            x_fit_vals, y_fit_vals = self.removePoints(x_fit_vals,y_fit_vals,0)   # Don't fit points with 0 rate

            if len(x_fit_vals) > self.min_plot_pts:
                new_fit = {}
                try:
                    new_fit = self.findFit(x_fit_vals,y_fit_vals,trigger)
                except KeyError:
                    print("\tUnable to create fit for: %s" % trigger)
                    skipped_fits[trigger] = "KeyError"
                    continue
                # Check to see if the fitter produced a NaN value for one of the fit params
                for fit_type in new_fit:
                    for i in range(len(new_fit[fit_type])):
                        if i == 0:
                            continue
                        elif math.isnan(new_fit[fit_type][i]):
                            if trigger not in nan_fits:
                                nan_fits[trigger] = {}
                            if fit_type not in nan_fits[trigger]:
                                nan_fits[trigger][fit_type] = i 
                            new_fit[fit_type][i] = 0.0
                        # Re-apply the normalization
                        if fit_type == "sinh":
                            # We need to scale all params EXCEPT param[0]
                            if i == 0 or i == 1 or i == 7:
                                # i == 0 is fit_type
                                # i == 1 is param[0]
                                # i == 7 is param_err[0]
                                continue
                            else:
                                new_fit[fit_type][i] /= normalization
                        elif fit_type == "exp":
                            # We need to scale all params EXCEPT param[2] and param[3]
                            if i == 0 or i == 3 or i == 4 or i == 9 or i == 10:
                                # i == 0 is fit_type
                                # i == 3 is param[2]
                                # i == 4 is param[3]
                                # i == 9 is param_err[2]
                                # i == 10 is param_err[3]
                                continue
                            else:
                                new_fit[fit_type][i] /= normalization
                        else:
                            # Scale all params
                            if i == 0:
                                # i == 0 is fit_type
                                continue
                            else:
                                new_fit[fit_type][i] /= normalization
                fits[trigger] = {}
                fits[trigger][group] = new_fit
            else:
                skipped_fits[trigger] = "Not enough points"

        if len(skipped_fits) > 0:
            print("Skipped fits:")
            for name in sorted(skipped_fits.keys()):
                print("\t%s: %s" % (name,skipped_fits[name]))

        if len(nan_fits) > 0:
            print("NaN fits: %d" % len(list(nan_fits.keys())))

        return fits

    # Removes points with y-values outside of a given range
    def getGoodPoints(self,xVals,yVals,avg_y=None,std_y=None,sig_y=4):
        goodX = array.array('f')
        goodY = array.array('f')
        if avg_y is None or std_y is None:
            # Recalculate these values
            avg_y, std_y = self.getSD(yVals)
        for x,y in zip(xVals,yVals):
            if (abs(y-avg_y) < sig_y*std_y):
                goodX.append(x)
                goodY.append(y)

        return goodX, goodY

    #Use: Removes pts with a y-val equal to ptVal
    def removePoints(self, xVals, yVals, ptVal=0):
        arrX = array.array('f')
        arrY = array.array('f')
        for x,y in zip(xVals,yVals):
            if y != ptVal:
                arrX.append(x)
                arrY.append(y)

        return arrX, arrY

    # Separates pts based on LS status flag
    def removeBadLS(self,xVals,yVals,status):
        goodX = array.array('f')
        goodY = array.array('f')
        badX = array.array('f')
        badY = array.array('f')
        for x,y,stat in zip(xVals,yVals,status):
            if stat:
                goodX.append(x)
                goodY.append(y)
            else:
                badX.append(x)
                badY.append(y)

        return goodX, goodY, badX, badY

    #returns SD of PU for a given run 
    def getSD(self,xVals):
        _sum = 0
        for x in xVals: _sum += x
        try: average_x = _sum/len(xVals)
        except: return 0, 0; 
        mse = 0
        for x in xVals: mse += (x - average_x)**2

        return average_x, math.sqrt(mse/len(xVals)) 

    # Use: Finds the root of the mean squared error of a fit
    # Returns: The square root of the mean squared error
    def getMSE(self, fitFunc, xVals, yVals):
        mse = 0
        for x,y in zip(xVals, yVals):
            mse += (fitFunc.Eval(x) - y)**2

        return math.sqrt(mse/len(xVals))

    def emptyFit(self):
        maxX = 1
        linear = TF1("Linear Fit", "pol1", 0, maxX)
        OutputFit = ["linear"]
        OutputFit += [0, 0, 0, 0]
        OutputFit += [0, 0, 0, 0, 0, 0]
        OutputFit += [0]

        return OutputFit

    def tryFit(self, xVals, yVals, name, fit_type):
        supported_fits = ["linear","quad","quad2","cube","exp","sinh"]
        if not fit_type in supported_fits:
            print("Fit not supported, generating empty fit...")
            return self.emptyFit()

        # Set up graph and functions
        fitGraph = TGraph(len(xVals), xVals, yVals)
        maxX = max(xVals)

        if fit_type == "linear":
            fit_func = TF1("Linear Fit","pol1",0,maxX)
        elif fit_type == "quad":
            fit_func = TF1("Quadratic Fit","pol2",0,maxX)
        elif fit_type == "quad2":
            fit_func = TF1("Quadratic Fit","pol2",0,maxX)
            fit_func.SetParameter(0,0.0)
            fit_func.FixParameter(0,0.0)
        elif fit_type == "cube":
            fit_func = TF1("Cubic Fit" ,"pol3",0,maxX)
            fit_func.SetParameter(0,0.0)
            fit_func.FixParameter(0,0.0)
        elif fit_type == "exp":
            fit_func = TF1("Exp Fit","[0]+[1]*expo(2)",0,maxX)
            #fit_func.SetParameter(1,1.0)
            #fit_func.FixParameter(1,1.0)
        elif fit_type == "sinh":
            my_sinh = "[1]*sinh([0]*x) + [2]"
            fit_func = TF1("Sinh Fit",my_sinh,0,maxX)
            fit_func.SetParameter(0,0.05)
            fit_func.SetParameter(1,0.5)
            fit_func.SetParameter(2,0.0)

        fitGraph.Fit(fit_func,"QNM","rob=0.90")

        fitMSE = self.getMSE(fit_func,xVals,yVals)

        OutputFit = [fit_type]
        OutputFit += [fit_func.GetParameter(0),fit_func.GetParameter(1),fit_func.GetParameter(2),fit_func.GetParameter(3)]
        OutputFit += [fitMSE, 0, fit_func.GetParError(0), fit_func.GetParError(1), fit_func.GetParError(2), fit_func.GetParError(3)]
        OutputFit += [fit_func.GetChisquare()]

        return OutputFit

    def findFit(self, xVals, yVals, name):
        output_fits = {}                                        # {'fit_type': fit_params }
        if self.use_point_selection:
            goodX, goodY = self.getGoodPoints(xVals,yVals)
            goodX, goodY = self.removePoints(goodX,goodY,0)
        else:
            goodX, goodY = xVals, yVals

        if len(goodX) == 0 or len(goodY) == 0:
            output_fits["empty"] = self.emptyFit()
            return output_fits

        all_fits = {}                                               # {'fit_type': fit_params }
        for fit_type in self.fits_to_try:
            all_fits[fit_type] = self.tryFit(goodX,goodY,name,fit_type)

        if self.use_best_fit:
            best_type, best_fit = self.getBestFit(all_fits)
            if not best_type is None:
                output_fits[best_type] = best_fit
        else:
            output_fits = all_fits

        return output_fits

    # Selects only the best fit from the set of fits generated, uses MSE as comparison
    def getBestFit(self,fits):
        fit_map = {}    # {'fit_type': {mse: fit_mse, weight: val}}
        min_MSE = None
        best_type = None
        best_fit = None
        for fit_type in fits:
            mse = fits[fit_type][5]
            if mse == 0:
                continue

            fit_map[fit_type] = {
                'mse': mse,
                'weight': 0,
            }
            if min_MSE is None:
                min_MSE = mse
                best_type = fit_type
                best_fit = fits[fit_type]
            elif mse < min_MSE:
                min_MSE = mse
                best_type = fit_type
                best_fit = fits[fit_type]

        if best_type is None:
            # All the fit mse were 0
            #return None,None,
            return "empty",self.emptyFit()

        if self.use_weighted_fit:
            best_mse = fit_map[best_type]['mse']
            weighted_best_type = None
            weight_best_fit = None
            min_val = None
            for fit_type in fits:
                fit_mse = fit_map[fit_type]['mse']
                val = abs(fit_mse - best_mse)/best_mse
                if fit_type in self.weight_map:
                    val += self.weight_map[fit_type]
                if min_val is None:
                    min_val = val
                    weighted_best_type = fit_type
                    weighted_best_fit = fits[fit_type]
                elif val < min_val:
                    min_val = val
                    weighted_best_type = fit_type
                    weighted_best_fit = fits[fit_type]
            return weighted_best_type,weighted_best_fit
        else:
            return best_type,best_fit

    # Saves the fits to a .pkl file, will *ONLY* save the specified fit_type
    # If no fit_type is specified, we save the fit with the smallest MSE
    def saveFits(self,fits,fname,fdir,fit_type=None):
        fits_to_save = {}           # {'trigger': fit_params}
        #for trigger in fits:
        #    if fit_type is None:
        #        b_type, b_fit = self.getBestFit(fits[trigger])
        #        fits_to_save[trigger] = b_fit
        #    else:
        #        fits_to_save[trigger] = fits[trigger][fit_type]

        path = os.path.join(fdir,fname)
        f = open(path, "wb")
        #pickle.dump(fits_to_save,f, 2)
        pickle.dump(fits,f, 2)
        f.close()
        print("Fit file saved to: %s" % path)

    # Merges two fits together
    def mergeFits(self,fits1,fits2):

        new_fits = copy.deepcopy(fits1)
        for trg in list(fits2.keys()):

            if trg not in new_fits:
                new_fits[trg] = {}

            for group, fit_types in fits2[trg].items():
                # Note: This will overwrite fits if fits1 and fits2 have a group with the same name
                new_fits[trg][group] = copy.deepcopy(fit_types)

        return new_fits

        #new_fits = {}
        ## Set new_fits = fits1:
        #for trig_name in fits1.keys():
        #        new_fits[trig_name] = fits1[trig_name]

        ## Iterate over triggers in Fits2:
        #for trig_name in fits2.keys():

        #        # If fits2 has a trigger that's not in fits1, add it to new_fits
        #        if not new_fits.has_key(trig_name):
        #                new_fits[trig_name] = {}

        #        # Change fit_type name in new_fits
        #        for fit_type in fits2[trig_name].keys():
        #                #new_fit_type = fit_type+' %s' %(label)
        #                new_fit_type = '%s %s' %(label,fit_type)
        #                new_fits[trig_name][new_fit_type] = fits2[trig_name][fit_type]

        #return new_fits


    ### TEST TEST TEST 2nd try ###
    def getPredictionPoints(self,fit_params,lsVals,puVals,bunches,mod_skip=0):

        fit_type, X0, X1, X2, X3, sigma, meanraw, X0err, X1err, X2err, X3err, ChiSqr = fit_params

        ls_arr = array.array('f')
        pred_arr = array.array('f')
        ls_err = array.array('f')
        pred_err = array.array('f')

        idx =0
        for ls,pu  in zip(lsVals,puVals):
            if fit_type == "exp":
                rr = bunches * (X0 + X1*math.exp(X2+X3*pu))
            elif fit_type == "sinh":
                rr = bunches * (X1*math.sinh(X0*pu) + X2)
            else:
                rr = bunches * (X0 + pu*X1 + (pu**2)*X2 + (pu**3)*X3)
            if rr < 0: rr = 0                       # Make sure prediction is non negative
            if mod_skip and idx % mod_skip != 0:    # Do not plot every point (for clarity)
                idx = idx+1
                continue 
            ls_arr.append(ls)
            pred_arr.append(rr)
            ls_err.append(0)
            pred_err.append(bunches*3*sigma)
            idx = idx+1

        return ls_arr,pred_arr,ls_err,pred_err


        ## ----------- End of class FitFinder ------------ ## 

