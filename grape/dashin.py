# pylint: disable=line-too-long
'''
Dashin translates a dashboard JSON file exported from an external
grafana server into a dashboard in a grape grafana server.

It does this by wrapping the dashboard description with the following
scaffolding:
   {
     "dashboards": <input-JSON>,
      "folderId": 0,
      "overwrite": true
   }

It also defines datasource variables by adding them to the
dashboard "templating" section. If the input JSON references
a datasource variable named: `${COOL_DS}` (for cool datasource)
and your grape datasource name is `myprojectgr` then this
process would create the following variable definition:

    {
      "current": {
        "selected": false,
        "text": "myprojectgr",
        "value": "myprojectgr"
      },
      "hide": 2,
      "includeAll": false,
      "label": null,
      "multi": false,
      "name": "CLARITY_DS",
      "options": [],
      "query": "postgres",
      "refresh": 1,
      "regex": "myprojectgr",
      "skipUrlSync": false,
      "type": "datasource"
  }

The scaffolding and the variables are removed by the dashout
command.

The input is a JSON file and description of the variables and
values. Here is an example:

   $ grape dashin -j external-dashboard.json -D COOL_DS=myprojectgr

When you are finished working on the dashboard you can upload
it using the dashout command like this:

   $ # Get the grape projects that are running.
   $ pipenv run grape status -v
   INFO 2021-01-11 18:08:42,447 status.py:187 - status
     Name   Type  Version  Status   Started              Elapsed   Id          Image              Created              Port
     jbhgr  gr    0.4.3    running  2021-01-11T16:47:24  09:21:18  5368be647f  sha256:9ad3ce931a  2021-01-11T16:47:24  4640
     jbhpg  pg    0.4.3    running  2021-01-11T16:47:24  09:21:17  7cf96782d7  sha256:0b0b68fee3  2021-01-11T16:47:24  4641
   INFO 2021-01-11 18:08:42,498 status.py:222 - done

   $ # Get the dashboard id from the status report.
   $ pipenv run grape tree -g 4640
   jbhgr:4640
     ├─ datasources
     │   └─ jbhpg:id=1:ty[e=postgres
     └─ folders
         ├─ JBH:1
         │   └─ dashboards
         │       ├─ Northstar Dashboard Mock:id=5:uid=lC0QCuaMz:panels=33
         │       └─ OKR Initiatives Health:id=6:uid=peAwjuaMk:panels=6
         └─ Northstar:2
             └─ dashboards
                 ├─ Jenkins Build Health Details:id=4:uid=ir0QjX-Mz:panels=9
                 └─ Jenkins Build Health:id=3:uid=6Q0QCuaGk:panels=70

   $ grape dashout -g 4640 -d 4 -f updated-external-dashboard.json -D COOL_DS
'''
# pylint: enable=line-too-long
import argparse
import json
import os
import sys
from typing import Any

import requests

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err, warn, debug
from grape.common.conf import DEFAULT_AUTH
from grape import __version__


# The default template settings.
# The user can override this with the -t option.
# Variables in the template are:
#    {{DASH}}  The dashboard JSON.
#    {{PGDS}}  The name of the grape data source.
#    {{PGNM}}  The name of the grape data source variable.
DEFAULT_TEMPLATE : dict = {
    # This is the wrapper for the dashboard.
    "wrapper": {
        "dashboard": "{{DASH}}",
        "folderId": 0,
        "overwrite": True
    },
    "datasource": {
        # This is the definition of a datasource variable.
        "current": {
            "selected": False,
            "text": "{{PGDS}}",
            "value": "{{PGDS}}"
        },
        "hide": 2,
        "includeAll": False,
        "label": None,
        "multi": False,
        "name": "{{PGNM}}",
        "options": [],
        "query": "postgres",
        "refresh": 1,
        "regex": "{{PGDS}}",
        "skipUrlSync": False,
        "type": "datasource"
    }
}


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
    #            it in the tree dump.
    #            The -g option says to write to a project.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -j dash.json -g 4600 -D CUSTOM_DS=myprojectpg
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
    value = {}
    try:
        with open(opts.json) as ifp:
            data = ifp.read()
            if data.startswith('['):
                err(f'input dashboard json file is a list not a map: "{opts.json}"')
            if not data.startswith('{'):
                # It must be a dictionary.
                err(f'input dashboard json file is not a map: "{opts.json}"')
        value = json.loads(data)
    except FileNotFoundError:
        err(f'input dashboard json file does not exist: "{opts.json}"')
    except json.decoder.JSONDecodeError as exc:
        err(f'input dashboard json file is invalid: "{opts.json}" - {exc}')
    return value


def read_template(opts: argparse.Namespace) -> dict:
    '''Read the dashboard template.

    This template contains the wrapper and variable
    settings (as code) that are used to augment the
    data.

    See the comments for the DEFAULT_TEMPLATE for
    more details about the structure.

    Args:
        opts: The command line arguments.

    Returns:
        template: The template.
    '''
    path = opts.template
    if not path:
        info('using default internal template')
        template = DEFAULT_TEMPLATE
    else:
        info(f'reading {opts.template}')
        try:
            with open(path) as ifp:
                template = json.load(ifp)
        except FileNotFoundError:
            err(f'dashboard template file does not exist: "{opts.template}"')
        except json.decoder.JSONDecodeError as exc:
            err(f'dashboard template file is invalid: "{opts.template}" - {exc}')
    if 'wrapper' not in template:
        err('missing expected key in the template')
    if 'datasource' not in template:
        err('missing expected key in the template')
    return template


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
    if 'templating' not in new_dash:
        # Add the variable scaffolding.
        new_dash['templating'] = {
            'list': []
        }

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
        new_dash['dashboard']['templating']['list'].insert(0, new_var)

    debug(f'new_dash:\n{json.dumps(new_dash, indent=4, sort_keys=True)}')
    return new_dash


def dump_new_dash(opts: argparse.Namespace, dash: dict):
    '''Dump new dash.

    This is only done if -f is specified.

    Args:
        opts: The command line arguments.
        dash: The unwrapped initial dashboard.
    '''
    if not opts.fname:
        return
    info(f'writing updated dashboard JSON to {opts.fname}')
    with open(opts.fname, 'w') as ofp:
        string = json.dumps(dash, indent=4, sort_keys=True)
        ofp.write(string + '\n')


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

    Import a JSON description of a dashboard.
    '''
    opts = getopts()
    initv(opts.verbose)
    info('dashin')
    template = read_template(opts)
    dash = read_raw_json(opts)
    new_dash = wrapit(dash, template)
    new_dash = setvars(opts, new_dash, template)
    dump_new_dash(opts, new_dash)
    write_to_grafana(opts, new_dash)
    info('done')
