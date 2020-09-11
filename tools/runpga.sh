#!/usr/bin/env bash
#
# Start a container that runs pgAdmin for the database you are
# interested in. After it runs, it will provide information
# about how to log into it.
#
# This script is idempotent. It will not re-create the pgAdmin
# container if it already exists.
#
# Usage:
#    $ runpga.sh <pg-container>
#    $ browser localhost:<port>  # <-- port is reported at the end of the run
#
set -e
: ${PGAEMAIL:="zzz@login.com"}
: ${PGAPASS:='password'}

# Make sure that the user specified a container.
PGNAME="$1"
if [ -z "$PGNAME" ] ; then
    printf '\x1b[31m'
    printf 'ERROR:%d %s\n' $LINENO "container not specified"
    CONTS=($(docker ps --filter name='.*pg' --format '{{ .Names }}' | sort -f))
    echo "There are ${#CONTS[@]} candidate containers: ${CONTS[@]}"
    if (( ${#CONTS[@]} )) ; then
        echo "Any of these commands will work."
        for CONT in ${CONTS[@]} ; do
            echo "   $0 ${CONT}"
        done
    else
        echo "There are no eligible containers, this will not work"
    fi
    printf '\x1b[0m'
    exit 1
fi

# Make sure the container exists.
CIDS=($(docker ps --filter "name=$PGNAME" --format '{{.ID}}'))
if (( ${#CIDS[@]} == 0 )) ; then
    printf '\x1b[31mERROR:%d %s\x1b[0m\n' $LINENO "container '$PGANAME' not found"
    exit 1
elif (( ${#CIDS[@]} > 1 )) ; then
    printf '\x1b[31mERROR:%d %s\x1b[0m\n' $LINENO "too many containers matching '$PGANAME' found: ${#CIDS[@]}"
    exit 1
fi

# Variables
CID=${CIDS[0]}
CPORT=$(docker inspect $CID | jq '.[] | .NetworkSettings.Ports."5432/tcp"[] | .HostPort' | tr -d '"')
PGANAME=$(echo -n "$PGNAME" | sed -e 's/..$/pa/')
PGAPORT=$(( CPORT + 1 ))
PGAPORT2=$(( PGAPORT + 1 ))

# Start the container if it is not already running.
CIDS=($(docker ps --filter "name=$PGANAME" --format '{{.ID}}'))
if (( ${#CIDS[@]} == 0 )) ; then
    # Make it idempotent.
    set -x
    docker run -d \
           -e PGADMIN_DEFAULT_EMAIL="$PGAEMAIL" \
           -e PGADMIN_DEFAULT_PASSWORD="$PGAPASS" \
           -h $PGANAME \
           --name $PGANAME \
           -p $PGAPORT:80 \
           -p $PGAPORT2:443 \
           dpage/pgadmin4
    { set +x; } 2>/dev/null
fi

# Summary
PGAGW=$(docker inspect $PGANAME | jq '.[]|.NetworkSettings.Networks.bridge.Gateway' | tr -d '"')
cat <<EOF

Summary
    Docker postgres ID:  $CID (port=$CPORT)
    Docker pgAdmin Host: $PGANAME

    pgAdmin URL:     http://localhost:${PGAPORT}
    pgAdmin Login:   $PGAEMAIL
    pgAdmin Passwod: $PGAPASS

    DB Server Host:  http://localhost:${PGAPORT}
    DB Username:     postgres
    DB Password:     password
    DB Address:      $PGAGW  (host localhost)
    DB Port:         $CPORT

    PSQL: docker exec -it $PGNAME psql -U postgres -d postgres

EOF
