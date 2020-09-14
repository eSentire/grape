'''
The delete operation deletes all artifacts created by the create
operation.
'''
import argparse
import os
import shutil
import subprocess
import sys
import time

import docker

from grape.common.args import DEFAULT_NAME, CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err, warn
from grape.common.conf import get_conf
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
    # Example 2: Delete the local modeling environment.
    # ------------------------------------------------
        $ {3} {0} -v -n {3} -g 4700

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


def delete_containers(conf: dict):
    '''
    Delete the docker containers.

    Args:
        conf - the configuration
    '''
    client = docker.from_env()
    for key in ['gr', 'pg']:
        cname = conf[key]['cname']
        containers = client.containers.list(filters={'name': cname})
        if containers:
            for container in containers:
                info(f'deleting container by name: "{cname}"')
                container.stop()
                time.sleep(3)
        else:
            info(f'container does not exist: "{cname}"')


def delete(conf: dict):
    '''
    Delete the docker infrastructure.

    Args:
        conf - the configuration
    '''
    delete_containers(conf)
    path = conf['pg']['name']
    if os.path.exists(path):
        info(f'removing directory: {path}')
        try:
            shutil.rmtree(path, ignore_errors=False, onerror=None)
        except FileNotFoundError:
            pass  # this is okay
        except PermissionError as exc:
            # Bad news!
            # Try deleting it as sudo.
            warn(exc)  # This is not okay!
            warn('will try to delete as sudo')
            cmd = f'sudo rm -rf {path}'
            try:
                subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            except subprocess.CalledProcessError as exc:
                err(exc)  # failed as exec
    else:
        info(f'directory does not exist: {path}')


def main():
    'main'
    opts = getopts()
    initv(opts.verbose)
    info(f'deleting {opts.base} based containers')
    conf = get_conf(opts.base, opts.fname, opts.grxport, opts.pgxport)
    delete(conf)
    info('done')
