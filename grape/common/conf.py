'''
The conf data for all tools.
'''
import datetime
import json
import os
from typing import Any, Dict

from grape.common.log import debug
from grape import __version__


DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin'
DEFAULT_AUTH = (DEFAULT_USERNAME, DEFAULT_PASSWORD)


def get_conf(bname: str, fname: str, grxport: int, pgxport: int) -> Dict[str, Any]:
    '''Get the grape project configuration data used by all tools.

    This is used by each of the commands and is customized by
    command line argument settings.

    Args:
        bname: The base name (from -n).
        fname: The file name (from -f).
        grxport: The external grafana port (from -g).
        pgxport: The external database port (from -p).

    Returns:
        conf: The configuration dictionary.
    '''
    grname = bname + 'gr'
    pgname = bname + 'pg'
    grpath_share = os.path.join(os.getcwd(), bname, 'gr')
    grpath_mnt = os.path.join(grpath_share, 'mnt')
    pgpath_share = os.path.join(os.getcwd(), bname, 'pg')
    pgpath_mnt = os.path.join(pgpath_share, 'mnt')
    conf : Dict[str, Any] = {
        'timestamp': datetime.datetime.utcnow().isoformat(timespec='seconds'),
        'version': __version__,
        'base': bname,
        'file': fname,
        'gr': {
            'client.containers.run': {
                'detach': True,
                'environment': [
                    'GF_PATHS_DATA=/mnt/grdata',
                ],
                'hostname': grname,
                'image': 'grafana/grafana:latest',
                'name': grname,
                'remove': True,
                'stdout': True,
                'stderr': True,
                'labels': {'grape.type': 'gr',
                           'grape.version' : __version__},
                'user': f'{os.getuid()}:{os.getgid()}',
                'volumes': {
                    grpath_mnt: {
                        'bind': '/mnt',
                        'mode': 'rw',
                    },
                },
            },
            'base': bname,
            'name': grname,
            'cname': '/' + grname,  # docker container path
            'xport': grxport,
            'iport': 3000,  # default grafana port
            'username': DEFAULT_USERNAME,
            'password': DEFAULT_PASSWORD,
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
            'client.containers.run': {
                'detach': True,
                'environment': [
                    'PGDATA=/mnt/pgdata',
                    'POSTGRES_USER=postgres',
                    'POSTGRES_PASSWORD=password'],
                'hostname': pgname,
                'image': 'postgres:latest',
                'name': pgname,
                'remove': True,
                'stdout': True,
                'stderr': True,
                'labels': {'grape.type': 'pg',
                           'grape.version' : __version__},
                'user': f'{os.getuid()}:{os.getgid()}',
                'volumes': {
                    pgpath_mnt: {
                        'bind': '/mnt',
                        'mode': 'rw',
                    },
                },
            },
            'base': bname,
            'name': pgname,
            'cname': '/' + pgname,  # docker container path
            'xport': pgxport,
            'iport': 5432,  # default postgres port
            'mnt': pgpath_mnt,
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

    # Add in the port mappings for the containers.
    conf['gr']['client.containers.run']['ports'] = {
        f'{conf["gr"]["iport"]}/tcp': conf['gr']['xport'],
    }
    conf['pg']['client.containers.run']['ports'] = {
        f'{conf["pg"]["iport"]}/tcp': conf['pg']['xport'],
    }

    debug(f'conf:\n{json.dumps(conf, indent=2)}')
    return conf
