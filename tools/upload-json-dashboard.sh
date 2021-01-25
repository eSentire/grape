#!/usr/bin/env bash
# shellcheck disable=SC2059
#
# This can be customized from the command line by setting the variable
# values like this if jq is installed.
#
#   $ ./upload-json-dashboard.sh -j external.json -d mypg -g 6300
#
# Or like this if it isn't.
#
#   $ ./upload-json-dashboard.sh -j external.json -d mypg -g 6300 -n DS_EXTERNALPG
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
    Uploads a dashboard JSON file to a Grafana server.

    The upload is limited to servers with simple authentication based
    on a username and password unless you override it using "-x" and
    "-n".

    The local dashboard JSON file is created by exporting the
    dashboard from the Grafana UI with the "Export for sharing
    externally" checkbox checked.

    This script is useful for transferring dashboards from one server
    to another.

    Although the same function can be accomplished in the UI, this
    script allows updates to be automated from the command line.

    This script requires that "curl" is installed.

OPTIONS
    -d NAME     The Grafana data source name.

    -f INT      The Grafana dashboard parent folder id.
                If not specified, the top level is assumed.

    -g PORT     The Grafana URL prefix.
                An example might be something like:
                    http://localhost:6300

    -h          This help message.

    -i NAME     The plugin id.
                The default is 'postgres'

    -j FILE     The dashboard JSON file to upload.

    -n NAME     The name of the Grafana datasource variable.
                If not specified, the name will be extracted
                from the JSON file if the jq program is present.

    -N          Do not use simple authentication.
                The user is expected to use the -x option to add extra
                data.

    -p PASSWORD The Grafana password.
                Normally you would want to use -P to prompt with no
                echo.

    -P          Prompt for the Grafana password.

    -u USERNAME The Grafana username.

    -v          Increase the level of verbosity.

    -x STRING   Add extra curl arguments.

EXAMPLES
    # Example 1.
    #    Get help
    \$ $0 -h

    # Example 2.
    #    Upload to a grape Grafana server.
    #    The -u and -p options do not need to be specified.
    #    Pipe the curl output in jq to make it more readable.
    #    They are only shown for clarity.
    \$ grape server -v  # find the port
    \$ $0 -u admin -p admin -g http://localhost:6400 -j x.json -d mypg -n DS_MYDB | jq

    # Example 3.
    #    Upload to a grape Grafana server.
    #    Pipe the curl output in jq to make it more readable.
    #    Use your own auth.
    \$ grape server -v  # find the port
    \$ $0 -g http://localhost:6400 -j x.json -d mypg -N -x '-u admin:admin' -n DS_MYDB | jq

EOF
    exit 0
}

# ================================================================
# Constants.
# ================================================================
ERRFMT='\x1b[31mERROR:%d: %s\x1b[0m\n'

# ================================================================
# Command line argument processing.
# ================================================================
set -e
DASH_AUTH=1
DASH_DS=
DASH_EXTRA_CURL=()
DASH_FOLDER=0
DASH_JSON=
DASH_NAME=
DASH_PLUGIN='postgres'
DASH_PASSWORD='admin'
DASH_USERNAME='admin'
DASH_URL=
VERBOSE=0

while getopts ':f:hd:g:i:j:n:Np:Pu:vx:' options ; do
    case ${options} in
        h )
            _help
            ;;
        d )
            DASH_DS=${OPTARG}
            ;;
        f )
            DASH_FOLDER=${OPTARG}
            ;;
        g )
            DASH_URL=${OPTARG}
            ;;
        i )
            DASH_PLUGIN=${OPTARG}
            ;;
        j )
            DASH_JSON=${OPTARG}
            ;;
        n )
            DASH_NAME=${OPTARG}
            ;;
        N )
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
            DASH_EXTRA_CURL=("${OPTARG//[ ]/}")
            ;;
        '?' )
            printf "$ERRFMT" $LINENO "invalid option: -$OPTARG" 1>&2
            exit 1
            ;;
    esac
done
shift $((OPTIND -1))

# ================================================================
# Check required options.
# ================================================================
if [ -n "$DASH_JSON" ] && [ -z "$DASH_NAME" ] ; then
    if jq --version &>/dev/null ; then
        # If jq is available, extract the variable name.
        DASH_NAME=$(jq '.__inputs[0].name' "$DASH_JSON" | awk -F'"' '{print $2}')
    fi
fi
# need bash 4 or later
BASH_MAJOR=$(echo "$BASH_VERSION" | awk -F. '{print $1}')
if (( BASH_MAJOR < 4 )) ; then
    # Need 4 or later to support "declare -A".
    printf "$ERRFMT" $LINENO "this version of bash is too old, must be 4 or later: $BASH_VERSION" 1>&2
    exit 1
fi

ERRCNT=0
declare -A ROPTS=( ['-d']="$DASH_DS" ['-j']="$DASH_JSON" ['-g']="$DASH_URL" ['-n']="$DASH_NAME")
for RKEY in "${!ROPTS[@]}" ; do
    RVAL=${ROPTS[$RKEY]}
    if [ -z "$RVAL" ] ; then
        printf "$ERRFMT" \
               $LINENO \
               "missing required option: '$RKEY', see the help (-h) for more information" \
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
    BASH_VERSION    : $BASH_VERSION
    DASH_AUTH       : $DASH_AUTH
    DASH_DS         : $DASH_DS
    DASH_FOLDER     : $DASH_FOLDER
    DASH_JSON       : $DASH_JSON
    DASH_NAME       : $DASH_NAME
    DASH_URL        : $DASH_URL
    DASH_USERNAME   : $DASH_USERNAME
    DASH_EXTRA_CURL : ${DASH_EXTRA_CURL[@]}
    VERBOSE         : $VERBOSE
EOF
fi

# ================================================================
# Other prerequisite checks.
# ================================================================
if [ ! -f "$DASH_JSON" ] ; then
    printf "$ERRFMT" $LINENO "file does not exist: $DASH_JSON" 1>&2
    exit 1
fi
if ! grep '"__inputs"' "$DASH_JSON" &>/dev/null ; then
    printf "$ERRFMT" $LINENO "missing required record '__inputs' in $DASH_JSON" 1>&2
    exit 1
fi
if ! curl --version &>/dev/null ; then
    printf "$ERRFMT" $LINENO "curl is not installed, cannot continue" 1>&2
    exit 1
fi

# ================================================================
# Create the JSON with the variables set.
#
# Note the the "inputs" record MUST appear before the "dashboard"
# record because the import operation picks up the first input
# specification and ignores the rest.
#
# This is relevant because there are two sources of external variable
# definitions in the dashboard description. The first is the "inputs"
# record at the top level (shown below) and the other is the
# "__inputs" record under each dashboard (not shown) which is created
# by Grafana when it exports the dashboard. The top level definition
# overrides all subsequent low level definitions which is why it must
# appear first.
# ================================================================
cat >x.json <<EOF
{
  "inputs": [{
    "name": "${DASH_NAME}",
    "type": "datasource",
    "pluginId": "${DASH_PLUGIN}",
    "value": "${DASH_DS}"
  }],
  "dashboard": $(cat "${DASH_JSON}"),
  "folderId": ${DASH_FOLDER},
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
curl "${AUTH[@]}" "${DASH_EXTRA_CURL[@]}" \
     -s \
     -k \
     -X POST \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     -d @x.json \
     "${DASH_URL}"/api/dashboards/import
if (( VERBOSE )) ; then { set +x; } 2>/dev/null ; fi
