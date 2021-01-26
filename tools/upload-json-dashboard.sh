#!/usr/bin/env bash
# shellcheck disable=SC2059,SC2207
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

       		This option can be specified multiple times
		along with -n and -d for multiple data sources.

    -f INT      The Grafana dashboard parent folder id.
                If not specified, the top level is assumed.

    -g PORT     The Grafana URL prefix.
                An example might be something like:
                    http://localhost:6300

    -h          This help message.

    -i NAME     The plugin id.

       		This option can be specified multiple times
		along with -n and -d for multiple data sources.

                The default is 'postgres'.

    -j FILE     The dashboard JSON file to upload.

    -k          Keep the temporary wrapper JSON.
    		This is mainly used for debugging.

    -n NAME     The name of the Grafana datasource variable.

       		This option can be specified multiple times
		along with -n and -d for multiple data sources.

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
    #    Upload a dashboard to a grape Grafana server.
    #    The -u and -p options do not need to be specified.
    #    Pipe the curl output in jq to make it more readable.
    #    They are only shown for clarity.
    \$ grape server -v  # find the port
    \$ $0 -u admin -p admin -g http://localhost:6400 -j x.json -n DS_MYDB -d mypg | jq

    # Example 3.
    #    Upload a dashboard to a grape Grafana server.
    #    Pipe the curl output in jq to make it more readable.
    #    Use your own auth.
    \$ grape server -v  # find the port
    \$ $0 -g http://localhost:6400 -j x.json -n DS_MYDB -d mypg -N -x '-u admin:admin' | jq

    # Example 4.
    #    Upload a dashboard to a grape Grafana server with multiple
    #    datasources.
    #
    #    Multiple data sources are specified by setting a 3-tuple
    #    of options for each dataset that describes the variable (-n),
    #    the new data source (-d) and the input plugin (-i).
    #
    #    Note that the same database can be used for multiple
    #    variables.
    #
    #    Also note that if -i is not specified at all, it defaults
    #    to postgres.
    \$ grape server -v  # find the port
    \$ $0 -g http://localhost:6400 -j x.json -N -x '-u admin:admin' \\
          -n DS_MYDB  -d mypg  -i postgres \\
          -n DS_MYDB2 -d mypg2 -i postgres \\
          -n DS_MYDB3 -d mypg3 -i postgres \\
          -n DS_MYDB4 -d mypg  -i postgres \\
	  | jq


    # Example 5.
    #    Upload a dashboard to a grape Grafana server with multiple
    #    datasources. Use the minimum number of entries for the tuple.
    #
    #    Note that for this to work properly, the datasets must be
    #    specified in the same order that they appear in the JSON
    #    "__inputs" record for the dashboard because it fills in
    #    the values for the -n and -i.
    \$ grape server -v  # find the port
    \$ $0 -g http://localhost:6400 -j x.json -N -x '-u admin:admin' \\
          -d mypg   \\
          -d mypg2  \\
          -d mypg3  \\
          -d mypg   \\
	  | jq

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
DASH_DS=()
DASH_EXTRA_CURL=()
DASH_FOLDER=0
DASH_JSON=
DASH_NAME=()
DASH_PLUGIN=()
DASH_PASSWORD='admin'
DASH_USERNAME='admin'
DASH_URL=
KEEP=0
VERBOSE=0
WRAP_JSON=/tmp/wrap-$$.json

while getopts ':f:hd:g:i:j:kn:Np:Pu:vx:' options ; do
    case ${options} in
        h )
            _help
            ;;
        d )
            DASH_DS+=("${OPTARG}")
            ;;
        f )
            DASH_FOLDER=${OPTARG}
            ;;
        g )
            DASH_URL=${OPTARG}
            ;;
        i )
            DASH_PLUGIN+=("${OPTARG}")
            ;;
        j )
            DASH_JSON=${OPTARG}
            ;;
        k )
            KEEP=1
            ;;
        n )
            DASH_NAME+=("${OPTARG}")
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
# expect bash 4 or later
BASH_MAJOR=$(echo "$BASH_VERSION" | awk -F. '{print $1}')
if (( BASH_MAJOR < 4 )) ; then
    # Need 4 or later to support "declare -A".
    printf "$ERRFMT" $LINENO "this version of bash is too old, must be 4 or later: $BASH_VERSION" 1>&2
    exit 1
fi

NUM_DASH_DS=${#DASH_DS[@]}
NUM_DASH_NAME=${#DASH_NAME[@]}
NUM_DASH_PLUGIN=${#DASH_PLUGIN[@]}

if [ -z "${DASH_JSON}" ] ; then
    printf "$ERRFMT" $LINENO "JSON dashboard file not specified (-j)" 1>&2
    exit 1
fi

if [ ! -f "${DASH_JSON}" ] ; then
    printf "$ERRFMT" $LINENO "JSON dashboard file does not exist (-j): ${DASH_JSON}" 1>&2
    exit 1
fi

if (( NUM_DASH_DS == 0 )) ; then
    printf "$ERRFMT" $LINENO "the -d option must be specified at least once" 1>&2
    exit 1
fi

if (( NUM_DASH_NAME == 0 )) ; then
    # If -n is not specified and jq is present, get all of the names.
    if jq --version &>/dev/null ; then
	DASH_NAME=( $(jq -c '.__inputs[].name' "$DASH_JSON" | awk -F'"' '{print $2}') )
	NUM_DASH_NAME=${#DASH_NAME[@]}
    fi
fi

if (( NUM_DASH_PLUGIN == 0 )) ; then
    # If -i is not specified and jq is present, get all of the plugins.
    if jq --version &>/dev/null ; then
	DASH_PLUGIN=( $(jq -c '.__inputs[].pluginId' "$DASH_JSON" | awk -F'"' '{print $2}') )
	NUM_DASH_PLUGIN=${#DASH_PLUGIN[@]}
    fi
fi

if (( NUM_DASH_DS != NUM_DASH_NAME )) ; then
    printf "$ERRFMT" $LINENO "the number -n and -d entries must be exactly the same" 1>&2
    if jq --version &>/dev/null ; then
	jq -c '.__inputs[]| {"-n": .name, "-d": .label, "-i": .pluginId}' "${DASH_JSON}"
    fi
    exit 1
fi

if (( NUM_DASH_DS != NUM_DASH_PLUGIN )) ; then
    printf "$ERRFMT" $LINENO "the number -n and -i entries must be exactly the same" 1>&2
    if jq --version &>/dev/null ; then
	jq -c '.__inputs[]| {"-n": .name, "-d": .label, "-i": .pluginId}' "${DASH_JSON}"
    fi
    exit 1
fi

if [ -z "$DASH_URL" ] ; then
    printf "$ERRFMT" $LINENO "grafana server URL not specified (-g)" 1>&2
    exit 1
fi

# ================================================================
# Report the setup.
# ================================================================
if (( VERBOSE )) ; then
    cat <<EOF
Setup
    BASH_VERSION    : $BASH_VERSION
    DASH_AUTH       : $DASH_AUTH
    DASH_DS         : $NUM_DASH_DS ${DASH_DS[@]}
    DASH_FOLDER     : $DASH_FOLDER
    DASH_JSON       : $DASH_JSON
    DASH_NAME       : $NUM_DASH_JSON ${DASH_NAME[@]}
    DASH_PLUGIN     : $NUM_DASH_PLUGIN ${DASH_PLUGIN[@]}
    DASH_URL        : $DASH_URL
    DASH_USERNAME   : $DASH_USERNAME
    DASH_EXTRA_CURL : ${DASH_EXTRA_CURL[@]}
    KEEP            : $KEEP
    VERBOSE         : $VERBOSE
    WRAP_JSON       : $WRAP_JSON
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
printf '{\n  "inputs": [' > "${WRAP_JSON}"
for((i=0; i<NUM_DASH_DS; i++)) ; do
    if (( i )) ; then
	printf '    ,\n' >>"${WRAP_JSON}"
    fi
    cat >>"${WRAP_JSON}" <<EOF
    {
      "name": "${DASH_NAME[$i]}",
      "type": "datasource",
      "pluginId": "${DASH_PLUGIN[$i]}",
      "value": "${DASH_DS[$i]}"
    }
EOF
done
cat >>"${WRAP_JSON}" <<EOF
  ],
  "dashboard": $(cat "${DASH_JSON}"),
  "folderId": ${DASH_FOLDER},
  "overwrite": true
}
EOF
#cat >"${WRAP_JSON}" <<EOF
#{
#  "inputs": [{
#    "name": "${DASH_NAME}",
#    "type": "datasource",
#    "pluginId": "${DASH_PLUGIN}",
#    "value": "${DASH_DS}"
#  }],
#  "dashboard": $(cat "${DASH_JSON}"),
#  "folderId": ${DASH_FOLDER},
#  "overwrite": true
#}
#EOF

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
     --fail \
     -s \
     -k \
     -X POST \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     -d @"${WRAP_JSON}" \
     "${DASH_URL}"/api/dashboards/import
if (( VERBOSE )) ; then { set +x; } 2>/dev/null ; fi

# ================================================================
# Clean up.
# ================================================================
if (( KEEP )) ; then
    rm -f "${WRAP_JSON}"
fi
