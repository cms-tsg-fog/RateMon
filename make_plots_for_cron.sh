#!/bin/bash
# crontab line for this is:
# 59 * * * * lxplus.cern.ch /afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/make_plots_for_cron.sh > /dev/null

thisDir=/afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/
outputDirBase=/afs/cern.ch/user/g/gesmith/www/HLT/RateVsPU/

cd $thisDir

theFillsAndRuns=$(python test_dump_fills_runs.py)

theRuns="${theFillsAndRuns[@]:5}"
theFill="${theFillsAndRuns[@]:0:4}"

# Do subset of triggers:
python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill $theRuns

# Do "All triggers" plots:
python plotTriggerRates.py --triggerList=monitorlist_ALL.list --fitFile=Fits/AllTriggers/FOG.pkl --saveDirectory=$outputDirBase$theFill/MoreTriggers $theRuns


# This is just to grab the run numbers used in the fit:
while read -r line
do
    fitCommand="$line"
done < "Fits/2016/command_line.txt"

# Adjust the html content in the output dir:
match='<html>'
insertFirst='<h3>Runs used to produce fits:<br>'
insertSecond=$(echo $fitCommand | sed 's/python plotTriggerRates.py --createFit --nonLinear --triggerList=monitorlist_COLLISIONS.list//')
insertThird='</h3>'
insertFourth='<h3><a href="./MoreTriggers/">Larger Subset of Triggers</a></h3>'
insertFifth='<h3>A Few Representative Triggers:</h3>'
file=$outputDirBase$theFill/index.html

sed -i "s#$match#$match\n$insertFirst\n$insertSecond$insertThird\n$insertFourth\n$insertFifth#" $file
