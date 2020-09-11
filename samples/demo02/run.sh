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
#curl -s -L 'https://raw.githubusercontent.com/TheEconomist/covid-19-excess-deaths-tracker/master/output-data/excess-deaths/all_weekly_excess_deaths.csv' \
#--out all_weekly_excess_deaths.csv
#{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'create the local grafana service'
set -x
pipenv run grape --version
pipenv run grape delete -v -n $NAME -g $PORT
pipenv run grape create -v -n $NAME -g $PORT
{ set +x; } 2>/dev/null

# Use all_weekly_excess_deaths.csv
printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'populate database tables and views'
set -x
pipenv run ./etl.py
docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\d'
#docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\dS+ all_weekly_excess_deaths'
#docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\dS+ all_weekly_excess_deaths_view'
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'grab the grafana configuration'
set -x
pipenv run grape save -v -n $NAME -g $PORT -f $NAME.zip
unzip -l $NAME.zip
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'update with the dashboard data'
set -x
unzip -l $NAME.zip
unzip -p $NAME.zip gr.json > gr.json
cp grafana.json gr.json
zip $NAME.zip gr.json
unzip -l $NAME.zip
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'upload the modified dashboard'
set -x
pipenv run grape load -v -n $NAME -g $PORT -f $NAME.zip
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'done'
cat <<EOF
You can now navigate to http://localhost:$PORT to see the demo
dashboard.
EOF
