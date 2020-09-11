'''
Save captures the specified grafana modeling development environment
and stores the result in the specified zip file.

The contents of that zip file can be stored directly in a revision
control system or the contents can be extracted and stored.
'''
import argparse
import json
import os
import sys
from functools import reduce
from zipfile import ZipFile

import requests

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err
from grape.common.conf import get_conf
from grape.common.pg import save as save_pg
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
    # Example 2: Save the local modeling environment.
    # ------------------------------------------------
        $ {2} {0} -v -n {3} -g 4700 -f example.zip

    # ------------------------------------------------
    # Example 3: Extract the contents of the saved zip file.
    #            They can be used to store text in a source
    #            code control system.
    # ------------------------------------------------
        $ {2} {0} -v -n {3} -g 4700 -f example.zip

        $ ## See whats in the zip file.
        $ unzip -l example.zip

        $ ## Extract the contents.
        $ unzip -p example.zip conf.json > conf.json
        $ unzip -p example.zip gr.json > gr.json
        $ unzip -p example.zip pg.sql > pg.sql

        $ ## Save them in the source code repository.
        $ git commit -m'update conf' conf.json gr.json pg.sql

        $ ## Check them out and reconstitute the zip file.
        $ git checkout conf.json gr.json pg.sql
        $ rm example.zip
        $ zip example.zip conf.json gr.json pg.sql
        $ unzip -l example.zip

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


def save_gr_read(conf: dict, service: str) -> dict:
    '''
    Read a single grafana service.

    Args:
        conf - the configuration
        service - the grafana REST service

    Returns
        the JSON from the URL request
    '''
    port = conf['gr']['xport']
    auth = (conf['gr']['username'], conf['gr']['password'])
    host = conf['gr']['host']
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    url = f'http://{host}:{port}/{service}'
    info(f'reading {url}')
    response = requests.get(url, auth=auth, headers=headers)
    if response.status_code != 200:
        err(f'request to {url} failed with status {response.status_code}\n'
            f'{json.dumps(response.json(), indent=2)}')
    result = response.json()
    return result


def save_gr_all(conf: dict) -> dict:
    '''
    Read the grafana state from a local server and save it.

    Args:
        conf - the configuration

    Returns
        the datasources, folders and dashboards
    '''
    info('reading grafana')

    # Read the datasources.
    datasources = save_gr_read(conf, 'api/datasources')

    # Read the folders.
    folders = save_gr_read(conf, 'api/folders?limit=100')
    info(f'read {len(folders)} folders')
    fids = reduce(lambda x, y: x+[y] if not y in x else x,
                  [fid['id'] for fid in folders],
                  [])
    if not fids:
        # The General folder always exists.
        fids = [0]

    # Read the dashboards.
    dashboards = []
    for fid in fids:
        recs = save_gr_read(conf, f'api/search?folderIds={fid}')
        for rec in recs:
            uid = rec['uid']
            dash = save_gr_read(conf, f'api/dashboards/uid/{uid}')
            dash['folderId'] = fid
            dashboards.append(dash)

    result = {
        'datasources': datasources,
        'folders': folders,
        'dashboards': dashboards,
    }
    info(f'{len(result["datasources"])} datasources')
    info(f'{len(result["folders"])} folders')
    info(f'{len(result["dashboards"])} dashboards')
    return result


def save(conf: dict):
    '''
    Save the database and grafana server state into an archive.

    Args:
        conf - the configuration
    '''
    ofn = conf['file']
    if os.path.exists(ofn):
        err(f'archive file already exists: {ofn}')

    # Load the data from the servers.
    grr = save_gr_all(conf)
    sql = save_pg(conf)

    # Now create the zip bundle.
    info(f'writing to {ofn}')
    if 'zip' in ofn.lower():
        # Do zip
        with ZipFile(ofn, 'w') as zfp:
            zfp.writestr('conf.json', json.dumps(conf))
            zfp.writestr('gr.json', json.dumps(grr))
            zfp.writestr('pg.sql', sql)
        # One can unzip the individual files like this:
        #   $ unzip -p /tmp/example.zip conf.json > /tmp/conf.json
        #   $ unzip -p /tmp/example.zip gr.json > /tmp/gr.json
        #   $ unzip -p /tmp/example.zip pg.sql > /tmp/pg.sql
    else:
        err('only zip files are supported')


def main():
    'main'
    opts = getopts()
    initv(opts.verbose)
    info(f'save {opts.base}')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    save(conf)
    info('done')
