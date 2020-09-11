#!/usr/bin/env python3
'''
CLI interface for the grape system.

This allows the user to only deal with a single interface.
'''
import os
import sys
from grape import __version__
from grape import create, delete, save, load, ximport, xexport


PROGRAM = os.path.splitext(os.path.basename(sys.argv[0]))[0]


def help0():
    '''
    Top level help.
    '''
    print(f'''\
Usage:
    {PROGRAM} [COMMAND] [OPTIONS]

Description:
    Welcome to the Grafana Model Development tool.

    This tool allows you to create, develop and maintain Grafana
    models in a local environment using docker containers.

    It can even import from and export to production setups.

    To use this tool you must have python3, pipenv and docker
    installed.

Commands:
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

Version:
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
    if not sys.argv[1:]:
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
    }
    arg = sys.argv[1].lower()
    if arg not in fmap:
        # look for partial matches.
        # this allows the user specify abbreviated
        # forms like "cr".
        for key in fmap:
            if key.startswith(arg):
                arg = key
                break
        if arg not in fmap:
            # if it still doesn't match, exit
            # stage left.
            sys.stderr.write('ERROR: unknown command, '
                             'please run this command for more '
                             f'information: {PROGRAM} help')
            sys.exit(1)
    sys.argv = sys.argv[1:]

    # Handle the special case where the user typed:
    #   COMMAND help
    if len(sys.argv) > 1 and sys.argv[1] == 'help':
        sys.argv[1] = '--help'

    # Run the command.
    fmap[arg]()
