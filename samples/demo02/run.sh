#!/usr/bin/env bash
#
# Create the demo01 grafana dev environment.
#
set -e

# Works on linux and mac
SDIR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)
PDIR=$(cd $(dirname $(dirname $SDIR)) && pwd)
PORT=4410
NAME='demo02'

printf '\x1b[35m'
cat <<EOF
# ================================================================
#
# Sample: $NAME
#
# ================================================================
EOF
printf '\x1b[0m'

#CIDS=($(docker ps --filter 'name=demo01' --format '{{.ID}}'))
cd $SDIR
rm -f $NAME.zip

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'initialize the environment'
set -x
(cd $PDIR && pipenv install)
{ set +x; } 2>/dev/null

# This is how the initial dataset was downloaded.
# The dataset is captured in the source code control system to
# make sure that the grafana display works as expected.
# If you re-enable this, you will need update the display
# time range.
#printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'download the raw csv data'
#set -x
#curl -L 'https://raw.githubusercontent.com/TheEconomist/covid-19-excess-deaths-tracker/master/output-data/excess-deaths/all_weekly_excess_deaths.csv' \
#-o all_weekly_excess_deaths.csv
#{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'create the local grafana service'
set -x
pipenv run grape --version
pipenv run grape delete -v -n $NAME -g $PORT
pipenv run grape create -v -n $NAME -g $PORT
{ set +x; } 2>/dev/null

# Use all_weekly_excess_deaths.csv
# The pipenv run python etl.py was added to fix a windows issue.
# This uses the upload-json-dashboard.sh tool to populate the dashboard.
printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'populate database tables and views'
set -x
pipenv run python etl.py all_weekly_excess_deaths.csv all_weekly_excess_deaths > demo02pg/mnt/all_weekly_excess_deaths.sql
docker exec -it ${NAME}pg psql -U postgres -d postgres -f /mnt/all_weekly_excess_deaths.sql
docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\d'
docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\dS+ all_weekly_excess_deaths'
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'upload the dashboard'
set -x
../../tools/upload-json-dashboard.sh -j dash.json -d "${NAME}pg" -g "http://localhost:${PORT}"
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'done'
cat <<EOF
You can now navigate to http://localhost:$PORT to see the demo
dashboard.
EOF
