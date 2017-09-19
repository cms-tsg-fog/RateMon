#! /bin/bash

HOST=$(hostname)

if [[ $HOST == *"lxplus"* ]]; then
    cd /afs/cern.ch/cms/slc6_amd64_gcc493/cms/cmssw/CMSSW_7_6_3/src
else
    export SCRAM_ARCH=slc5_amd64_gcc462
    export VO_CMS_SW_DIR=/nfshome0/cmssw2
    source $VO_CMS_SW_DIR/cmsset_default.sh
    cd $VO_CMS_SW_DIR/$SCRAM_ARCH/cms/cmssw/CMSSW_5_2_6/src
fi

#cmsenv
eval `scramv1 runtime -sh`

cd -

alias rateMon='python ShiftMonitorTool.py'
alias plotRates='python plotTriggerRates.py'