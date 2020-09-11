'''
The YAML configuration that describes the external server.
'''
import getpass
import json
import yaml
from grape.common.log import debug


def get_xconf(ifn: str) -> dict:
    '''
    Import the YAML configuration that describes the external server.

    Args:
        ifn - The YAML file name
    Returns
        The import conf.
    '''
    with open(ifn) as ifp:
        iconf = yaml.load(ifp, Loader=yaml.FullLoader)
        if 'url' not in iconf or not iconf['url']:
            url = input('url: ')
            iconf['url'] = url
        if 'username' not in iconf or not iconf['username']:
            username = input('username: ')
            iconf['username'] = username
        if 'password' not in iconf or not iconf['password']:
            password = getpass.getpass('password: ')
            iconf['password'] = password
        if 'databases' in iconf:
            for i, rec in enumerate(iconf['databases']):
                if 'password' not in rec:
                    print('please enter database password')
                    for key, val in sorted(rec.items(), key=lambda x: x[0].lower()):
                        print(f'  {key}="{val}"')
                    password = getpass.getpass('  password: ')
                    iconf['databases'][i]['password'] = password
    while iconf['url'].endswith('/'):
        iconf['url'] = iconf['url'][:-1]
    debug(json.dumps(iconf, indent=2))
    return iconf
