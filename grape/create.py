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
from grape.common.log import initv, info, warn, err
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


def create_container_init(conf: dict, waitval: float):
    '''
    Wait for the containers to initialized by looking
    for messages in the logs.

    This search allows initialization to complete
    faster than just doing a simple wait.

    Args:
        conf: The configuration.
        waitval: The container create wait time in seconds.
    '''
    client = docker.from_env()
    recs = [
        {'key': 'gr', 'value': b'created default admin'},
        {'key': 'pg', 'value': b'database system is ready to accept connections'},
    ]
    def wait_timedout(start: float,  # pylint: disable=too-many-arguments
                      i: int, ival: int,
                      name: str,
                      sleep: float, opname: str):
        '''Check to see if the wait time limit was exceeded.
        '''
        elapsed = time.time() - start
        if elapsed <= waitval:
            if (i % ival) == 0:  # approximately once per second
                info('   container not initialized yet, will try again '
                     f'({opname}): {name} ({elapsed:0.1f})')
            time.sleep(sleep)
            return False

        # Worst case is that we simply wait the maximum time.
        warn(f'   container failed to initialize ({opname}): "{name}"')
        return True

    for rec in recs:
        key = rec['key']
        val = rec['value']
        name = conf[key]['name']
        info(f'checking container initialization status of "{name}" with max wait: {waitval}')
        start = time.time()
        wval = 0.1  # wait time value in seconds
        ival = 10  # report about once per second

        # Load the containers.
        # Note that the the containers.get() and the logs() operations
        # are glommed together under the same timeout because the user
        # only cares about the total time.
        i = 0
        while True:
            try:
                cobj = client.containers.get(name)
                break
            except docker.errors.NotFound:
                time.sleep(wval)
            i += 1
            if wait_timedout(start, i, ival, name, wval, 'get'):
                break

        # Read the container logs.
        logs = ''
        i = 0
        while True:
            try:
                logs = cobj.logs(tail=20)
                if val in logs.lower():
                    info(f'container initialized: "{name}"')
                    break
            except docker.errors.NotFound:
                time.sleep(wval)
            i += 1
            if wait_timedout(start, i, ival, name, wval, 'logs'):
                err(f'cannot continue:\nLOG: ({len(logs)}):\n{logs.decode("utf-8")}')
                break


def create_containers(conf: dict, waitval: float):
    '''
    Create the docker containers.

    Args:
        conf: The configuration.
        wait: The container create wait time.
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
            try:
                os.makedirs(key1)
                os.chmod(key1, 0o775)
            except FileExistsError as exc:
                warn(exc)

        ports = kconf['ports']
        info(f'creating container "{cname}": {ports}')
        client.containers.run(image=kconf['image'],
                              hostname=kconf['name'],
                              name=kconf['name'],
                              remove=kconf['remove'],
                              detach=kconf['detach'],
                              labels=kconf['labels'],
                              ports=ports,
                              environment=kconf['env'],
                              volumes=kconf['vols'])
        wait = waitval

    if wait:
        create_container_init(conf, wait)


def create(conf: dict, wait: float):
    '''
    Create the docker infrastructure.

    Args:
        conf: The configuration.
        wait: The container create wait time.
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
