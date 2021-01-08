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

import docker  # type: ignore

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info, warn, err
from grape.common.conf import get_conf
from grape.common.gr import load_datasources
from grape import __version__


def getopts() -> argparse.Namespace:
    '''Process the module specific command line options.

    Returns:
       opts: The argument namespace.
    '''
    argparse._ = args_get_text  # type: ignore
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
    '''Create the start script.

    Args:
        kconf: The configuration data for a key.
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


def create_container_init(conf: dict, waitval: float):  # pylint: disable=too-many-locals
    '''Initialize the containers.

    Wait for the containers to initialized by looking
    for messages in the logs.

    This search allows initialization to complete
    faster than just doing a simple wait.

    Args:
        conf: The configuration data.
        waitval: The container create wait time in seconds.
    '''
    # This is a heuristic that does a short wait to give docker
    # sufficient time to start to define the new containers before we
    # start to query them.
    #
    # In particular, this significantly reduces the chance
    # that the docker.errors.NotFound exception will be
    # raised.
    #
    # One second is probably overkill.
    time.sleep(1)
    client = docker.from_env()

    # The values below are heuristic based on empirical observation of
    # the logs. They may have to change based on versions of docker.
    recs = [
        {'key': 'gr', 'value': 'created default admin'},
        {'key': 'pg', 'value': 'database system is ready to accept connections'},
    ]

    # Define the sleep interval.
    # Try to report status about every 2 seconds or so based on elaped time.
    sleep = 0.1  # time to sleep
    smodval = max(2, int(2. / sleep))  # report approximately every 2s

    # Wait the containers to initialize.
    for rec in recs:
        key = rec['key']
        val = rec['value']
        name = conf[key]['name']
        info(f'checking container initialization status of "{name}" with max wait: {waitval}')

        # Load the containers.
        # Note that the the containers.get() and the logs() operations
        # are glommed together under the same timeout because the user
        # only cares about the total time.
        try:
            cobj = client.containers.get(name)
        except docker.errors.NotFound as exc:
            err(f'container failed to initialize: "{name}" - {exc}')

        # Read the container logs.
        start = time.time()
        logs = ''
        i = 0
        while True:
            try:
                logs = str(cobj.logs(tail=20))
                if val in logs.lower():
                    elapsed = time.time() - start
                    info(f'container initialized: "{name}" after {elapsed:0.1f} seconds')
                    break
            except docker.errors.NotFound as exc:
                err(f'container failed to initialize: "{name}" - {exc}')

            elapsed = time.time() - start
            if elapsed <= waitval:
                i += 1
                if (i % smodval) == 0:
                    info('   container not initialized yet, will try again: '
                         f'{name} ({elapsed:0.1f}s)')
                time.sleep(sleep)
            else:
                # Worst case is that we simply wait the maximum time.
                err(f'container failed to initialize: "{name}"\nData: {logs}')


def create_containers(conf: dict, wait: float):
    '''Create the docker containers.

    Args:
        conf: The configuration data.
        wait: The container create wait time.
    '''
    create_start(conf['pg'])  # only needed for the database
    client = docker.from_env()
    num = 0
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
                warn(str(exc))

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
        num += 1

    if wait:
        create_container_init(conf, wait)


def create(conf: dict, wait: float):
    '''Create the docker infrastructure.

    Args:
        conf: The configuration data.
        wait: The container create wait time.
    '''
    create_containers(conf, wait)
    datasources = [conf['gr']['datasource']]
    load_datasources(conf, datasources)


def main():
    '''Create command main.

    This is the command line entry point for the create command.
    '''
    opts = getopts()
    initv(opts.verbose)
    info(f'creating {opts.base} based containers')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    create(conf, opts.wait)
    info('done')
