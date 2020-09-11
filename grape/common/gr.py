'''
Common grafana utilities.
'''
import json
from functools import reduce
import docker
import requests
from grape.common.log import info, err


def getpgip(conf: dict) -> str:
    '''
    Special handling to "fix" the url.
    Get the correct internal IP address.

    Args:
        conf - the configuration

    Returns
        The corrected IP address for the pg container.
    '''
    name = conf['gr']['cname']
    client = docker.from_env()
    containers = client.containers.list(filters={'name': name})
    if len(containers) == 0:
        err('docker container does not exist: "{name}"')
    elif len(containers) > 1:
        err('too many docker containers (>1) named "{name}"')
    rec = containers[0].attrs
    hip = rec['NetworkSettings']['Networks']['bridge']['Gateway']
    port = conf['pg']['xport']
    url =  f'{hip}:{port}'
    return url


def load_datasources(conf: dict, recs: list):
    '''
    Load the grafana datasources.

    Args:
        conf - the configuration
        recs - the grafana setup data for datasources.
    '''
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    pmap = {}
    if 'import' in conf:
        # Load the import mappings.
        for rec in conf['import']['databases']:
            rmap = {}
            for key, val in rec.items():
                if key == 'name':
                    continue
                rmap[key] = val
            name = rec['name']
            pmap[name] = rmap

    # Fill in the url for the default database.
    pgname = conf['pg']['name']
    if pgname not in pmap:
        pmap[pgname] = {
            'name': pgname,
            'url':  getpgip(conf),
            'password': conf['pg']['password']
        }

    # Update grafana.
    auth = (conf['gr']['username'], conf['gr']['password'])
    gurl = conf['gr']['url']
    for rec in recs:
        name = rec['name']
        if name in pmap:
            for key, val in pmap[name].items():
                rec[key] = val
        url = gurl + '/api/datasources'
        info(f'uploading datasource "{name}" - {url}')
        response = requests.post(url,
                                 json=rec,
                                 auth=auth,
                                 headers=headers)
        info(f'response status: {response.status_code} from {url}')
        if response.status_code not in (200, 409):
            err(f'upload failed with status {response.status_code} to {url}')


def load_folders(conf: dict, recs: list):
    '''
    Load the grafana folders.

    Args:
        conf - the configuration
        recs - the grafana setup data for folders.
    '''
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    auth = (conf['gr']['username'], conf['gr']['password'])
    gurl = conf['gr']['url']
    for rec in recs:
        name = rec['title']
        url = gurl + '/api/folders'
        info(f'uploading folder "{name}" - {url}')
        response = requests.post(url,
                                 json=rec,
                                 auth=auth,
                                 headers=headers)
        info(f'response status: {response.status_code} from {url}')
        if response.status_code not in (200, 412, 500):
            err(f'upload failed with status {response.status_code} to {url}')


def load_fmap(conf: dict, recs: list) -> dict:
    '''
    Map the grafana folders from the old ids to the new ones.

    This must be done after the new folders have been uploaded.

    Args:
        conf - the configuration
        recs - the grafana setup data for folders.

    Returns:
        The folder map.
    '''
    fmapn = {}
    for rec in recs:  # old folders
        fid = rec['id']
        title = rec['title']
        fmapn[title] = {'old': fid, 'new': -1}

    # Get the new folders.
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    auth = (conf['gr']['username'], conf['gr']['password'])
    url = conf['gr']['url'] + '/api/folders?limit=100'
    info(f'downloading folders from {url}')
    response = requests.get(url,
                            auth=auth,
                            headers=headers)
    if response.status_code != 200:
        err(f'download failed with status {response.status_code} to {url}')
    folders = response.json()  # these are the new folders

    # Now map them.
    for rec in folders:
        fid = rec['id']
        title = rec['title']
        fmapn[title]['new'] = fid

    # Map the old folder ids to the new folder ids.
    fmap = {}
    for val in fmapn.values():
        key = val['old']
        val = val['new']
        fmap[key] = val

    return fmap


def load_dashboards(conf: dict, recs: list, fmap: dict):
    '''
    Load the grafana dashboards.

    Args:
        conf - the configuration
        recs - the grafana setup data for dashboards.
        fmap - folder/title map
    '''
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    auth = (conf['gr']['username'], conf['gr']['password'])
    gurl = conf['gr']['url']
    for rec in recs:
        name = rec['dashboard']['title']
        fid = fmap[rec['folderId']]
        url = gurl + '/api/dashboards/db'
        info(f'uploading dashboard ({fid}) "{name}" - {url}')
        jrec = rec
        jrec['dashboard']['id'] = None  # create the dash board
        jrec['dashboard']['uid'] = None
        jrec['folderId'] = fid
        response = requests.post(url,
                                 json=jrec,
                                 auth=auth,
                                 headers=headers)
        info(f'response status: {response.status_code} from {url}')
        if response.status_code not in (200, 412):
            err(f'upload failed with status {response.status_code} to {url}')


def load_all(conf: dict, zgr: dict):
    '''
    Load the grafana setup.

    Args:
        conf - the configuration
        zgr - the grafana setup.
    '''
    load_datasources(conf, zgr['datasources'])
    load_folders(conf, zgr['folders'])
    load_fmap(conf, zgr['folders'])
    fmap = load_fmap(conf, zgr['folders'])
    load_dashboards(conf, zgr['dashboards'], fmap)


def read_service(burl: str, auth: tuple, service: str) -> dict:
    '''
    Read a single grafana service.

    Args:
        burl - the base URL
        auth - the auth tuple
        service - the grafana REST service

    Returns
        the JSON from the URL request
    '''
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    url = f'{burl}/{service}'
    info(f'reading {url}')
    response = requests.get(url, auth=auth, headers=headers)
    if response.status_code != 200:
        err(f'request to {url} failed with status {response.status_code}\n'
            f'{json.dumps(response.json(), indent=2)}')
    result = response.json()
    return result


def read_all_services(burl: str, auth: tuple) -> dict:
    '''
    Read the grafana state from an external server and save it.

    Args:
        burl - the base URL
        auth - the auth tuple

    Returns
        the datasources, folders and dashboards
    '''
    info('reading grafana')

    # Read the datasources.
    datasources = read_service(burl, auth, 'api/datasources')

    # Read the folders.
    folders = read_service(burl, auth, 'api/folders?limit=100')
    info(f'read {len(folders)} folders')
    fids = reduce(lambda x, y: x+[y] if not y in x else x,
                  [fid['id'] for fid in folders],
                  [])
    if not fids:
        # The General folder always exists.
        fids = [0]

    # Read the dashboards.
    dashboards = []
    for fid in fids:
        recs = read_service(burl, auth, f'api/search?folderIds={fid}')
        for rec in recs:
            uid = rec['uid']
            dash = read_service(burl, auth, f'api/dashboards/uid/{uid}')
            dash['folderId'] = fid
            dashboards.append(dash)

    result = {
        'datasources': datasources,
        'folders': folders,
        'dashboards': dashboards,
    }
    info(f'{len(result["datasources"])} datasources')
    info(f'{len(result["folders"])} folders')
    info(f'{len(result["dashboards"])} dashboards')
    return result
