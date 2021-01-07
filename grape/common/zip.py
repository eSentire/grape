'''
zip utils
'''
import json
import os
from zipfile import ZipFile
from grape.common.log import info, err


def load(conf: dict) -> dict:
    '''Load the zip state data.

    The state data that describes a project is stored in
    a zip file with known files. This function encapsulates
    reading them.

    The known files are: conf.json, gr.json and pg.sql.

    The conf.json file contains project configuration data.

    The gr.json file contains the grafana server datasources,
    folders and dashboards setup.

    The pq.sql contains the database setup.

    The conf dictionary that is returned as three top level
    keys: 'conf', 'gr' and 'pg'. One for each file read.

    Args:
        opts: The command line arguments.

    Returns:
        conf: The configuration data from each file.
    '''
    ofn = conf['file']
    if not os.path.exists(ofn):
        err(f'archive file does not exist: {ofn}')

    info(f'loading from {ofn}')
    with ZipFile(ofn, 'r') as zfp:
        zfn = 'conf.json'
        with zfp.open(zfn) as ifp:
            info(f'loading {zfn} from {ofn}')
            zconf = json.loads(ifp.read().decode('utf-8'))

        zfn = 'gr.json'
        with zfp.open(zfn) as ifp:
            info(f'loading {zfn} from {ofn}')
            zgr = json.loads(ifp.read().decode('utf-8'))

        zfn = 'pg.sql'
        with zfp.open(zfn) as ifp:
            info(f'loading {zfn} from {ofn}')
            sql = ifp.read().decode('utf-8')
    result = {
        'conf': zconf,
        'gr': zgr,
        'pg': sql,
    }
    return result
