#!/usr/bin/env bash

if [[ "${BASH_SOURCE-}" == "$0" ]]; then
    echo "You must source this script: \$ source $0" >&2
    exit 33
fi

if [[ -f "$(pwd)/venv/bin/python3" ]]; then
    export PATH="$(pwd)/venv/bin:$PATH"
    export PYTHONPATH="$(pwd)/venv/lib/python3.6/site-packages:$(pwd)/venv/lib64/python3.6/site-packages"
fi

alias rateMon='python3 ShiftMonitorTool.py --dbConfigFile=dbConfig.yaml'
alias plotRates='python3 plotTriggerRates.py --dbConfigFile=dbConfig.yaml'
