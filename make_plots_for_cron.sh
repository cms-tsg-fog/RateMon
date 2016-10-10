#!/bin/bash

cd /afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/
outputDirBase=/afs/cern.ch/user/g/gesmith/www/HLT/RateVsPU/

theFillsAndRuns=$(python test_dump_fills_runs.py)

theRuns="${theFillsAndRuns[@]:5}"
theFill="${theFillsAndRuns[@]:0:4}"

#mkdir outputDirBase$theFill
#python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill --useFills $theFill
python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill $theRuns

while read -r line
do
    fitCommand="$line"
done < "Fits/2016/command_line.txt"

match='<html>'
insertFirst='Runs used to produce fits:<br>'
insertSecond=$(echo $fitCommand | sed 's/python plotTriggerRates.py --createFit --nonLinear --triggerList=monitorlist_COLLISIONS.list//')
file=$outputDirBase$theFill/index.html

sed -i "s/$match/$match\n$insertFirst\n$insertSecond/" $file
