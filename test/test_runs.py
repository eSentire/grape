'''
Test run operations like create, delete, save and load.

The tests must run in module order because they have dependencies on
the previous results.

That is enforced using pytest-depends. Using dependencies ensures that
future refactoring won't affect implicit dependencies and it ensures
that running a single test will create the proper pre-requisities.

Creating and deleting the projects takes a long time (30 seconds or
so) so creating a fixture to create and tear down projects for each
test would slow things down too much.
'''
import inspect
import os
import pathlib
import sys
import time
from subprocess import Popen, PIPE
from typing import Any, Tuple
from zipfile import ZipFile
import pytest
import docker  # type: ignore

from grape import cli
from grape import delete
from grape import create
from grape import save
from grape import load
from grape import ximport
from grape import xexport
from grape import status
from grape import tree


GPORT = 4700
NAME = 'grape_test1'

GPORT2 = 4710
NAME2 = 'grape_test2'


def debug(msg: str, level: int = 1):
    '''
    Print a debug message with context.

    Args:
        msg: The message string.
        level: The stack level. Default is the caller.
    '''
    lnum = inspect.stack()[level].lineno
    fname = inspect.stack()[level].filename
    base = os.path.basename(fname)
    print(f'\x1b[35mDEBUG:{base}:{lnum}: {msg}\x1b[0m\n')


def make_yaml_file(path: str, gport: int):
    '''Make the YAML file for the grafana server login.

    Args:
        gport: The grafana server port.
        path: The YAML file name.

    Raises:
        OSError: If the local filesystem is read-only. That should
            never happen.
    '''
    content = f'''\
url: http://localhost:{gport}/
username: 'admin'
password: 'admin'
databases:
  - database: 'postgres'
    password: 'password'
'''

    # Write the file.
    with open(path, 'w') as ofp:
        ofp.write(content)


def make_names(name: str) -> Tuple[str, str, str]:
    '''Simple function that generates useful names.

    This could easily be a test fixture but it is not worth it.

    Args:
        name: The name of the grape project.

    Returns:
        cgr: The name of the graphana container.
        cpg: The name of the database container.
        zpf: The name of the zip file.
    '''
    return name + 'gr', name + 'pg', name + '.zip'


def test_run_cli(capsys: Any):
    'test the wrapper interface'
    fct = inspect.stack()[0].function  # fct name

    # Test no args.
    sys.argv = [fct]
    with pytest.raises(SystemExit) as exc:
        cli.main()
    out, err = capsys.readouterr()
    debug(f'cmd=<<<{sys.argv}>>>')
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert exc.type == SystemExit
    assert exc.value.code == 0

    # test cli help and version.
    for cmd in ['help', '--help', '-h', 'version', '--version', '-V']:
        sys.argv = [fct, cmd]
        with pytest.raises(SystemExit) as exc:
            cli.main()
        out, err = capsys.readouterr()
        debug(f'cmd=[{len(cmd)}]<<<{cmd}>>>')
        debug(f'out=[{len(out)}]<<<{out}>>>')
        debug(f'err=[{len(err)}]<<<{err}>>>')
        assert exc.type == SystemExit
        assert exc.value.code == 0

    # now test cli operations help
    for cmd in ['create', 'cr', 'delete', 'del', 'load', 'save', 'import', 'export']:
        for opt in ['-h', '--help', '-V', '--version', 'help', 'version']:
            sys.argv = [fct, cmd, opt]
            with pytest.raises(SystemExit) as exc:
                cli.main()
            out, err = capsys.readouterr()
            debug(f'cmd=[{len(cmd)}]<<<{cmd}>>>')
            debug(f'out=[{len(out)}]<<<{out}>>>')
            debug(f'err=[{len(err)}]<<<{err}>>>')
            assert exc.type == SystemExit
            assert exc.value.code == 0

    # Test: help COMMAND
    for cmd in ['create', 'cr', 'delete', 'del', 'load', 'save', 'import', 'export']:
        sys.argv = [fct, 'help', cmd]
        with pytest.raises(SystemExit) as exc:
            cli.main()
        out, err = capsys.readouterr()
        debug(f'cmd=[{len(cmd)}]<<<{cmd}>>>')
        debug(f'out=[{len(out)}]<<<{out}>>>')
        debug(f'err=[{len(err)}]<<<{err}>>>')
        assert exc.type == SystemExit
        assert exc.value.code == 0

    # Test bad argument handling.
    sys.argv = [fct, 'frobniz']
    with pytest.raises(SystemExit) as exc:
        cli.main()
    out, err = capsys.readouterr()
    debug(f'cmd=[{len(cmd)}]<<<{cmd}>>>')
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert exc.type == SystemExit
    assert exc.value.code != 0


@pytest.mark.depends(on=['test_run_cli'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
        (NAME2, GPORT2),
    ],
)
def test_run_init(capsys: Any, name: str, gport: int):
    '''Initialization: delete a project.

    In this case the project should not already exist.

    This cleans up everything for the subsequent tests.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Delete the primary set of resources.
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport)]
    delete.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert not os.path.exists(namepg)
    assert namegr in err
    assert namepg in err
    if os.path.exists(namezp):
        os.unlink(namezp)
    assert not os.path.exists(namezp)


@pytest.mark.depends(on=['test_run_init'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_create(capsys: Any, name: str, gport: int):
    '''Create a project.

    The project will be used in subsequent tests.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, _namezp = make_names(name)
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport)]
    create.main()
    out, err = capsys.readouterr()
    script = os.path.join(namepg, 'start.sh')
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert os.path.exists(namepg)
    assert os.path.exists(script)  # make sure that the script was created
    assert namegr in err
    assert namepg in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': namegr})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': namepg})
    assert len(cpg) == 1


@pytest.mark.depends(on=['test_run_create'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_save(capsys: Any, name: str, gport: int):
    '''Save the project data to a zip file.

    This file will be used in the next text.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    _namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport), '-f', namezp]
    save.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert os.path.exists(namepg)
    assert os.path.exists(namezp)
    assert 'docker exec' in err
    assert '1 datasources' in err
    with ZipFile(namezp, 'r') as zfp:
        names = zfp.namelist()
        debug(f'names={names}')
    assert len(names) == 3
    assert 'conf.json' in names
    assert 'gr.json' in names
    assert 'pg.sql' in names


@pytest.mark.depends(on=['test_run_save'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_load(capsys: Any, name: str, gport: int):
    '''Load the saved data from the zip file create in the previous
    test.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function
    assert os.path.exists(namepg)  # the database directory
    assert os.path.exists(namezp)  # the zip file
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport), '-f', namezp]
    load.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert namegr in err
    assert namepg in err


@pytest.mark.depends(on=['test_run_load'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_import(capsys: Any, name: str, gport: int):
    '''Import data into the test project.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    _namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Prerequisites.
    assert os.path.exists(namepg)
    if os.path.exists(namezp):
        os.unlink(namezp)

    # Create the YAML conf file for logging in.
    xcfn = fct + '.yaml'
    make_yaml_file(xcfn, gport)
    assert os.path.exists(xcfn)

    # Run import.
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport), '-f', namezp, '-x', xcfn]
    ximport.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert namepg in err
    assert f'http://localhost:{gport}' in err
    os.unlink(xcfn)


@pytest.mark.depends(on=['test_run_import'])
@pytest.mark.parametrize(
    'name,name2,gport2',
    [
        (NAME, NAME2, GPORT2),
    ],  # pylint: disable=too-many-locals
)
def test_run_export(capsys: Any, name: str, name2: str, gport2: int):
    '''Export data into the test project.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        name2: The export grape project.
        gport2: The export grafana port.
    '''
    _namegr, namepg, namezp = make_names(name)
    namegr2, namepg2, _namezp2 = make_names(name2)
    fct = inspect.stack()[0].function

    # Prerequisites.
    assert os.path.exists(namepg)

    # Create the name2 container to export to.
    sys.argv = [fct, '-v', '-n', name2, '-g', str(gport2)]
    create.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert os.path.exists(namepg2)
    assert namegr2 in err
    assert namepg2 in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': namegr2})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': namepg2})
    assert len(cpg) == 1

    # Prerequisites.
    assert os.path.exists(namezp)  # the import zip.
    assert os.path.exists(namepg2)  # the export database

    # Create the YAML conf file for logging in.
    xcfn = fct + '.yaml'
    make_yaml_file(xcfn, gport2)
    assert os.path.exists(xcfn)

    # Export the primary container to it.
    sys.argv = [fct, '-v', '-n', name2, '-g', str(gport2), '-f', namezp, '-x', xcfn]
    xexport.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert namepg2 in out
    assert f'http://localhost:{GPORT2}' in out
    os.unlink(xcfn)


@pytest.mark.depends(on=['test_run_export'])
@pytest.mark.parametrize(
    'name,name2',
    [
        (NAME, NAME2),
    ],
)
def test_run_status(capsys: Any, name: str, name2: str):
    '''Check the status of the containers created in previous tests.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        name2: The export grape project.
    '''
    _namegr, namepg, _namezp = make_names(name)
    _namegr2, namepg2, _namezp2 = make_names(name2)
    fct = inspect.stack()[0].function

    # Prerequisites.
    assert os.path.exists(namepg)
    assert os.path.exists(namepg2)

    sys.argv = [fct, '-v']
    status.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')

    client = docker.from_env()
    containers = client.containers.list(filters={'label': 'grape.type'})
    assert len(containers) >= 2


@pytest.mark.depends(on=['test_run_status'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
        (NAME2, GPORT2),
    ],
)
def test_run_tree(capsys: Any, name: str, gport: int):
    '''Check the tree report.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        gport: The grafana server port for a grape project.
    '''
    namegr, namepg, _namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Prerequisites.
    assert os.path.exists(namepg)

    # Negative test.
    with pytest.raises(SystemExit) as exc:
        sys.argv = [fct, '-g', '55555']
        tree.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert exc.value.code

    # Positive test.
    rfile = fct + '.log'
    sys.argv = [fct, '-g', str(gport), '-f', rfile]
    tree.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')

    with open(rfile) as ifp:
        out = ifp.read()
        debug(f'out=[{len(out)}]<<<{out}>>>')
    key = namegr + ':' + str(gport)
    assert ' datasources' in out
    assert ' folders' in out
    assert namepg in out
    assert key in out  # grape_test1gr:4700
    assert ':id=1:type=postgres' in out  # make sure that the database is there
    os.unlink(rfile)  # delete the report log

    # Positive test #2 (sort)
    sys.argv = [fct, '-g', str(gport), '-f', rfile, '--sort']
    tree.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')

    with open(rfile) as ifp:
        out = ifp.read()
        debug(f'out=[{len(out)}]<<<{out}>>>')
    key = namegr + ':' + str(gport)
    assert ' datasources' in out
    assert ' folders' in out
    assert namepg in out
    assert key in out  # grape_test1gr:4700
    assert ':id=1:type=postgres' in out  # make sure that the database is there
    os.unlink(rfile)  # delete the report log


@pytest.mark.depends(on=['test_run_tree'])
@pytest.mark.parametrize(
    'name',
    [
        (NAME),
    ],
)
def test_run_runpga(name: str):
    '''Test the runpga script.

    Since this is not python, we check for the existence of the
    created container.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    _namegr, namepg, _namezp = make_names(name)

    # Prerequisites.
    assert os.path.exists(namepg)

    # Run the subprocess to create the pgAdmin container.
    path = os.path.join(pathlib.Path(__file__).parent.parent.absolute(), 'tools', 'runpga.sh')
    debug(f'path={path}')
    assert os.path.exists(path)
    debug(f'container={namepg}')
    proc = Popen([path, namepg], stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    debug(f'out=[{len(out)}]<<<{repr(out)}>>>')
    debug(f'err=[{len(err)}]<<<{repr(err)}>>>')
    assert proc.returncode == 0

    # Make sure that the container was created.
    # The 2 second wait is sufficient for the container to show
    # up in the docker process table.
    time.sleep(2)
    namepa = name + 'pa'  # the pgadmin container
    client = docker.from_env()
    containers = client.containers.list(filters={'name': namepa})
    assert containers
    assert len(containers) == 1

    # Now that the pgAdmincontainer exists, delete it.
    # We gave proven that the script created it.
    # We need to make sure that the container is destroyed.
    containers = client.containers.list(filters={'name': namepa})
    container = containers[0]
    container.remove(force=True)
    time.sleep(5)  # it will take much less time than this

    # Make sure that it is dead and gone.
    containers = client.containers.list(filters={'name': namepa})
    assert not containers


@pytest.mark.depends(on=['test_run_runpga'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],  # pylint: disable=too-many-locals
)
def test_run_dash_import_csv(capsys, name: str, gport: int):
    '''Verify that the dashboard csv import idiom works.

    This is very similar to what demo02 does.

    The test converts a CSV dataset to SQL and loads it
    into a database. After that it creates a dashboard
    that uses that database.

    It uses the tools/csv2sql.py and tools/upload-json-dashboard.sh
    scripts.

    Args:
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    _namegr, namepg, _namezp = make_names(name)
    testdir = pathlib.Path(__file__).parent.absolute()
    csvfile = os.path.join(testdir, 'test_run_dash_import_csv.csv')
    dashfile = os.path.join(testdir, 'test_run_dash_import_csv.json')
    script1 = os.path.join(pathlib.Path(__file__).parent.parent.absolute(),
                           'tools', 'csv2sql.py')
    script2 = os.path.join(pathlib.Path(__file__).parent.parent.absolute(),
                           'tools', 'upload-json-dashboard.sh')

    debug(f'namepg  : {namepg}')
    debug(f'gport   : {gport}')
    debug(f'testdir : {testdir}')
    debug(f'csvfile : {csvfile}')
    debug(f'dashfile: {dashfile}')
    debug(f'script1 : {script1}')
    debug(f'script2 : {script2}')

    # Verify that the data files exist.
    assert os.path.exists(namepg)
    assert os.path.exists(csvfile)
    assert os.path.exists(dashfile)

    # Verify that the help option works for the scripts.
    for path in [script1, script2]:
        debug(f'path={path}')
        assert os.path.exists(path)
        proc = Popen([path, '-h'], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        debug(f'out=[{len(out)}]<<<{repr(out)}>>>')
        debug(f'err=[{len(err)}]<<<{repr(err)}>>>')
        assert proc.returncode == 0

    # Create the SQL file with the correct file.
    sqlfile = os.path.join(testdir, namepg, 'mnt', 'test_run_dash_import_csv.sql')
    debug(f'sqlfile={sqlfile}')
    proc = Popen([script1,
                  '-v',
                  '-t', 'all_weekly_excess_deaths',
                  '-o', sqlfile, csvfile],
                 stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    debug(f'out=[{len(out)}]<<<{repr(out)}>>>')
    debug(f'err=[{len(err)}]<<<{repr(err)}>>>')
    assert proc.returncode == 0
    assert os.path.exists(sqlfile)

    # Import the data into the container using docker.
    client = docker.from_env()
    containers = client.containers.list(filters={'name': namepg})
    assert containers
    assert len(containers) == 1
    container = containers[0]
    cmd = 'psql -U postgres -d postgres -f /mnt/test_run_dash_import_csv.sql'
    container.exec_run(cmd, stdout=True, stderr=False, tty=True)
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{repr(out)}>>>')
    debug(f'err=[{len(err)}]<<<{repr(err)}>>>')

    # At this point the database container is ready to roll
    # so it is time to create the dashboard.
    # $ jq '.__inputs[].name' test/test_run_dash_import_csv.json
    # "DS_DEMO02PG"
    proc = Popen([script2,
                  '-d', namepg,
                  '-f', '0',
                  '-g', f'http://localhost:{gport}',
                  '-j', dashfile,
                  '-n', 'DS_DEMO02PG',
                  '-v'],
                 stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    debug(f'out=[{len(out)}]<<<{repr(out)}>>>')
    debug(f'err=[{len(err)}]<<<{repr(err)}>>>')
    assert proc.returncode == 0

    # And voila! It is done!


@pytest.mark.depends(on=['test_run_dash_import_csv'])
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
        (NAME2, GPORT2),
    ],
)
def test_run_cleanup(capsys: Any, name: str, gport: int):
    '''Delete a grape project.

    It is called multiple times to clean up the test artifacts.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    _namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Delete the set of resources.
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport)]
    delete.main()
    out, err = capsys.readouterr()
    debug(f'out=[{len(out)}]<<<{out}>>>')
    debug(f'err=[{len(err)}]<<<{err}>>>')
    assert not os.path.exists(namepg)
    assert namepg in err
    if os.path.exists(namezp):
        os.unlink(namezp)
    assert not os.path.exists(namezp)
