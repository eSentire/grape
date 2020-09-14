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


def create_start(kconf: dict):
    '''
    Create the start script.

    Args:
        kconf - the configuration for a key
    '''
    # Create the start script.
    name = kconf['name']
    fname = os.path.join(os.getcwd(), f'{name}/start.sh')
    if os.path.exists(fname):
        return

    # Create the docker command.
    cmd = 'docker run'
    if kconf['detach']:
        cmd += ' -d'
    if kconf['remove']:
        cmd += ' --rm'
    if name:
        cmd += f' --name {name} -h {name}'
    if kconf['env']:
        for env in kconf['env']:
            cmd += f' -e "{env}"'
    if kconf['ports']:
        for key1, val1 in kconf['ports'].items():
            cport = key1
            hport = val1
            cmd += f' -p {hport}:{cport}'
    if kconf['vols']:
        for key1, val1 in kconf['vols'].items():
            cmd += f' -v {key1}:' + val1['bind']
    cmd += ' ' + kconf['image']

    # Create the script.
    info(f'start script: {fname}')
    dname = os.path.dirname(fname)
    if not os.path.exists(dname):
        os.makedirs(dname)
    with open(fname, 'w') as ofp:
        ofp.write(f'''\
#!/usr/bin/env bash
# Start the {name} container.
cd {os.getcwd()}
{cmd}
echo "started - it may take up to 30 seconds to initialize"
''')
    os.chmod(fname, 0o775)


def create_containers(conf: dict, waitval: float):
    '''
    Create the docker containers.

    Args:
        conf - the configuration
        wait - the container create wait time
    '''
    create_start(conf['pg'])  # only needed for the database

    client = docker.from_env()
    wait = 0
    for key in ['gr', 'pg']:
        kconf = conf[key]
        cname = kconf['cname']
        containers = client.containers.list(filters={'name': cname})
        if containers:
            info(f'container already exists: "{cname}"')
            continue

        # Create the volume mounted subdirectories with the proper
        # permissions.
        for key1 in kconf['vols']:
            os.makedirs(key1)
            os.chmod(key1, 0o775)

        ports = kconf['ports']
        info(f'creating container "{cname}": {ports}')
        client.containers.run(image=kconf['image'],
                              hostname=kconf['name'],
                              name=kconf['name'],
                              remove=kconf['remove'],
                              detach=kconf['detach'],
                              ports=ports,
                              environment=kconf['env'],
                              volumes=kconf['vols'])
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
