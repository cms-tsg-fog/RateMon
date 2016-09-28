#!/bin/bash

cd /afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/
outputDirBase=/afs/cern.ch/user/g/gesmith/www/HLT/

#theFill=$(python test_dump_fills_runs.py)
theFillsAndRuns=$(python test_dump_fills_runs.py)

#echo $theRuns
echo " "

#IFS=' ' read -ra fillAndRuns <<< "$theRuns"
#echo $fillAndRuns
#
#for i in "${fillAndRuns[@]}"; do
#    echo $i
#done


#fillAndRuns=$(echo $theRuns | tr " " "\n")

theRuns="${theFillsAndRuns[@]:5}"
theFill="${theFillsAndRuns[@]:0:4}"


#for number in $fillAndRuns
#do
#    echo $number
#done


mkdir outputDirBase$theFill
#python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill --useFills $theFill
python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill $theRuns
