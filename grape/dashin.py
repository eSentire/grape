'''
Implements the dashin command.

See the common/dashio.py file for more details about the
dashin/dashout flow. It is documented in a single place
because dashin/dashout are so closely intertwined. One
does not make sense with the other.

Note that dashin cannot import directly from external grafana
server. The inability to do that was an intentional design decision
that resulted from considering the complexity of different authn/z
schemes (usernames, passwords, roles, etc.) that might exist for any
external grafana server. This system understands how to interact with
grape grafana servers for authn/z. It does not know how to interact
with other grafana servers for authn/z.
'''
import argparse
import json
import os
import sys
from typing import Any

import requests

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err, warn, debug
from grape.common.conf import DEFAULT_AUTH
from grape.common.dashio import read_template, write_dash
from grape.common.json import read_json_dict_from_file
from grape import __version__


def getopts() -> argparse.Namespace:
    '''Get the command line options.

    Returns:
        opts: The command line options.
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
    # Example 2: Import a grafana dashboard JSON file
    #            into a grape project and then observe
    #            it in the tree dump. THe dash.json was
    #            created by the user.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -j dash.json -u -g 4600 -D CUSTOM_DS=myprojectpg
        $ {2} tree -g 4600

    # ------------------------------------------------
    # Example 3: Import a grafana dashboard JSON file
    #            into a local JSON file.
    #            The -f option says to write to a file.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -j dash.json -f newdash.json -D CUSTOM_DS=myprojectpg

    # ------------------------------------------------
    # Example 4: Import a grafana dashboard JSON file
    #            (dash.json), change it in the grafana
    #            UI and then upload it to newdash.json.
    #
    #            Note that the dashout command does
    #            not accept a value for the variable.
    #            If a value is supplied, it is ignored.
    #
    #            Also note that the dashout command
    #            requires the dashboard id which is
    #            reported by the tree command.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -j dash.json -g 4600 -D CUSTOM_DS=myprojectpg
        $ # Do stuff in the grafana ui.
        $ {2} tree -g 4600  # tree view gets the dasboard id (-d)
        $ {2} dashout -g 4600 -d 3 -f newdash.json -D CUSTOM_DS

VERSION:
   {1}
'''.format(base, __version__, CLI).strip()
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog.rstrip() + '\n ')
    add_common_args(parser, '-D', '-f', '-g', '-i', '-j', '-t', '-u')
    opts = parser.parse_args()
    return opts


def read_raw_json(opts: argparse.Namespace) -> dict:
    '''Read the raw JSON.

    Args:
        opts: The command line arguments.

    Returns:
        dash: The initial JSON dashboard. It is guaranteed to be a dict.
    '''
    info(f'reading {opts.json}')
    return read_json_dict_from_file(opts.json)


def setvar(data: Any, name: str, value: Any) -> Any:
    '''Set a data value based on a variable name.

    This function walks through JSON structure and replaces
    a variable name with a value.

    For example, assume that this is the input data:
        {
           "name": "{{NAME}}"
           "path": "/here/there/{{NAME}}/everywhere"
        }

    If the variable name is "{{NAME}}" and the value is "foobar",
    the result of this operation would be:
        {
           "name": "foobar"
           "path": "/here/there/foobar/everywhere"
        }

    Although example above uses strings for the variable value that is
    misleading because the value can be anything including nested
    JSON.

    Args:
        data: The dataset.
        name: The name to replace. Typically something like {{DASH}}.
        value: The value to replace it with.

    Returns:
        updated: The updated data.
    '''
    if isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = setvar(item, name, value)
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, str):
                if name == val:
                    data[key] = value  # Allow change of type.
                elif name in val:
                    data[key] = val.replace(name, str(value))
            elif isinstance(val, (list, tuple, dict)):
                data[key] = setvar(val, name, value)
    elif isinstance(data, str):
        string = str(data)
        if string == name:
            data = value  # Allow change of type.
        elif name in string:
            data = str(data).replace(name, str(value))
    return data


def wrapit(dash: dict, template: dict) -> dict:
    '''Add the wrapper if it is not already present.

    This is interesting because it uses a template so
    that modifying it in the future does not require
    a code change.

    Args:
        dash: The unwrapped initial dashboard.
        template: The template.

    Returns:
        dash: The updated dashboard.
    '''
    wrapper = template['wrapper']
    setw = set(wrapper)
    setd = set(dash)
    if setw.issubset(setd):
        # All of the keys in the wrapper are defined so
        # we assyne that the wrapper is already defined.
        return dash
    info('wrapping dashboard')
    updated = setvar(wrapper, '{{DASH}}', dash)
    debug(f'updated:\n{json.dumps(updated, indent=4, sort_keys=True)}')
    return updated


def setvars(opts: argparse.Namespace, dash: dict, template: dict) -> dict:
    '''Set the variable values.

    The datasource variable values are specified on the command line.

    Args:
        opts: The command line arguments.
        dash: The unwrapped initial dashboard.
        template: The template.

    Returns:
        dash: The updated dashboard.
    '''
    info('setting the variables')
    new_dash = dash

    # Fix the id and uid.
    if 'id' in new_dash:
        new_dash['id'] = None
    if 'uid' in new_dash:
        new_dash['uid'] = None

    # Load the datasource variables.
    dsvars = {}
    if 'dashboard' in dash:
        ddash = dash['dashboard']
        if '__inputs' in ddash:
            for var in ddash['__inputs']:
                if var['type'] == 'datasource':
                    key = var['name']
                    value = var['pluginName']
                    dsvars[key] = value
                    info(f'   found datasource variable in dashboard: {key}="{value}"')

    if not opts.vardefs:
        # No variables defined.
        if dsvars:
            warn(f'need to define this variables {dsvars}')
        return new_dash

    # Create the variable scaffolding.
    vkey0 = template['meta']['vkey0']
    vkey1 = template['meta']['vkey1']
    if vkey0 not in new_dash:
        # Add the variable scaffolding.
        new_dash[vkey0] = {
            vkey1: []
        }
    assert vkey1 in new_dash[vkey0]

    # Process all of the command line variables.
    tds = template['datasource']
    for variable in opts.vardefs:
        if '=' not in variable:
            err(f'invalid variable specification, it must have a value: {variable}')
        name, value = variable.split('=', 1)
        info(f'   creating variable {name} with value "{value}"')
        if name not in dsvars:
            warn(f'variable "{name}" is not defined in dashboard json')
        new_var = setvar(tds, '{{PGDS}}', value)
        new_var = setvar(new_var, '{{PGNM}}', name)
        # Always insert at the beginning of the list.
        # This O(N) operation is okay because the list
        # is typically very small.
        new_dash['dashboard'][vkey0][vkey1].insert(0, new_var)

    debug(f'new_dash:\n{json.dumps(new_dash, indent=4, sort_keys=True)}')
    return new_dash


def write_to_grafana(opts: argparse.Namespace, dash: dict):
    '''Write the dashboard to the grape grafana server.

    This uses the -g option to figure out where to write to when the
    -u option is specified.

    The -g option has a default so it is impossible to detect the case
    where no upload is wanted.

    Args:
        opts: The command line arguments.
        dash: The unwrapped initial dashboard.
    '''
    if not opts.upload:
        return
    burl = f'http://127.0.0.1:{opts.grxport}'
    info('upload to {burl}')
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    auth = DEFAULT_AUTH
    try:
        url = burl + '/api/datasources'
        response = requests.post(burl,
                                 json=dash,
                                 auth=auth,
                                 headers=headers)
    except requests.ConnectionError as exc:
        err(str(exc))
    info(f'response status: {response.status_code} from {url}')
    if response.status_code not in (200, 400, 412):
        err(f'upload failed with status {response.status_code} to {url}')


def main():
    '''Dashin command main.

    This is the command line entry point for the dash command.

    Add scaffolding to a grafana JSON dashboard description extracted
    from an internal server so that it can be imported into a local
    grafana server for updating. It does this by adding scaffolding to
    make it importable.
    '''
    opts = getopts()
    initv(opts.verbose)
    info('dashin')
    template = read_template(opts)
    dash = read_raw_json(opts)
    new_dash = wrapit(dash, template)
    new_dash = setvars(opts, new_dash, template)
    write_dash(opts, new_dash)
    write_to_grafana(opts, new_dash)
    info('done')
