#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail
IFS=$'\n\t\v'
cd `dirname "${BASH_SOURCE[0]:-$0}"`

# For use in CI environments
# checks environment variables for any DB passwords
# and patches dbConfig.yaml before starting server.py

# if complete config is given, replace config
if [[ -n "${DBCONFIG:-}" ]]; then
  echo "$DBCONFIG" > dbConfig.yaml
fi

# change individual username=password env variables
for s in `cat dbConfig.yaml | grep "'user': " | sed -E "s|  'user': '(.*)'|\1|"`; do
  v=${s^^}  # username in uppercase
  p=${!v:-} # get variable by name $v
  if [[ -n "$p" ]]; then
    echo "injecting password for $s"
    sed -i "/^  'user': '$s'/{:1;/  'passwd': .*$/!{N;b 1}
     s/.*/  'user': '$s'\n  'passwd': '$p'/g}" dbConfig.yaml
  fi
done


if [[ -f ./venv/bin/python3 ]]; then
  ./venv/bin/python3 server.py
else
  python3 server.py
fi
