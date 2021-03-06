#!/usr/bin/env bash
# shellcheck disable=SC2059
#
# Create the demo01 grafana dev environment.
#
set -e

# Works on linux and mac.
# There is some rather tricky quoting going on to
# make shellcheck happy.
SDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PDIR=$(cd "$(dirname "$(dirname "$SDIR")")" && pwd)
PORT=4410
NAME='demo02'
IFMT='\x1b[35mINFO:%d: %s\x1b[0m\n'

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
cd "$SDIR"
rm -f "$NAME.zip"

printf "$IFMT" $LINENO 'initialize the environment'
set -x
(cd "$PDIR" && pipenv install)
{ set +x; } 2>/dev/null

# This is how the initial dataset was downloaded.
# The dataset is captured in the source code control system to
# make sure that the grafana display works as expected.
# If you re-enable this, you will need update the display
# time range.
#printf "$IFMT" $LINENO 'download the raw csv data'
#set -x
#curl -L 'https://raw.githubusercontent.com/TheEconomist/covid-19-excess-deaths-tracker/master/output-data/excess-deaths/all_weekly_excess_deaths.csv' \
#-o all_weekly_excess_deaths.csv
#{ set +x; } 2>/dev/null

printf "$IFMT" $LINENO 'create the local grafana service'
set -x
pipenv run grape --version
pipenv run grape delete -v -n $NAME -g $PORT
pipenv run grape create -v -n $NAME -g $PORT
{ set +x; } 2>/dev/null

# Use all_weekly_excess_deaths.csv to generate the SQL data.
#
# This uses the csv2sql.py to analyze the CSV, figure out the types
# and generate the SQL commands which are then uploaded to the
# database using psql.
#
# Note that csv2sql.py is run twice. The first time it simply
# displays the table schema.
#
# Also note that the SQL is generated to the /mnt directory in the
# database container. This makes it possible for psql to find it.
#
# This is the data that is required by the dashboard.
printf "$IFMT" $LINENO 'show the SQL table schema'
set -x
pipenv run python ../../tools/csv2sql.py -H -c NA=0 -v all_weekly_excess_deaths.csv
{ set +x; } 2>/dev/null

printf "$IFMT" $LINENO 'create the SQL'
set -x
pipenv run python ../../tools/csv2sql.py -c NA=0 -v all_weekly_excess_deaths.csv -o demo02pg/mnt/all_weekly_excess_deaths.sql
{ set +x; } 2>/dev/null

printf "$IFMT" $LINENO 'populate database tables'
set -x
docker exec -it ${NAME}pg psql -U postgres -d postgres -f /mnt/all_weekly_excess_deaths.sql
{ set +x; } 2>/dev/null

# View what was created.
printf "$IFMT" $LINENO 'view the database tables'
set -x
docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\d'
docker exec -it ${NAME}pg psql -U postgres -d postgres -c '\dS+ all_weekly_excess_deaths'
{ set +x; } 2>/dev/null

# This uses the upload-json-dashboard.sh tool to populate the dashboard.
printf "$IFMT" $LINENO 'upload the dashboard'
set -x
../../tools/upload-json-dashboard.sh -f 0 -j dash.json -d "${NAME}pg" -g "http://localhost:${PORT}"
{ set +x; } 2>/dev/null
printf '\n'

# All done.
printf "$IFMT" $LINENO 'done'
cat <<EOF
You can now navigate to http://localhost:$PORT to see the demo
dashboard.
EOF
