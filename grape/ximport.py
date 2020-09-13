'''
The import operation captures an external grafana environment for the
purposes of experimenting or working locally.

It imports rhe datasources without passwords because grafana never
exports passwords which means that they have to be updated manually
after the import operation completes or by specifying the passwords in
the associated conf file. It does not import databases.

The import operation creates a zip file that can be used by a load
operation. It also requires a conf file that is specified by the -x
option.

The YAML file that describes the external access cannot be created
automatically because grafana does not export passwords.
'''
import argparse
import json
import os
import sys
from zipfile import ZipFile

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err
from grape.common.gr import read_all_services
from grape.common.pg import save as save_pg
from grape.common.conf import get_conf
from grape.common.xconf import get_xconf
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
    # Example 2: Import an external grafana system.
    #            The external YAML must be created
    #            manually because it contains
    #            sensitive information.
    # ------------------------------------------------
        $ edit import.yaml
        $ {2} import -v -n example -g 4800 -f import.zip -x import.yaml
        $ {2} load   -v -n example -g 4800 -f import.zip

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


def ximport(conf: dict, xconf: str):
    '''
    Import an external grafana server system.

    The imported system will be stored in a local system.

    This operation requires an import conf file.

    Args:
        conf - the configuration
        xconf - the external conf
    '''
    info('import')
    ofn = conf['file']
    if os.path.exists(ofn):
        err(f'archive file already exists: {ofn}')

    iconf =  get_xconf(xconf)
    conf['import'] = iconf
    auth = (iconf['username'], iconf['password'])
    grr = read_all_services(iconf['url'], auth)
    sql = save_pg(conf)
    info(f'writing to {ofn}')
    if 'zip' in ofn.lower():
        # Do zip
        with ZipFile(ofn, 'w') as zfp:
            zfp.writestr('conf.json', json.dumps(conf))
            zfp.writestr('gr.json', json.dumps(grr))
            zfp.writestr('pg.sql', sql)
        # One can unzip the individual files like this:
        #   $ unzip -p /mnt/example.zip conf.json > /mnt/conf.json
        #   $ unzip -p /mnt/example.zip gr.json > /mnt/gr.json
        #   $ unzip -p /mnt/example.zip pg.sql > /mnt/pg.sql
    else:
        err('only zip files are supported')


def main():
    'main'
    opts = getopts()
    initv(opts.verbose)
    info(f'import from {opts.xconf}')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    ximport(conf, opts.xconf)
    info('done')
