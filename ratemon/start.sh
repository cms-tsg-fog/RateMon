#!/usr/bin/env bash

# set -o errexit -o nounset -o pipefail
IFS=$'\n\t'
cd `dirname $0`

export https_proxy=http://cmsproxy.cms:3128/
export http_proxy=http://cmsproxy.cms:3128/
$*

source ./set.sh
exec python3 ShiftMonitorTool.py --configFile=/cmsnfsratemon/ratemon/.ShiftMonitor_config.json
