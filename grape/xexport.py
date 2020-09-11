'''
The export operation exports a grafana visualization service to an
external source.

It requires a zip file from a save operation (-f) and a YAML file that
describes the external source (-x).

The YAML file that describes the external access cannot be created
automatically because grafana does not export passwords.
'''
import argparse
import os
import sys

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info
from grape.common.gr import load_all as gr_load_all
from grape.common.conf import get_conf
from grape.common.xconf import get_xconf
from grape.common.zip import load as zp_load
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
        $ {3} {0} -h

    # ------------------------------------------------
    # Example 2. Export to an external grafana system.
    # ------------------------------------------------
        $ edit export.yaml
        $ {2} {0} -v -b {3} -g 4900 -f export.zip
        $ {2} {0} -v -b {3} -g 4900 -f export.zip -x export.yaml

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


def xexport(conf: dict, xconf: str):
    '''
    Export to an external grafana server system.

    This is meant to be the inverse operation to
    the importing.

    This operation requires an import conf file
    as well as a load zip file.

    Args:
        conf - the configuration
        xconf - the external conf
    '''
    info('export')

    # Collect the data in the import yaml file.
    # Create a password map so that the passwords
    # for the databases can be restored.
    iconf = get_xconf(xconf)
    pmap = {}
    if 'databases' in iconf:
        for database in iconf['databases']:
            for key in database:
                # Allow the user to specify an arbitrary key like
                # 'name' or 'database'.
                if key == 'password':
                    continue
                name = database[key]
                password = database['password']
                if key not in pmap:
                    pmap[key] = {}
                pmap[key][name] = password

    # Collect the data in the save zip file.
    result = zp_load(conf)
    zgr = result['gr']

    # Fix the passwords in zgr.
    # Everything else s/b fine.
    if pmap:
        for rec in zgr['datasources']:
            if not rec['password']:
                # The password is not defined.
                # If it is defined, it is not changed because the user
                # changed it manually by editing the zip contents.
                for key in pmap:
                    if key not in rec:
                        continue
                    name = rec[key]
                    if name not in pmap[key]:
                        continue
                    password = pmap[key][name]
                    rec['password']  = password

    # Fix the conf to write to the external source.
    conf['gr']['username'] = iconf['username']
    conf['gr']['password'] = iconf['password']
    conf['gr']['url'] = iconf['url']

    # Remove the local datasource.
    name = conf['pg']['name']
    if name in zgr['datasources']:
        info(f'removing the local database datasource: {name}')
        del zgr['datasources'][name]

    # Write the grafana configuration out.
    gr_load_all(conf, zgr)


def main():
    'main'
    opts = getopts()
    initv(opts.verbose)
    info(f'export using {opts.xconf}')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    xexport(conf, opts.xconf)
    info('done')
