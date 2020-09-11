#!/usr/bin/env bash
#
# Create the demo01 grafana dev environment.
#
set -e

# Works on linux and mac
SDIR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)
PDIR=$(cd $(dirname $(dirname $SDIR)) && pwd)
PORT=4500
NAME='import'

printf '\x1b[35m'
cat <<EOF
# ================================================================
#
# Sample: $NAME
#
# ================================================================
EOF
printf '\x1b[0m'
cd $SDIR
if [ ! -f "$NAME.yaml" ] ; then
   printf '\x1b[31mERROR:%d: %s\x1b[0m\n' $LINENO "file not found: $NAME.yaml, you must create it manually"
   exit 1
fi
rm -f $NAME.zip

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'initialize the environment'
set -x
(cd $PDIR && pipenv install)
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'create the local grafana service'
set -x
pipenv run grape --version
pipenv run grape delete -v -n $NAME -g $PORT
pipenv run grape create -v -n $NAME -g $PORT
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'import the external grafana service'
set -x
pipenv run grape import -v -n $NAME -g $PORT -x $NAME.yaml -f $NAME.zip
{ set +x; } 2>/dev/null

# For debugging only.
: ${DEBUG:=0}
if (( DEBUG )) ; then
    printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'view the import state'
    unzip -l $NAME.zip
    unzip -p $NAME.zip conf.json > conf.json
    cat conf.json | jq
    { set +x; } 2>/dev/null
    rm -f conf.json
fi

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'upload to the local grafana service'
set -x
pipenv run grape load -v -n $NAME -g $PORT -f $NAME.zip
{ set +x; } 2>/dev/null

printf '\x1b[35mINFO:%d: %s\x1b[0m\n' $LINENO 'done'
cat <<EOF
You can now navigate to http://localhost:$PORT to see the imported
dashboard.
EOF
