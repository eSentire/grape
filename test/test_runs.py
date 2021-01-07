'''
Test run operations like create, delete, save and load.
'''
import inspect
import os
import sys
from typing import Any, Callable, Tuple
from zipfile import ZipFile
import pytest
import docker
from decorator import decorator

from grape import cli
from grape import delete
from grape import create
from grape import save
from grape import load
from grape import ximport
from grape import xexport
from grape import status


GPORT = 4700
NAME = 'grape_test1'

GPORT2 = 4710
NAME2 = 'grape_test2'


@decorator
def insulate_globals(fct: Callable, *args: Any, **kwargs: Any) -> Callable:
    '''Simple decorator to insulate sys.argv.

    Args:
        fct: The function to wrap.
        args: The unnamed args.
        kwargs: The named args.

    Returns:
        wrapper: The decorated function wrapper.
    '''
    def wrapper(*args, **kwargs):
        save = sys.argv  # save the sys level args
        fct(*args, **kwargs)
        sys.argv = save  # restore the sys level args
    return wrapper


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


@insulate_globals
def test_run_01_cli(capsys: Any):
    'test the wrapper interface'
    fct = inspect.stack()[0].function  # fct name

    # Test no args.
    sys.argv = [fct]
    with pytest.raises(SystemExit) as exc:
        cli.main()
    out, err = capsys.readouterr()
    print(f'cmd=<<<{sys.argv}>>>')
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert exc.type == SystemExit
    assert exc.value.code == 0

    # test cli help and version.
    for cmd in ['help', '--help', '-h', 'version', '--version', '-V']:
        sys.argv = [fct, cmd]
        with pytest.raises(SystemExit) as exc:
            cli.main()
        out, err = capsys.readouterr()
        print(f'cmd=<<<{sys.argv}>>>')
        print(f'out=<<<{out}>>>')
        print(f'err=<<<{err}>>>')
        assert exc.type == SystemExit
        assert exc.value.code == 0

    # now test cli operations help
    for cmd in ['create', 'cr', 'delete', 'del', 'load', 'save', 'import', 'export']:
        for opt in ['-h', '--help', '-V', '--version', 'help', 'version']:
            sys.argv = [fct, cmd, opt]
            with pytest.raises(SystemExit) as exc:
                cli.main()
            out, err = capsys.readouterr()
            print(f'cmd=<<<{sys.argv}>>>')
            print(f'out=<<<{out}>>>')
            print(f'err=<<<{err}>>>')
            assert exc.type == SystemExit
            assert exc.value.code == 0

    # Test: help COMMAND
    for cmd in ['create', 'cr', 'delete', 'del', 'load', 'save', 'import', 'export']:
        sys.argv = [fct, 'help', cmd]
        with pytest.raises(SystemExit) as exc:
            cli.main()
        out, err = capsys.readouterr()
        print(f'cmd=<<<{sys.argv}>>>')
        print(f'out=<<<{out}>>>')
        print(f'err=<<<{err}>>>')
        assert exc.type == SystemExit
        assert exc.value.code == 0

    # Test bad argument handling.
    sys.argv = [fct, 'frobniz']
    with pytest.raises(SystemExit) as exc:
        cli.main()
    out, err = capsys.readouterr()
    print(f'cmd=<<<{sys.argv}>>>')
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert exc.type == SystemExit
    assert exc.value.code != 0


@insulate_globals
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
        (NAME2, GPORT2),
    ],
)
def test_run_02_delete(capsys: Any, name: str, gport: int):
    '''Delete a project.

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
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert not os.path.exists(namepg)
    assert namegr in err
    assert namepg in err
    if os.path.exists(namezp):
        os.unlink(namezp)
    assert not os.path.exists(namezp)


@insulate_globals
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_03_create(capsys: Any, name: str, gport: int):
    '''Create a project.

    The project will be used in subsequent tests.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport)]
    create.main()
    out, err = capsys.readouterr()
    script = os.path.join(namepg, 'start.sh')
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert os.path.exists(namepg)
    assert os.path.exists(script)  # make sure that the script was created
    assert namegr in err
    assert namepg in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': namegr})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': namepg})
    assert len(cpg) == 1


@insulate_globals
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_04_save(capsys: Any, name: str, gport: int):
    '''Save the project data to a zip file.

    This file will be used in the next text.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport), '-f', namezp]
    save.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert os.path.exists(namepg)
    assert os.path.exists(namezp)
    assert 'docker exec' in err
    assert '1 datasources' in err
    with ZipFile(namezp, 'r') as zfp:
        names = zfp.namelist()
        print(names)
    assert len(names) == 3
    assert 'conf.json' in names
    assert 'gr.json' in names
    assert 'pg.sql' in names


@insulate_globals
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_05_load(capsys: Any, name: str, gport: int):
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
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert namegr in err
    assert namepg in err


@insulate_globals
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
    ],
)
def test_run_06_import(capsys: Any, name: str, gport: int):
    '''Import data into the test project.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Setup.
    assert os.path.exists(namepg)
    if os.path.exists(namezp):
        os.unlink(namezp)
    xcfn = fct + '.yaml'
    with open(xcfn, 'w') as ofp:
        ofp.write(f'''\
# Grafana login.
url: http://localhost:{gport}
username: 'admin'
password: 'admin'

databases:
  - database: 'postgres'
    password: 'password'
''')
    assert os.path.exists(xcfn)

    # Run import.
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport), '-f', namezp, '-x', xcfn]
    ximport.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert namepg in err
    assert f'http://localhost:{gport}' in err
    os.unlink(xcfn)


@insulate_globals
@pytest.mark.parametrize(
    'name,gport,name2,gport2',
    [
        (NAME, GPORT, NAME2, GPORT2),
    ],
)
def test_run_07_export(capsys: Any, name: str, gport: int, name2: str, gport2: int):
    '''Export data into the test project.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
        name2: The export grape project.
        gport2: The export grafana port.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Prerequisites.
    assert os.path.exists(namepg)

    # Create the name2 container to export to.
    sys.argv = [fct, '-v', '-n', name2, '-g', str(gport2)]
    create.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert os.path.exists(NAMEPG2)
    assert namegr2 in err
    assert namepg2 in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': namegr2})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': namepg2})
    assert len(cpg) == 1

    # Setup.
    assert os.path.exists(namezp)  # the import zip.
    assert os.path.exists(namepg2)  # the export database

    xcfn = fct + '.yaml'
    with open(xcfn, 'w') as ofp:
        ofp.write(f'''\
# Grafana login.
url: http://localhost:{gport2}/
username: 'admin'
password: 'admin'

databases:
  - database: 'postgres'
    password: 'password'
''')
    assert os.path.exists(xcfn)

    # Export the primary container to it.
    sys.argv = [fct, '-v', '-n', name2, '-g', str(gport2), '-f', namezp, '-x', xcfn]
    xexport.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert namepg2 in out
    assert f'http://localhost:{GPORT2}' in out
    os.unlink(xcfn)


@insulate_globals
@pytest.mark.parametrize(
    'name,name2',
    [
        (NAME, NAME2),
    ],
)
def test_run_08_status(capsys: Any, name: str, name2: str):
    '''Check the status of the containers created in previous tests.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        name2: The export grape project.
    '''
    namegr, namepg, _namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Prerequisites.
    assert os.path.exists(namepg)
    assert os.path.exists(namepg2)

    sys.argv = [fct, '-v']
    status.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')

    client = docker.from_env()
    containers = client.containers.list(filters={'label': 'grape.type'})
    assert len(containers) >= 2


@insulate_globals
@pytest.mark.parametrize(
    'name,gport',
    [
        (NAME, GPORT),
        (NAME2, GPORT2),
    ],
)
def test_run_09_cleanup(capsys: Any, name: str, gport: int):
    '''Delete a grape project.

    It is called multiple times to clean up the test artifacts.

    Args:
        capsys: Pytest fixture for capturing stdout/stderr.
        name: The grape project name for this test.
        gport: The grafana port for this test.
    '''
    namegr, namepg, namezp = make_names(name)
    fct = inspect.stack()[0].function

    # Delete the set of resources.
    sys.argv = [fct, '-v', '-n', name, '-g', str(gport)]
    delete.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert not os.path.exists(namepg)
    assert namepg in err
    if os.path.exists(namezp):
        os.unlink(namezp)
    assert not os.path.exists(namezp)
