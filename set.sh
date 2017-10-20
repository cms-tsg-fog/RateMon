#! /bin/bash

HOST=$(hostname)

if [[ $HOST == *lxplus* ]]; then
    # lxplus machines
    export VO_CMS_SW_DIR=/nfshome0/cmssw3
    export SCRAM_ARCH=slc7_amd64_gcc630
    export CMSSW_VERSION=CMSSW_9_2_10
elif [[ $HOST == *hilton* ]]; then
    # hilton machines
    export VO_CMS_SW_DIR=/opt/offline
    export SCRAM_ARCH=slc7_amd64_gcc630
    export CMSSW_VERSION=CMSSW_9_2_10
else
    # other online machines
    export VO_CMS_SW_DIR=/nfshome0/cmssw3
    export SCRAM_ARCH=slc6_amd64_gcc493
    export CMSSW_VERSION=CMSSW_8_0_22
fi

source $VO_CMS_SW_DIR/cmsset_default.sh
cd $VO_CMS_SW_DIR/$SCRAM_ARCH/cms/cmssw/$CMSSW_VERSION/
eval `scramv1 runtime -sh`
cd -

alias rateMon='python ShiftMonitorTool.py'
alias plotRates='python plotTriggerRates.py'
