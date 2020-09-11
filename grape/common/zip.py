'''
zip utils
'''
import json
import os
from zipfile import ZipFile
from grape.common.log import info, err


def load(conf: dict) -> dict:
    '''
    Load the zip data.

    Args:
        opts - the command line arguments

    Returns
        The conf, gr and pg data from the zip in
        a dictionary.
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
