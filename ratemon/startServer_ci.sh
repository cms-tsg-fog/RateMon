#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail
IFS=$'\n\t\v'
cd `dirname "${BASH_SOURCE[0]:-$0}"`

if [[ -f ./venv/bin/python3 ]]; then
  ./venv/bin/python3 server.py
else
  python3 server.py
fi
