#!/bin/bash
export SCRAM_ARCH=slc5_amd64_gcc462
export VO_CMS_SW_DIR=/nfshome0/cmssw2
source $VO_CMS_SW_DIR/cmsset_default.sh
cd $VO_CMS_SW_DIR/$SCRAM_ARCH/cms/cmssw/CMSSW_5_2_4/src
cmsenv
cd -
echo "Setting up CMSSW CVS environment"
export CVS_RSH="ssh"
export CVSROOT=":gserver:cmssw.cvs.cern.ch:/cvs/CMSSW"
echo "Getting certificate for CERN kerberos for $USER"
kinit "$USER@CERN.CH"

