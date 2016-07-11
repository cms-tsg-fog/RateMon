#! /bin/bash
export SCRAM_ARCH=slc5_amd64_gcc462
export VO_CMS_SW_DIR=/nfshome0/cmssw2
source $VO_CMS_SW_DIR/cmsset_default.sh
cd $VO_CMS_SW_DIR/$SCRAM_ARCH/cms/cmssw/CMSSW_5_2_6/src
cmsenv
cd -
alias rateMon='python ShiftMonitorTool.py'
alias plotRates='python plotTriggerRates.py'