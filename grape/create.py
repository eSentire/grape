'''
Creates a docker container for grafana, a docker container for
postgresql and connects them so that the postgresql container
database becomes a datasource in the grafana container.

The container names have a pg and gr suffix to denote which
service they are running.

It also creates a local directory to save the
postgres database state and the grafana dashboard state
and creates startup scripts for each dashboard in the local
directory.

If the docker containers were previously killed because of something
like a system crash, `grape create` will restart them in the same
state. The grafana dashboards and postgresql database contents will
not be lost. Beware that the `grape delete` operation will destroy the
state data.

The local directory has the same name as the name of the project.  It
container two subdirectories: gr for grafana dashboard data and pg for
postgresql data. There is a `start.sh` script in each of them for their
respective containers. There are also other directories that are
specific to the storage systems for grafana and postgresql.
'''
import argparse
import os
import sys
import time

import docker  # type: ignore

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err
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
    add_common_args(parser, '-g', '-n', '-p', '-w')
    opts = parser.parse_args()
    return opts


def create_start(conf: dict, key: str):
    '''Create the start script.

    Args:
        kconf: The configuration data.
        key: pg or gr.
    '''
    # Create the start script.
    kconf = conf[key]
    base = kconf['base']
    name = kconf['name']
    fname = os.path.join(os.getcwd(), base, key, 'start.sh')
    if os.path.exists(fname):
        return

    # Create the docker command.
    cmd = 'docker run'
    kwargs = kconf['client.containers.run']
    if kwargs['detach']:
        cmd += ' -d'
    if kwargs['remove']:
        cmd += ' --rm'
    if name:
        cmd += f' --name {name} -h {name}'
    if kwargs['environment']:
        for env in kwargs['environment']:
            cmd += f' -e "{env}"'
    if kwargs['ports']:
        for key1, val1 in kwargs['ports'].items():
            cport = key1
            hport = val1
            cmd += f' -p {hport}:{cport}'
    if kwargs['volumes']:
        for key1, val1 in kwargs['volumes'].items():
            cmd += f' -v {key1}:' + val1['bind']
    cmd += ' ' + kwargs['image']

    # Create the script.
    info(f'start script: {fname}')
    dname = os.path.dirname(fname)
    if not os.path.exists(dname):
        os.makedirs(dname)
    with open(fname, 'w', encoding='utf-8') as ofp:
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
    # Values entries must be in lowercase, they are used for pattern
    # matching in the docker logs.
    recs = [
        {'key': 'gr', 'values': ['created default admin',
                                 'http server listen']},
        {'key': 'pg', 'values': ['database system is ready to accept connections']},
    ]

    # Define the sleep interval.
    # Try to report status about every 2 seconds or so based on elaped time.
    sleep = 0.1  # time to sleep
    smodval = max(2, int(2. / sleep))  # report approximately every 2s

    # Wait the containers to initialize.
    for rec in recs:
        key = rec['key']
        values = rec['values']
        name = conf[key]['name']
        info(f'checking container initialization status of "{name}" with max wait: {waitval}')

        # Load the containers.
        # Note that the the containers.get() and the logs() operations
        # are glommed together under the same timeout because the user
        # only cares about the total time.
        try:
            cobj = client.containers.get(name)
        except docker.errors.DockerException as exc:
            logs = cobj.logs().decode('utf-8')  # provide the full log
            ##clist = [f'{c.name}:{c.short_id}:{c.status}'
            # for c in client.containers.list(all=True)]
            err(f'container failed to initialize: "{name}" - {exc}\n{logs}')

        # Read the container logs.
        start = time.time()
        logs = ''
        i = 0
        while True:
            try:
                logs = cobj.logs(tail=20).decode('utf-8')
                done = False
                for value in values:
                    if value in logs.lower():
                        elapsed = time.time() - start
                        info(f'container initialized: "{name}" after {elapsed:0.1f} seconds')
                        done = True  # initialization was successful, bases on log pattern match
                        break
                if done:
                    break
            except docker.errors.DockerException as exc:
                logs = cobj.logs().decode('utf-8')  # provide the full log
                err(f'container failed to initialize: "{name}" - {exc}\n{logs}')

            elapsed = time.time() - start
            if elapsed <= waitval:
                i += 1
                if (i % smodval) == 0:
                    info('   container not initialized yet, will try again: '
                         f'{name} ({elapsed:0.1f}s)')
                time.sleep(sleep)
            else:
                # Worst case is that we simply wait the maximum time.
                logs = cobj.logs().decode('utf-8')  # provide the full log
                err(f'container failed to initialize: "{name}"\nData: {logs}')


def create_containers(conf: dict, wait: float):
    '''Create the docker containers.

    Args:
        conf: The configuration data.
        wait: The container create wait time.
    '''
    create_start(conf, 'pg')  # postgresql
    create_start(conf, 'gr')  # grafana
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
        kwargs = kconf['client.containers.run']
        for key1 in kwargs['volumes']:
            try:
                os.makedirs(key1)
                os.chmod(key1, 0o775)
            except FileExistsError as exc:
                info(str(exc))  # this is perfectly fine

        ports = kconf['ports']
        info(f'creating container "{cname}": {ports}')
        try:
            cobj = client.containers.run(**kwargs)
        except docker.errors.DockerException as exc:
            logs = cobj.logs().decode('utf-8')
            err(f'container failed to run: "{cname}" - {exc}:\n{logs}\n')
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
    conf = get_conf(opts.base, '', opts.grxport, opts.pgxport)
    create(conf, opts.wait)
    info('done')
