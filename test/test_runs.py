'''
Test run operations like create, delete, save and load.
'''
import inspect
import os
import sys
from typing import Any
from zipfile import ZipFile
import pytest
import docker

from grape import cli
from grape import delete
from grape import create
from grape import save
from grape import load
from grape import ximport
from grape import xexport


GPORT = 4700
NAME = 'grape_test1'
NAMEGR = NAME + 'gr'
NAMEPG = NAME + 'pg'
NAMEZP = NAME + '.zip'

GPORT2 = 4710
NAME2 = 'grape_test2'
NAMEGR2 = NAME2 + 'gr'
NAMEPG2 = NAME2 + 'pg'
NAMEZP2 = NAME2 + '.zip'


def test_run_00_cli(capsys: Any):
    'test the wrapper interface'
    sargs = sys.argv
    fct = inspect.stack()[0].function

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

    sys.argv = sargs


def test_run_01_delete(capsys: Any):
    'start delete'
    sargs = sys.argv
    fct = inspect.stack()[0].function

    # Delete the primary set of resources.
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT)]
    delete.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert not os.path.exists(NAMEPG)
    assert NAMEGR in err
    assert NAMEPG in err
    if os.path.exists(NAMEZP):
        os.unlink(NAMEZP)
    assert not os.path.exists(NAMEZP)

    # Now delete the second set of recources.
    sys.argv = [fct, '-v', '-n', NAME2, '-g', str(GPORT2)]
    delete.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert not os.path.exists(NAMEPG2)
    assert NAMEGR2 in err
    assert NAMEPG2 in err
    if os.path.exists(NAMEZP2):
        os.unlink(NAMEZP2)
    assert not os.path.exists(NAMEZP2)
    sys.argv = sargs


def test_run_02_create(capsys: Any):
    'create'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT)]
    create.main()
    out, err = capsys.readouterr()
    script = f'{NAMEPG}/start.sh'
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert os.path.exists(NAMEPG)
    assert os.path.exists(script)  # make sure that the script was created
    assert NAMEGR in err
    assert NAMEPG in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': NAMEGR})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': NAMEPG})
    assert len(cpg) == 1
    sys.argv = sargs


def test_run_03_save(capsys: Any):
    'save'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT), '-f', NAMEZP]
    save.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert os.path.exists(NAMEPG)
    assert os.path.exists(NAMEZP)
    assert 'docker exec' in err
    assert '1 datasources' in err
    with ZipFile(NAMEZP, 'r') as zfp:
        names = zfp.namelist()
        print(names)
    assert len(names) == 3
    assert 'conf.json' in names
    assert 'gr.json' in names
    assert 'pg.sql' in names
    sys.argv = sargs


def test_run_04_load(capsys: Any):
    'load'
    assert os.path.exists(NAMEPG)
    assert os.path.exists(NAMEZP)
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT), '-f', NAMEZP]
    load.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert NAMEGR in err
    assert NAMEPG in err
    sys.argv = sargs


def test_run_05_import(capsys: Any):
    'save'
    sargs = sys.argv
    fct = inspect.stack()[0].function

    # Setup.
    assert os.path.exists(NAMEPG)
    if os.path.exists(NAMEZP):
        os.unlink(NAMEZP)
    xcfn = fct + '.yaml'
    with open(xcfn, 'w') as ofp:
        ofp.write(f'''\
# Grafana login.
url: http://localhost:{GPORT}
username: 'admin'
password: 'admin'

databases:
  - database: 'postgres'
    password: 'password'
''')
    assert os.path.exists(xcfn)

    # Run import.
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT), '-f', NAMEZP, '-x', xcfn]
    ximport.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert NAMEPG in err
    assert f'http://localhost:{GPORT}' in err
    os.unlink(xcfn)
    sys.argv = sargs


def test_run_06_export(capsys: Any):
    'test export'

    sargs = sys.argv
    fct = inspect.stack()[0].function

    # Create the NAME2 container to export to.
    sys.argv = [fct, '-v', '-n', NAME2, '-g', str(GPORT2)]
    create.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert os.path.exists(NAMEPG2)
    assert NAMEGR2 in err
    assert NAMEPG2 in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': NAMEGR2})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': NAMEPG2})
    assert len(cpg) == 1

    # Setup.
    assert os.path.exists(NAMEZP)  # the import zip.
    assert os.path.exists(NAMEPG2)  # the export database

    xcfn = fct + '.yaml'
    with open(xcfn, 'w') as ofp:
        ofp.write(f'''\
# Grafana login.
url: http://localhost:{GPORT2}/
username: 'admin'
password: 'admin'

databases:
  - database: 'postgres'
    password: 'password'
''')
    assert os.path.exists(xcfn)

    # Export the primary container to it.
    sys.argv = [fct, '-v', '-n', NAME2, '-g', str(GPORT2), '-f', NAMEZP, '-x', xcfn]
    xexport.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert NAMEPG2 in out
    assert f'http://localhost:{GPORT2}' in out
    os.unlink(xcfn)
    sys.argv = sargs


def test_run_07_delete(capsys: Any):
    'end with delete'
    sargs = sys.argv
    fct = inspect.stack()[0].function

    # Delete the primary set of resources.
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT)]
    delete.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert not os.path.exists(NAMEPG)
    assert NAMEPG in err
    if os.path.exists(NAMEZP):
        os.unlink(NAMEZP)
    assert not os.path.exists(NAMEZP)

    # Now delete the second set of recources.
    sys.argv = [fct, '-v', '-n', NAME2, '-g', str(GPORT2)]
    delete.main()
    out, err = capsys.readouterr()
    print(f'out=<<<{out}>>>')
    print(f'err=<<<{err}>>>')
    assert not os.path.exists(NAMEPG2)
    assert NAMEGR2 in err
    assert NAMEPG2 in err
    if os.path.exists(NAMEZP2):
        os.unlink(NAMEZP2)
    assert not os.path.exists(NAMEZP2)

    sys.argv = sargs
