#!/usr/bin/env python3
'''
CLI interface for the grape system.

This allows the user to only deal with a single interface.
'''
import os
import sys
from grape import __version__
from grape import create, delete, save, load, ximport, xexport, status, tree


PROGRAM = os.path.splitext(os.path.basename(sys.argv[0]))[0]


def help0():
    '''
    Top level help.
    '''
    print(f'''\
USAGE:
    {PROGRAM} [COMMAND] [OPTIONS]

DESCRIPTION:
    Welcome to the Grafana Model Development tool.

    This tool allows you to create, develop and maintain Grafana
    models in a local environment using docker containers.

    It can even import from and export to production setups.

    To use this tool you must have python3, pipenv and docker
    installed.

COMMANDS:
    Each command has its own help and examples. You get that help by
    specifying "COMMAND help" or "COMMAND -h" or "COMMAND --help".

    The following commands are available:

    help        This message.

    version     The system version.

    create      The create operation creates a docker container
                for grafana and a docker container for postgres.
                It then sets the datasource in the grafana server
                and creates a local directory to save the postgres
                state.

    delete      The delete operation deletes all artifacts created
                by the create operation.

    save        The save operation captures the specified
                visualization environment in a zip file.
                It is what you use to capture changes for
                future use.

    load        The load operation updates the visualization
                environment from a saved state (zip file).

    import      The import operation captures an external
                grafana environment for the purposes of
                experimenting or working locally.

                It imports rhe datasources without passwords
                because grafana never exports passwords which
                means that they have to be updated manually
                after the import operation completes or by
                specifying the passwords in the associated
                conf file. It does not import databases.

                The import operation creates a zip file that
                can be used by a load operation. It also
                requires a conf file that is specified by
                the -x option.

    export      The export operation exports a grafana
                visualization service to an external
                source. It requires a zip file from a
                save operation (-f) and a YAML file that
                describes the external source (-x).

    status      Report the status of grape related
                related containers by look for specific
                labels that were added when the containers
                were started.

    tree        Print a tree view of the datasources, folders
                and dashboards in a grafana server.

VERSION:
    {PROGRAM}-{__version__}
''')
    sys.exit(0)


def version():
    '''
    Print the version.
    '''
    print(f'{PROGRAM}-{__version__}')
    sys.exit(0)


def main():
    'main'
    if len(sys.argv) < 2:
        # No arguments brings up the help.
        help0()

    # Create the command map.
    fmap = {
        # help
        'help': help0,
        '--help': help0,
        '-h': help0,

        # version
        'version': version,
        '--version': version,
        '-V': version,

        # commands
        'create': create.main,
        'delete': delete.main,
        'save': save.main,
        'load': load.main,
        'import': ximport.main,
        'export': xexport.main,
        'status': status.main,
        'tree': tree.main,
    }
    if sys.argv[1] == '-V':
        # Special case handling because case matters.
        fct = fmap[sys.argv[1]]
    else:
        arg = sys.argv[1].lower()
        if arg not in fmap:
            # look for partial matches.
            # this allows the user specify abbreviated
            # forms like "cr".
            for key in fmap:
                if key.startswith(arg) and not arg.startswith('-'):
                    arg = key
                    break
            if arg not in fmap:
                # if it still doesn't match, exit
                # stage left.
                sys.stderr.write(f'ERROR: unknown command "{arg}", '
                                 'please run this command for more '
                                 f'information: {PROGRAM} help')
                sys.exit(1)
        fct = fmap[arg]
    sys.argv = sys.argv[1:]

    # Handle the special case where the user typed:
    #   COMMAND (help|version)
    if len(sys.argv) > 1:
        if sys.argv[1] == 'help':
            # user typed: COMMAND help
            sys.argv[1] = '--help'
        elif sys.argv[1] == 'version':
            # user typed: COMMAND version
            sys.argv[1] = '--version'
        elif sys.argv[0] == 'help':
            if not sys.argv[1].startswith('-'):
                # user typed: help COMMAND
                sys.argv[0] = sys.argv[1]
                sys.argv[1] = '--help'

    # Run the command.
    fct()
