#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail
IFS=$'\n\t\v'

HOST=$(hostname -f)

if [[ $HOST == *lxplus* ]]; then
    # lxplus machines
    export VO_CMS_SW_DIR=/afs/cern.ch/cms
    export SCRAM_ARCH=slc6_amd64_gcc493
    export CMSSW_VERSION=CMSSW_8_0_22
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

# When not on cms, lxplus or hilton machines we'll skip this phase,
# since scramv1 won't be available (the CMS build program)

if [[ -d ${VO_CMS_SW_DIR:-} ]]
then
    source $VO_CMS_SW_DIR/cmsset_default.sh
    cd $VO_CMS_SW_DIR/$SCRAM_ARCH/cms/cmssw/$CMSSW_VERSION/
    eval `scramv1 runtime -sh`
    cd -
fi

if [[ -f /opt/ratemon/venv/bin/python3 ]]; then
    export PATH="/opt/ratemon/venv/bin:$PATH"
fi

alias rateMon='python3 ShiftMonitorTool.py --dbConfigFile=dbConfig.yaml'
alias plotRates='python3 plotTriggerRates.py --dbConfigFile=dbConfig.yaml'
