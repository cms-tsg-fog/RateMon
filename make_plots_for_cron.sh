#!/bin/bash

cd /afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/
outputDirBase=/afs/cern.ch/user/g/gesmith/www/HLT/RateVsPU/

theFillsAndRuns=$(python test_dump_fills_runs.py)

theRuns="${theFillsAndRuns[@]:5}"
theFill="${theFillsAndRuns[@]:0:4}"

#mkdir outputDirBase$theFill
#python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill --useFills $theFill
python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill $theRuns
