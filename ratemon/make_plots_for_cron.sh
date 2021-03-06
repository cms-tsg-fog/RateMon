#!/bin/bash
# crontab line for this is:
# 59 * * * * lxplus.cern.ch /afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/make_plots_for_cron.sh > /dev/null
# 59 * * * * /data/RateMon/make_plots_for_cron.sh > /dev/null

#thisDir=/afs/cern.ch/work/g/gesmith/runCert/AndrewBranchCron/RateMon
#thisDir=/afs/cern.ch/work/a/awightma/RateMon
thisDir=/data/RateMon

#outputDirBase=/afs/cern.ch/user/g/gesmith/www/HLT/RateVsPU/
#outputDirBase=$thisDir/tempTest/
#outputDirBase=/afs/cern.ch/user/a/awightma/www/dev/cron_output_test/
outputDirBase=/cmsnfsrateplots/rateplots/

cd $thisDir

source set.sh

theFillsAndRuns=$(python test_dump_fills_runs.py)

theRuns="${theFillsAndRuns[@]:5}"       # <-- This will break at fill 10000 (near the end of Run 3?)
theFill="${theFillsAndRuns[@]:0:4}"     # <-- This will break at fill 10000 (near the end of Run 3?)

# Manually re-create plots for particular fill
#theRuns="284006 284014"
#theFill=5450

# Do subset of triggers:
python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/Monitor_Triggers/FOG.pkl --saveDirectory="${thisDir}/${theFill}" $theRuns

# Do "All triggers" plots:
python plotTriggerRates.py --fitFile=Fits/All_Triggers/FOG.pkl --saveDirectory="${thisDir}/${theFill}/MoreTriggers" --cronJob $theRuns

if [ -d "${outputDirBase}${theFill}" ]; then
    # The directory already exists!
    rm -r "${outputDirBase}${theFill}"
fi

mv "${thisDir}/${theFill}" "${outputDirBase}${theFill}"

# Generate the index.html file
python FormatRatePlots.py "${outputDirBase}${theFill}"

cp "${thisDir}/WBM_CSS_Files/style.css" "${outputDirBase}${theFill}/style.css"
cp "${thisDir}/WBM_CSS_Files/table.css" "${outputDirBase}${theFill}/table.css"
