'''
Creates a docker containers for grafana and a docker container for
postgres.

It then sets the datasource in the grafana server and creates a local
directory to save the postgres state.
'''
import argparse
import os
import sys
import time

import docker

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info
from grape.common.conf import get_conf
from grape.common.gr import load_datasources
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
    # Example 2: Create a local modeling environment.
    #            Show how to access Grafana in a browswer
    #            and how to access the database using docker.
    # ------------------------------------------------
        $ {2} {0} -v -n {3} -g 4700
        $ browser http://localhost:4700
        $ docker exec -it {3}pgx01 psql -d postgres -U postgres

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


def create_containers(conf: dict, waitval: float):
    '''
    Create the docker containers.

    Args:
        conf - the configuration
        wait - the container create wait time
    '''
    client = docker.from_env()
    wait = 0
    for key in ['gr', 'pg']:
        cname = conf[key]['cname']
        containers = client.containers.list(filters={'name': cname})
        if containers:
            info(f'container already exists: "{cname}"')
            continue
        ports = conf[key]['ports']
        info(f'creating container "{cname}": {ports}')
        client.containers.run(image=conf[key]['image'],
                              hostname=conf[key]['name'],
                              name=conf[key]['name'],
                              remove=conf[key]['remove'],
                              detach=conf[key]['detach'],
                              ports=ports,
                              environment=conf[key]['env'],
                              volumes=conf[key]['vols'])
        wait = waitval

    if wait:
        # Give the containers time to start up.
        info(f'wait {wait} seconds for the containers to start up')
        time.sleep(wait)


def create(conf: dict, wait: float):
    '''
    Create the docker infrastructure.

    Args:
        conf - the configuration
        wait - the container create wait time
    '''
    create_containers(conf, wait)
    datasources = [conf['gr']['datasource']]
    load_datasources(conf, datasources)


def main():
    'main'
    opts = getopts()
    initv(opts.verbose)
    info(f'creating {opts.base} based containers')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    create(conf, opts.wait)
    info('done')
