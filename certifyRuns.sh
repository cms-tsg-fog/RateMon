#!/bin/bash 
#Usage ./certifyRuns.sh runList TriggerList firstFitRun lastFitRun fitFile fitRootFile JSONFile

runList=runList.txt
TriggerList=monitorlist_Sept_Core_2012.list
firstFitRun=202305
lastFitRun=203002
fitFile=Fits/2012/Fit_HLT_NoV_10LS_Run${firstFitRun}to${lastFitRun}.pkl #Contains fit parameters to make predictions
fitRootFile=HLT_10LS_delivered_vs_rate_Run${firstFitRun}-${lastFitRun}.root #Contains fit curves to look at
JSONFile=Cert_190456-202305_8TeV_PromptReco_Collisions12_JSON.txt #Latest golden json to be use in making fit file

if [ $# -ge 1 ]; then
    runList=${1}
fi
if [ $# -ge 2 ]; then
    TriggerList=${2}
fi
if [ $# -ge 3 ]; then
    firstFitRun=${3}
fi
if [ $# -ge 4 ]; then
    lastFitRun=${4}
fi
if [ $# -ge 5 ]; then
    fitFile=${5}
fi
if [ $# -ge 6 ]; then
    fitRootFile=${6}
fi
if [ $# -ge 7 ]; then
    JSONFile=${7}
fi

echo Certifying runs from file $runList
echo Using Trigger List $TriggerList from run $firstFitRun to $lastFitRun 
echo Fit files are $fitFile $fitRootFile 
echo JSON file is $JSONFile

if [ ! -f $JSONFile ]; then
    scp lxplus.cern.ch:/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions12/8TeV/Prompt/${JSONFile} .
fi

if [ ! -f $runList ]; then
     echo "Did not find $runList, but it can be made like"
     echo 'for i in $(eval echo {202305..203002}); do echo $i >> runList.txt ; done'
     exit 1
fi

#if fit file doesn't exist, make it!!!
if [[ ( ! -f $fitFile ) || ( ! -f $fitRootFile ) ]]; then
    echo Fit file do not exist, creating
    ./DatabaseRatePredictor.py --makeFits --TriggerList=$TriggerList --Beam --NoVersion --json=$JSONFile ${firstFitRun}-${lastFitRun}
    echo Done making fit file.
fi

if [[ ! -f $fitFile ]]; then
    echo "Fit file $fitFile does not exist...aborting"
    exit 1
fi

if [[ ! -f $fitRootFile ]]; then
    echo "Fit file $fitRootFile does not exist...aborting"
    exit 1
fi

touch nonCollisionsRunList.txt
for run in `cat $runList` 
  do
  if [ -f HLT_1LS_ls_vs_rawrate_Run${run}-${run}.pdf ]; then
      echo Skipping because .pdf exists for run $run
      continue
  fi

  if [[ $(grep $run nonCollisionsRunList.txt 2> /dev/null) ]] ; then
      echo Skipping because run $run was already checked to be non-collisions
      continue
  fi

  echo Producing Plots for run $run
  ./DatabaseRatePredictor.py --Beam --secondary --TriggerList=${TriggerList} --fitFile=${fitFile} ${run}  >& log
  if [ ! -f HLT_1LS_ls_vs_rawrate_Run${run}-${run}.root ]; then
      echo -e "\tNo output root fit file for run $run, was the collisions key used?\n"
      echo $run >> nonCollisionsRunList.txt
      continue
  fi

  root -b -l -q 'dumpToPDF.C+("HLT_1LS_ls_vs_rawrate_Run'${run}'-'${run}'.root", "'${fitRootFile}'")'  
  if [ $? -ne 0 ]; then
      echo Return value from dumpToPDF not 0!!!! Quitting...
      exit 1
  fi
done

echo Done.

