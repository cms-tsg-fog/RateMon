# This is a script that can be used  to produce plots with the "cronJob" option of plotTriggerRates turned on
# For a full version of this script for Run 3, we will need the following three components:
#    1) Get the latest runs from the DB
#    2) Create the rate vs PU plots
#    3) Save and/or move the plots and summary json to /cmsnfsrateplots/rateplots/ on kvm-s3562-1-ip151-84 and/or to the dir on eos
# Example of how to run this script with cron:
#   - In the crontab file, put: "1 * * * * python3 /opt/ratemon/make_plots_for_cron.py > /dev/null"

import os
import yaml
import socket
import datetime

import plotTriggerRates as ptr
from omsapi import OMSAPI
from DBParser import DBParser

# Read database parser 
parser = DBParser()

# Constructs the str for the out dir path
def make_output_dir_str(base_dir,subdir_str,append_timestamp=False):
    sub_dir_name = subdir_str
    if append_timestamp:
        timestamp_tag = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        sub_dir_name = sub_dir_name + "_" + timestamp_tag
    out_dir_path_name = os.path.join(base_dir,sub_dir_name)
    return out_dir_path_name

def getRunType(runNumber): # FIXME: should be replaced by version in plotTriggerRates.py when oldParser is removed
    try:
        triggerMode = parser.getTriggerMode(runNumber)
    except:
        triggerMode = "other"
    
    if triggerMode.find("cosmics") > -1:
        runType = "cosmics"
    elif triggerMode.find("circulating") > -1:
        runType = "circulating"
    elif triggerMode.find("collisions") > -1:
        if parser.getFillType(runNumber).find("IONS") > -1:
            runType = "collisionsHI" # heavy-ion collisions
        else:
            runType = "collisions" # p-p collisions
    elif triggerMode == "MANUAL":
        runType = "MANUAL"
    elif triggerMode.find("highrate") > -1:
        runType = "other"
    else: runType = "other"
    
    return runType

# Make the plots
def main():

    controller = ptr.MonitorController()

    # Get the runs from the latest fill with stable beams
    run_lst , fill_num = parser.getRecentRuns()
    
    print(f"Making plots for fill {fill_num}, runs: {run_lst}")
    if len(run_lst) == 0: raise Exception("Error: No runs specified. Exiting.")

    # Some placeholder options for where to save the plots
    save_dir_base = "/cmsnfsrateplots/rateplots/LS2/" # For LS2 tests on kvm-s3562-1-ip151-84 # FIXME: needs to be updated to Run3 for OMS to pick up
    out_dir = make_output_dir_str(save_dir_base,str(fill_num))
    print("Saving plots to:",out_dir)

    # Define run type
    for run in run_lst:
        run_type = getRunType(run)
        if run_type != getRunType(run_lst[0]): # sanity check
            print("WARNING: Run type has changed across the list of runs.")
            break
    
    # Which triggers to use
    trigger_list = controller.readTriggerList("/opt/ratemon/TriggerLists/monitorlist_{runType}.list".format(runType = run_type.upper()))

    # Make the plots
    controller.runStandalone(
        saveDirectory  = out_dir,
        triggerList    = trigger_list,
        data_lst       = run_lst,
        runType        = run_type,
        cronJob        = True, 
        fitFile        = "/opt/ratemon/Fits/{runType}/referenceFits_{runType}_all.pkl".format(runType = run_type)
    )


if __name__ == "__main__":
    main()
