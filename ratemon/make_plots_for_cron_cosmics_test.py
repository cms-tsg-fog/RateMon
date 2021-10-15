# This script is a testing script that was used during MWGR #3 of 2021
# It uses the cronJobCosmics option of plotTriggerRates
# It's not clear that this script will be of any use in the long term, but it was useful for running tests while in cosmics mode during MWGRs, so we decided to commit it
# It is a bit hard-coded, as it was written for a very particular set of tests and checks, so if this script will be used in the future, it will certainly have to be edited a bit to fit the needs of whatever test it will be used for

#!/usr/bin/env python3
# crontab line for this is:
# 59 * * * * /data/RateMon/make_plots_for_cron.sh > /dev/null

import subprocess
import yaml
import os

#from DBParser import DBParser
import plotTriggerRates as ptr

# Read database configuration from file
with open('dbConfig.yaml', 'r') as stream:
    try:
        dbCfg = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print("Unable to read the given YAML database configuration file. Error:", exc)

controller = ptr.MonitorController()

# We did not use this for the tests this script was used for
def get_latest_run():
    run_info = parser.getLatestRunInfo()
    return run_info[0]

# Make the plots
def main():

    theFill = None
    theRuns = None

    testing = True

    # Manually select particular fill/runs
    theFill=7498
    theRuns=[341052]
    
    # Do not continue if we somehow have empty fills or runs
    if ((theRuns is None) or (theFill is None)):
        raise Exception
    else:
        print("The runs and fills are not None. Continuing with the script...")

    # Set up the dir to save to
    if testing:
        thisDir="/afs/cern.ch/work/k/kmohrman/rate_mon_dirs/RateMon_test-cron_branch/ratemon/ratemon" # NOTE: this is hard coded (will have to be changed if this script ever gets used again)
        saveDirBase=os.path.join(thisDir,"TMP_rateplots")
    else:
        raise Exception("This script is currently only set up to run in testing mode".)
    out_dir  = os.path.join(thisDir,str(theFill))
    save_dir = os.path.join(saveDirBase,str(theFill))
    out_dir  = os.path.join(out_dir,"MoreTriggers")
    save_dir = os.path.join(save_dir,"MoreTriggers")
    print(f"Out info:\n\tOutput plots to: {out_dir} \n\tSave plots to: {save_dir}")

    trigger_list = controller.readTriggerList("TriggerLists/monitorlist_COSMICS.list")

    # Make the plots
    controller.runStandalone(
        dbConfig = dbCfg,
        saveDirectory = out_dir,
        triggerList = trigger_list,
        cronJobCosmics = True,
        vsLS = True,
        data_lst = theRuns,
    )

    # Copy the plots to the final destination, if it does not already exist
    # We could have the code do this, but for the tests that we used this script for, we just moved the plots by hand.

main()
