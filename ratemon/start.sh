#!/usr/bin/env bash

# set -o errexit -o nounset -o pipefail
IFS=$'\n\t'
cd `dirname $0`

source ./set.sh
exec python2 ShiftMonitorTool.py --dbConfigFile=dbConfig.yaml