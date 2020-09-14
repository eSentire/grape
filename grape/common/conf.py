'''
The conf data for all tools.
'''
import datetime
import json
import os

from grape.common.log import debug
from grape import __version__


def get_conf(bname: str, fname: str, grxport: int, pgxport: int) -> dict:
    '''
    Get the configuration used by all tools.

    Args:
        bname - the base name (from -n)
        fname - the file name (from -f)
        grxport - the external grafana port (from -g)
        pgxport - the external database port (from -p)
    '''
    grname = bname + 'gr'
    pgname = bname + 'pg'
    pgpath_share = os.path.join(os.getcwd(), pgname)
    #pgpath_data = os.path.join(pgpath_share, 'data')
    pgpath_mnt = os.path.join(pgpath_share, 'mnt')
    conf = {
        'timestamp': datetime.datetime.utcnow().isoformat(timespec='seconds'),
        'version': __version__,
        'base': bname,
        'file': fname,
        'gr': {
            'name': grname,
            'cname': '/' + grname,  # docker container path
            'xport': grxport,
            'iport': 3000,  # default grafana port
            'image': 'grafana/grafana:latest',
            'remove': True,
            'detach': True,
            'env': [],
            'vols': {},
            'username': 'admin',
            'password': 'admin',
            'host': 'localhost',
            'url': f'http://localhost:{grxport}',
            'datasource': {
                'name': pgname,
                'type': 'postgres',
                'access': 'proxy',
                'user': 'postgres',
                'password': 'password',
                'database': 'postgres',
                'url': 'localhost:5432',
                'jsonData': {
                    'postgresVersion': 1000,
                    'sslmode': 'disable',
                },
                'readOnly': False,
            },
        },
        'pg': {
            'name': pgname,
            'cname': '/' + pgname,  # docker container path
            'xport': pgxport,
            'iport': 5432,  # default postgres port
            'image': 'postgres:latest',
            'remove': True,
            'detach': True,
            'env': [
                'PGDATA=/mnt/pgdata',
                'POSTGRES_USER=postgres',
                'POSTGRES_PASSWORD=password'],
            'share': pgpath_share,
            'mnt': pgpath_mnt,
            'vols': {
#                pgpath_data: {
#                    'bind': '/var/lib/postgresql/data',
#                    'mode': 'rw',
#                },
                pgpath_mnt: {
                    'bind': '/mnt',
                    'mode': 'rw',
                },
            },
            'dbname': 'postgres',
            'username': 'postgres',
            'password': 'password',
            'host': 'localhost',
        },
    }

    # Update defaults, if needed.
    if not conf['pg']['xport']:
        conf['pg']['xport'] = conf['gr']['xport'] + 1
    if not conf['file']:
        conf['file'] = conf['base'] + '.zip'

    # Add in the port mappings.
    conf['gr']['ports'] = {
        f'{conf["gr"]["iport"]}/tcp': conf['gr']['xport'],
    }
    conf['pg']['ports'] = {
        f'{conf["pg"]["iport"]}/tcp': conf['pg']['xport'],
    }

    debug(f'conf:\n{json.dumps(conf, indent=2)}')
    return conf
