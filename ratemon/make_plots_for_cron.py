# This is a placeholder script that shows an example of how to produce plots with the "cronJob" option of plotTriggerRates turned on
# For a full version of this script for Run 3, we will need the following three components:
#    1) Get the latest runs from the DB
#    2) Create the rate vs PU plots
#    3) Move the plots and summary json to /cmsnfsrateplots/rateplots/ on kvm-s3562-1-ip151-84, or wherever we decide to put them
# This script can do 1 and 2 but it does not do 3 right now, so we'll need to swap that in before we want to actually use it
# How to run this script: "python3 create_plots_dump_trg_json.py"

import os
import yaml
import socket
import datetime

from omsapi import OMSAPI
import plotTriggerRates as ptr
from DBParser import DBParser


# Initiate connection to endpoints and authenticate
hostname = socket.gethostname()
if "lxplus" in hostname:
    omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1", cert_verify=False)
    omsapi.auth_krb()
else:
    omsapi = OMSAPI("http://cmsoms.cms:8080/api")


# Read database configuration from file (needed since we use the oldParser option for getPathsInDatasets())
with open('dbConfig.yaml', 'r') as stream:
    try:
        dbCfg = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print("Unable to read the given YAML database configuration file. Error:", exc)


# Constructs the str for the out dir path
def make_output_dir_str(base_dir,subdir_str,append_timestamp=True):
    sub_dir_name = subdir_str
    if append_timestamp:
        timestamp_tag = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        sub_dir_name = sub_dir_name + "_" + timestamp_tag
    out_dir_path_name = os.path.join(base_dir,sub_dir_name)
    return out_dir_path_name


# Make the plots
def main():

    controller = ptr.MonitorController()
    parser = DBParser()

    # Get the runs from the latest fill with stable beams
    run_lst , fill_num = parser.getRecentRuns()
    #run_lst , fill_num = [324998,324999,325000,325001] , 7324 # Hard code specific runs, for testing
    
    # Some placeholder options for where to save the plots
    # Eventually we'll want to save to /cmsnfsrateplots/rateplots/ or wherever (or mv the plots to there after we create them)
    save_dir_base = os.getcwd() # For testing
    #save_dir_base = "/eos/user/k/kmohrman/www/rate_vs_PU_plots/checks_for_oms/" # For testing on lxplus (if you are kelci)
    #save_dir_base = "/cmsnfsrateplots/rateplots/testing/" # For testing on kvm-s3562-1-ip151-84
    out_dir = make_output_dir_str(save_dir_base,"testing_ratemon_"+str(fill_num))

    # Which triggers to use
    trigger_list = controller.readTriggerList("TriggerLists/monitorlist_COLLISIONS.list")

    # Make the plots
    controller.runStandalone(
        oldParser      = True,
        dbConfig       = dbCfg,
        saveDirectory  = out_dir,
        triggerList    = trigger_list,
        data_lst       = run_lst,
        cronJob        = True, # For testing in the mode we'll use during data taking
        fitFile        = "Fits/All_Triggers/FOG.pkl"
    )


if __name__ == "__main__":
    main()
