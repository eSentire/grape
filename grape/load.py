'''
The load operation updates the specificed grafana modeling environment
from a saved state (zip file).
'''
import argparse
import os
import sys

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info
from grape.common.conf import get_conf
from grape.common.gr import load_all as gr_load
from grape.common.pg import load as pg_load
from grape.common.zip import load as zp_load
from grape.create import create
from grape.delete import delete
from grape import __version__


def getopts() -> argparse.Namespace:
    '''Process the command line options.

    Returns:
       opts: The argument namespace.
    '''
    argparse._ = args_get_text  # type: ignore
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
    # Example 2: Load an existing zip file.
    # ------------------------------------------------
        $ {2} {0} -v -n {3} -g 4700 -f example.zip

    # ------------------------------------------------
    # Example 3: Modify the contents of an existing zip
    #            file then load it.
    # ------------------------------------------------
        $ ## See whats in the zip file.
        $ unzip -l example.zip

        $ ## Extract the contents.
        $ unzip -p example.zip conf.json > conf.json
        $ unzip -p example.zip gr.json > gr.json
        $ unzip -p example.zip pg.sql > pg.sql

        $ ## Re-constitute the zip file and load it.
        $ zip example.zip conf.json gr.json pg.sql
        $ unzip -l example.zip
        $ {2} {0} -v -n {3} -g 4700 -f example.zip

VERSION:
   {1}
'''.format(base, __version__, CLI, DEFAULT_NAME).strip()
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog.rstrip() + '\n ')
    add_common_args(parser)
    opts = parser.parse_args()
    return opts


def load(conf: dict, wait: float):
    '''Load the servers.

    Load the current grafana and postgres servers from
    an archive.

    The easiest implementation is to delete the docker
    containers, re-create them and then populate them.
    The alternative would be to delete the individual
    components of each service which is a challenge.

    Args:
        conf: The configuration data.
        wait: The container create wait time.
    '''
    result = zp_load(conf)
    zconf = result['conf']
    zgr = result['gr']
    sql = result['pg']

    # Special case handling for import an zip file.
    if 'import' in zconf:
        assert 'import' not in conf
        conf['import'] = zconf['import']

    delete(conf)
    create(conf, wait)
    gr_load(conf, zgr)
    pg_load(conf, sql)


def main():
    '''Load command main.

    This is the command line entry point for the load command.
    '''
    opts = getopts()
    initv(opts.verbose)
    info(f'load {opts.fname} into {opts.base}')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    load(conf, opts.wait)
    info('done')
