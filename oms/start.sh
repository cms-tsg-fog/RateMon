#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail
IFS=$'\n\t\v'

sed -i -- "s|CMS_WBM_R|${DB_USER}|g" /aggregator.config.yml
sed -i -- "s|PASSWORD|${DB_PASS}|g" /aggregator.config.yml
java -jar /aggregator.jar server /aggregator.config.yml