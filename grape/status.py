'''
Reports the status of grape based containers.

The containers are identified by the grape.type
label.

It then sets the datasource in the grafana server and creates a local
directory to save the postgres state.
'''
import argparse
import datetime
import os
import sys

import dateutil.parser
import docker

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info
from grape import __version__


def getopts() -> argparse.Namespace:
    '''
    Process the command line options.

    Returns:
       The argument namespace.
    '''
    argparse._ = args_get_text  # to capitalize help headers
    base = os.path.basename(sys.argv[0])
    usage = '\n {0} [OPTIONS]'.format(base)
    desc = 'DESCRIPTION:{0}'.format('\n  '.join(__doc__.split('\n')))
    epilog = '''
EXAMPLES:
    # ------------------------------------------------
    # Example 1: Help.
    # ------------------------------------------------
        $ {2} {0} -h

    # ------------------------------------------------
    # Example 2: List all of the grape related containers.
    # ------------------------------------------------
        $ {2} {0}

    # ------------------------------------------------
    # Example 3: List all of the grape related containers
    #            with headers.
    # ------------------------------------------------
        $ {2} {0} -v

VERSION:
   {1}
'''.format(base, __version__, CLI).strip()
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog.rstrip() + '\n ')
    add_common_args(parser)
    opts = parser.parse_args()
    return opts


class Column:
    '''
    The column.
    '''
    def __init__(self, name: str):
        self.m_name = name
        self.m_maxlen = len(name)
        self.m_rows = []

    def add(self, value: str):
        '''
        Add a row.
        '''
        self.m_maxlen = max(self.m_maxlen, len(value))
        self.m_rows.append(value)

    def size(self):
        '''
        Return the number of rows.
        '''
        return len(self.m_rows)

    def get(self, i: int, prefix: str = '  '):
        '''
        Returns the formatted value for a row.
        '''
        val = self.m_rows[i]
        fmt = f'{prefix}{val:<{self.m_maxlen}}'
        return fmt

    def hdr(self, prefix: str = '  '):
        '''
        Returns the formatted value for a row.
        '''
        val = self.m_name
        fmt = f'{prefix}{val:<{self.m_maxlen}}'
        return fmt


def get_elapsed_time(start_str: str) -> str:
    '''
    Get the elapsed time in seconds.
    '''
    start = dateutil.parser.parse(start_str)
    now = datetime.datetime.now(datetime.timezone.utc)
    elapsed = now - start
    tsecs = int(elapsed.total_seconds())
    days = divmod(tsecs, 86400)
    hours = divmod(days[1], 3600)
    minutes = divmod(hours[1], 60)
    seconds = divmod(minutes[1], 1)
    fmt = f'{hours[0]:>02}:{minutes[0]:>02}:{seconds[0]:>02}'
    if days[0] == 1:
        fmt = '1 day, ' + fmt
    elif days[0] > 1:
        fmt = f'{days[0]} days, ' + fmt
    return fmt


def main():
    'main'
    opts = getopts()
    initv(opts.verbose)
    info('status')
    client = docker.from_env()
    containers = client.containers.list(filters={'label': 'grape.type'})

    # Collect report rows for each column.
    cols = {'created': Column('Created'),
            'id': Column('Id'),
            'elapsed': Column('Elapsed'),
            'image': Column('Image'),
            'name': Column('Name'),
            'started': Column('Started'),
            'status': Column('Status'),
            'type': Column('Type'),
            'version': Column('Version')}
    for container in sorted(containers, key=lambda x: x.name.lower()):
        cols['created'].add(container.attrs['Created'])
        cols['id'].add(container.short_id)
        cols['image'].add(container.image.short_id)
        cols['name'].add(container.name)
        cols['status'].add(container.status)
        cols['type'].add(container.labels['grape.type'])
        cols['version'].add(container.labels['grape.version'])
        if container.status.lower() in ['running']:
            string = container.attrs['State']['StartedAt']
            elapsed = get_elapsed_time(string)
            cols['started'].add(string)
            cols['elapsed'].add(elapsed)
        else:
            cols['started'].add('')
            cols['elapsed'].add('')

    # Report the status.
    colnames = ['name', 'type', 'version', 'status', 'started', 'elapsed', 'id', 'image', 'created']
    ofp = sys.stdout
    if opts.verbose:
        if ofp == sys.stdout:
            ofp.write('\x1b[34m')
        for key in colnames:
            ofp.write(cols[key].hdr())
        if ofp == sys.stdout:
            ofp.write('\x1b[0m')
        ofp.write('\n')

    for i in range(cols['name'].size()):
        for key in colnames:
            ofp.write(cols[key].get(i))
        ofp.write('\n')

    info('done')
