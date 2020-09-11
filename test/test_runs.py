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


GPORT = 4700
NAME = 'grape_test'
NAMEGR = NAME + 'gr'
NAMEPG = NAME + 'pg'
NAMEZP = NAME + '.zip'


def test_run_00_cli(capsys: Any):
    'test the wrapper as well as help and version feedback'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    for cmd in ['create', 'delete', 'load', 'save', 'import', 'export']:
        for opt in ['-h', '--help', '-V', '--version']:
            sys.argv = [fct, cmd, opt]
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.type == SystemExit
            assert exc.value.code == 0
            out, err = capsys.readouterr()
            print(f'out="{out}"')
            print(f'err="{err}"')
            assert 'grape' in out
    sys.argv = sargs


def test_run_01_delete(capsys: Any):
    'start delete'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT)]
    delete.main()
    _out, err = capsys.readouterr()
    sys.argv = sargs
    assert not os.path.exists(NAMEPG)
    assert NAMEGR in err
    assert NAMEPG in err
    if os.path.exists(NAMEZP):
        os.unlink(NAMEZP)
    assert not os.path.exists(NAMEZP)


def test_run_02_create(capsys: Any):
    'create'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT)]
    create.main()
    _out, err = capsys.readouterr()
    sys.argv = sargs
    assert os.path.exists(NAMEPG)
    assert NAMEGR in err
    assert NAMEPG in err
    client = docker.from_env()
    cgr = client.containers.list(filters={'name': NAMEGR})
    assert len(cgr) == 1
    cpg = client.containers.list(filters={'name': NAMEPG})
    assert len(cpg) == 1


def test_run_03_save(capsys: Any):
    'save'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT), '-f', NAMEZP]
    save.main()
    _out, err = capsys.readouterr()
    sys.argv = sargs
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


def test_run_04_load(capsys: Any):
    'load'
    assert os.path.exists(NAMEPG)
    assert os.path.exists(NAMEZP)
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT), '-f', NAMEZP]
    load.main()
    _out, err = capsys.readouterr()
    sys.argv = sargs
    assert NAMEGR in err
    assert NAMEPG in err


def test_run_05_import(capsys: Any):
    'save'
    assert os.path.exists(NAMEPG)
    if os.path.exists(NAMEZP):
        os.unlink(NAMEZP)
    fct = inspect.stack()[0].function
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
    sargs = sys.argv
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT), '-f', NAMEZP, '-x', xcfn]
    ximport.main()
    _out, err = capsys.readouterr()
    sys.argv = sargs
    print(f'err="{err}"')
    assert NAMEPG in err
    assert f'http://localhost:{GPORT}' in err
    os.unlink(xcfn)


def test_run_06_delete(capsys: Any):
    'end with delete'
    sargs = sys.argv
    fct = inspect.stack()[0].function
    sys.argv = [fct, '-v', '-n', NAME, '-g', str(GPORT)]
    delete.main()
    _out, err = capsys.readouterr()
    sys.argv = sargs
    assert not os.path.exists(NAMEPG)
    assert NAMEPG in err
    if os.path.exists(NAMEZP):
        os.unlink(NAMEZP)
    assert not os.path.exists(NAMEZP)
