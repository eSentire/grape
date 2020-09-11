'''
Postgres database utilities.
'''
import os
import subprocess
import time
from grape.common.log import info, err, debug, warn


def load(conf: dict, sql: str):
    '''
    Load the database data.

    This is done using psql in the container by copying
    the sql to the tmp directory that is mounted to the
    container.

    Args:
        conf - the configuration
        sql  - the SQL to update the database.
    '''
    dbname = conf['pg']['dbname']
    name = conf['pg']['name']
    user = conf['pg']['username']
    tmp = conf['pg']['tmp']
    tfn = f'tmp{os.getpid()}.sql'
    tfpx = f'{tmp}/{tfn}'  # external (host) path
    tfpi = f'/tmp/{tfn}'  # internal (container) path

    # Fix minor nit. The role always already exists.
    sql = sql.replace('CREATE ROLE postgres;', '-- CREATE ROLE postgres;')

    # Now write the SQL.
    with open(tfpx, 'w') as ofp:
        ofp.write(sql)
    if not os.path.exists(tfpx):
        err(f'file does not exist: {tfpx}')

    # Write to the database.
    cmd = f'docker exec {name} psql -d {dbname} -U {user} -f {tfpi}'
    tmax = 10
    tcnt = 0
    while tcnt <= tmax:
        try:
            info(cmd)
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            break
        except subprocess.CalledProcessError as exc:
            tcnt += 1
            warn(f'try {tcnt} of {tmax}\n' + exc.output.decode('utf-8'))
            if tcnt == tmax:
                err(exc)
            time.sleep(5)
    debug(out.decode('utf-8'))


def save(conf: dict) -> str:
    '''
    Read the database contents.

    This is the same as a backup command and the only reasonable
    way to do it is by using the pgdump command.

    Args:
        conf - the configuration

    Returns
        the SQL to restore the database
    '''
    info('reading the database')
    name = conf['pg']['name']
    user = conf['pg']['username']
    cmd = f'docker exec {name} pg_dumpall -U {user}'
    try:
        info(cmd)
        out = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as exc:
        warn(exc)
        out = b'-- no pg docker container'
    sql = str(out.decode('utf-8'))
    info(f'read {len(sql)} bytes of sql for the database')
    return sql
