#! /bin/bash
export SCRAM_ARCH=slc7_amd64_gcc630
export VO_CMS_SW_DIR=/opt/offline
source $VO_CMS_SW_DIR/cmsset_default.sh
cd $VO_CMS_SW_DIR/$SCRAM_ARCH/cms/cmssw/CMSSW_9_2_10/src
cmsenv
cd -
