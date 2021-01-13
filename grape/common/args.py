'''
Common args support.
'''
import argparse
from grape import __version__


CLI  = 'grape'
DEFAULT_NAME = 'grapex01'


def args_get_text(string: str):
    '''Convert to argparse section titles upper case to make things
    consistent.

    Args:
        string: The string from argparse.

    Returns:
        string: The string in uppercase if it matches known patterns.
    '''
    lookup = {
        'usage: ': 'USAGE:',
        'positional arguments': 'POSITIONAL ARGUMENTS',
        'optional arguments': 'OPTIONAL ARGUMENTS',
        'show this help message and exit': 'Show this help message and exit.\n ',
    }
    return lookup.get(string, string)


def add_common_args(parser: argparse.ArgumentParser, *enable: str):
    '''Add command line arguments that are common to all tools.

    Managine the arguments in a single place guarantees consistent
    arguments for all commands.

    Args:
        parser - The parser object.
        enable: The options to enable.
    '''
    if '-f' in enable:
        parser.add_argument('-f', '--file',
                            action='store',
                            type=str,
                            dest='fname',
                            default='',
                            metavar=('FILE'),
                            help='''\
The file name for load, save, import, export
and tree operations.

If not specified the default is the BASE.zip.
 ''')

    if '-g' in enable:
        parser.add_argument('-g', '--grxport',
                            action='store',
                            type=int,
                            default=4600,
                            help='''\
The grafana server host interface port.
This is the port that allows access
to the grafana visualization server
from the localhost.

The default is %(default)s.
 ''')

    if '-i' in enable:
        parser.add_argument('-i', '--indent',
                            action='store',
                            type=int,
                            default=3,
                            help='''\
Indent level.
Default is %(default)s.
 ''')

    if '-n' in enable:
        parser.add_argument('-n', '--name',
                            action='store',
                            type=str,
                            dest='base',
                            default=DEFAULT_NAME,
                            help='''\
The base name for the docker containers.

The default is %(default)s.

When the create operation is run the default
setting will create the following named
docker entities:
    %(default)sgr - grafana server docker container
    %(default)spg - postgres server docker container

It will also create a directory for
persistent postgres data storage in
    %(default)s
 ''')

    if '-p' in enable:
        parser.add_argument('-p', '--pgxport',
                            action='store',
                            type=int,
                            default=0,
                            help='''\
The postgres server host interface port.
This is the port that allows access
to the database from the localhost.

If it is not specified, it is one more
than the grafana port. Thus if the
grafana host interface port is specified
as 4400, the default postgres server
host interface port will be 4401.
 ''')

    if '-s' in enable:
        parser.add_argument('-s', '--sort',
                            action='store_true',
                            help='''\
Sort the tree data.
 ''')

    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='''\
Increase the level of verbosity.
Setting -v once sets logging.INFO.
Setting -v twice sets logging.DEBUG.
 ''')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s version {0}'.format(__version__),
                        help='''\
Show program's version number and exit.
 ''')

    if '-w' in enable:
        parser.add_argument('-w', '--wait',
                            action='store',
                            type=float,
                            default=60,
                            metavar=('SECONDS'),
                            help='''\
The maximum number of seconds to wait after
the containers have been created. It is used
by the create and load commands.

Default: %(default)s.
 ''')

    if '-x' in enable:
        parser.add_argument('-x', '--external-conf',
                            action='store',
                            dest='xconf',
                            metavar=('FILE'),
                            help='''\
YAML conf file that describes how
to access the external grafana server
for the import and export operation.

The contents of the YAML file look like
this:

  # Data to access an external grafana server.
  # If any fields are not present, then the user
  # will be prompted for them.
  url: 'https://official.grafana.server'
  username: 'bigbob'
  password: 'supersecret'

  # The passwords for each database can optionally
  # be specified. If they are not specified, then
  # the user will be prompted for them.
  # They cannot be imported automatically because
  # grafana filters them out.
  databases:
    - name: 'PostgreSQL'
      password: 'donttellanyone'
    - name: 'InfluxDB'
      password: 'topsecret!'
''')
