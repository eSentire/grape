#!/usr/bin/env bash
#
# This can be customized from the command line
# by setting the variable values like this:
#
#   $ ./grape-upload-json-dashboard.sh -j external.json -d mypg -g 6300
#
# Help is available, by specifying the -h option.
#
# Note that you can run grape status -v to see the available
# servers.
#
# This script was linted by shellcheck.

# ================================================================
# Functions
# ================================================================
function _help() {
    cat <<EOF
USAGE
    $0 -h

DESCRIPTION
    Uploads a local dashboard JSON file to another Grafana server.

    The upload is limited to servers with simple authentication based
    on a username and password.

    The local dashboard JSON file is creatined by exporting the
    dashboard from the Grafana UI with the "Export for sharing
    externally" checkbox checked.

    This script is useful for transferring dashboards from one server
    to another which is handy in cases where there is the development
    server is separate from the release server.

    Although the same function can be accomplished in the UI, this
    script allows updates to be automated in a build.

    This script requires that "curl" is installed.

OPTIONS
    -d NAME     The Grafana data source name.

    -g PORT     The grafan URL prefix.
                An example might be something like:
		    http://localhost:6300

    -h          This help message.

    -j FILE     The dashboard JSON file to upload.

    -n          Do not use simple authentication.
     		The user is expected to use the -x option to add extra
		data.

    -p PASSWORD The Grafana password.
                Normally you would want to use -P to prompt with no
		echo.

    -P          Prompt for the Grafana password.

    -u USERNAME The Grafana username.

    -v          Increase the level of verbosity.

    -x STRING   Add extra arguments.

EXAMPLES
    # Example 1.
    #    Get help
    \$ $0 -h

    # Example 2.
    #    Upload to a grape grafana server.
    #    The -u and -p options do not need to be specified.
    #    Pipe the curl output in jq to make it more readable.
    #    They are only shown for clarity.
    \$ grape server -v  # find the port
    \$ $0 -u admin -p admin -g http://localhost:6400 -j x.json -d mypg | jq

    # Example 3.
    #    Upload to a grape grafana server.
    #    Pipe the curl output in jq to make it more readable.
    #    Use your own auth.
    \$ grape server -v  # find the port
    \$ $0 -g http://localhost:6400 -j x.json -d mypg -n -x '-u admin:admin' | jq

EOF
    exit 0
}

# ================================================================
# Command line argument processing.
# ================================================================
set -e
DASH_AUTH=1
DASH_USERNAME='admin'
DASH_PASSWORD='admin'
DASH_JSON=
DASH_DS=
DASH_URL=
DASH_EXTRA=()
VERBOSE=0

while getopts ':hd:g:j:np:Pu:vx:' options ; do
    case ${options} in
	h )
	    _help
	    ;;
	d )
	    DASH_DS=${OPTARG}
	    ;;
	g )
	    DASH_URL=${OPTARG}
	    ;;
	j )
	    DASH_JSON=${OPTARG}
	    ;;
	n )
	    DASH_AUTH=0
	    ;;
	p )
	    DASH_PASSWORD=${OPTARG}
	    ;;
	P )
	    read -r -p 'Password: ' -s DASH_PASSWORD
	    printf '\n'
	    ;;
	u )
	    DASH_USERNAME=${OPTARG}
	    ;;
	v )
	    VERBOSE=$(( VERBOSE + 1 ))
	    ;;
	x )
	    DASH_EXTRA=("${OPTARG//[ ]/}")
	    ;;
	'?' )
	    printf '\x1b[31mERROR:%d: %s\x1b[0m\n' $LINENO "Invalid Option: -$OPTARG" 1>&2
	    exit 1
	    ;;
    esac
done
shift $((OPTIND -1))

# ================================================================
# Check required options.
# ================================================================
# need bash 4 or later
BASH_MAJOR=$(echo "$BASH_VERSION" | awk -F. '{print $1}')
if (( BASH_MAJOR < 4 )) ; then
    # Need 4 or later to support "declare -A".
    printf '\x1b[31mERROR:%d: %s\x1b[0m\n' $LINENO "This version of bash is too old: $BASH_VERSION" 1>&2
    exit 1
fi

ERRCNT=0
declare -A ROPTS=( ['-d']="$DASH_DS" ['-j']="$DASH_JSON" ['-g']="$DASH_URL")
for RKEY in "${!ROPTS[@]}" ; do
    RVAL=${ROPTS[$RKEY]}
    if [ -z "$RVAL" ] ; then
	printf '\x1b[31mERROR:%d: %s\x1b[0m\n' \
	       $LINENO \
	       "Missing required option: '$RKEY'. See the help (-h) for more information." \
	       1>&2
	ERRCNT=$(( ERRCNT += 1))
    fi
done
if (( ERRCNT )) ; then exit 1 ; fi

# ================================================================
# Report the setup.
# ================================================================
if (( VERBOSE )) ; then
    cat <<EOF
Setup
    DASH_AUTH     : $DASH_AUTH
    DASH_DS       : $DASH_DS
    DASH_JSON     : $DASH_JSON
    DASH_URL      : $DASH_URL
    DASH_USERNAME : $DASH_USERNAME
    DASH_EXTRA    : ${DASH_EXTRA[@]}
    VERBOSE       : $VERBOSE
EOF
fi

# ================================================================
# Create the JSON with the variables set.
#
# Note the the "inputs" record MUST appear before the "dashboard"
# record because the import operation picks up the first input
# specification and ignores the reas.
#
# This is relevant because the inputs described below references the
# correct the datasource where are the __inputs in the dashboard
# record reference the old, incorrect datasource.
# ================================================================
cat >x.json <<EOF
{
  "inputs": [{
    "name": "DS_XDIOXPG",
    "type": "datasource",
    "pluginId": "postgres",
    "value": "${DASH_DS}"
  }],
  "dashboard": $(cat "${DASH_JSON}"),
  "overwrite": true
}
EOF

# ================================================================
# Upload to the Grafana server.
# ================================================================
if (( DASH_AUTH )) ; then
    AUTH=('-u' "${DASH_USERNAME}:${DASH_PASSWORD}")
else
    AUTH=()
fi
if (( VERBOSE )) ; then set -x ; fi
curl "${AUTH[@]}" "${DASH_EXTRA[@]}" \
     -s \
     -k \
     -X POST \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     -d @x.json \
     "${DASH_URL}"/api/dashboards/import
if (( VERBOSE )) ; then { set +x; } 2>/dev/null ; fi
