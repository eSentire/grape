'''
Implements the dashin command.

See the common/dashio.py file for more details about the
dashin/dashout flow. It is documented in a single place
because dashin/dashout are so closely intertwined. One
does not make sense with the other.

Note that dashout cannot export directly to an external grafana
server. The inability to do that was an intentional design decision
that resulted from considering the complexity of different authn/z
schemes (usernames, passwords, roles, etc.) that might exist for any
external grafana server. This system understands how to interact with
grape grafana servers for authn/z. It does not know how to interact
with other grafana servers for authn/z.
'''
import argparse
import os
import sys
from typing import List

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err, warn
from grape.common.conf import DEFAULT_AUTH
from grape.common.gr import read_all_services
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
    # Example 2: Export a grafana dashboard JSON file
    #            from a grape project to that it can
    #            be uploaded to an external server
    #            manually using curl, postman or the
    #            grafana UI in the external server.
    #
    #            Run the status and tree commands to
    #            get the dashboard id (-d).
    #
    #            Note that only the variable name is needed.
    # ------------------------------------------------
        $ {2} status -v  # figure out the port
        $ {2} tree -g 4600  # get the dashboard id
        $ {2} {0} -f updated-dash.json -d 4 -g 4600 -D CUSTOM_DS

    # ------------------------------------------------
    # Example 3: Test the conversion from end to end
    #            using external dashboard JSON file.
    # ------------------------------------------------
        $ {2} dashin -j external-dash.json -f augmented-dash.json -D CUSTOM_DS=myprojectpg
        $ {2} dashout -j augmented-dash.json -f updated-dash.json -D CUSTOM_DS
        $ diff -w external-dash.json updated-dash.json

VERSION:
   {1}
'''.format(base, __version__, CLI).strip()
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog.rstrip() + '\n ')
    add_common_args(parser, '-d', '-D', '-f', '-g', '-i', '-j', '-t', '-u')
    opts = parser.parse_args()
    return opts


def read_local_dashboard(opts: argparse.Namespace) -> dict:
    '''Read the local dashboard.

    There are two ways to read the dashboard, from the server
    directly using the -g option setting or from a JSON file (-j).

    Args:
        opts: The command line arguments.

    Returns:
        dash: The local JSON dashboard with the scaffolding that needs
            to be removed.
    '''
    info('read local dashboard')
    dash = {}
    if opts.json:
        # Read from a local file.
        # This will have the scaffolding.
        dash = read_json_dict_from_file(opts.json)
    else:
        # The user wants us to read the dashboard from a grape server.
        if not opts.dashid:
            err(f'the dashboard id must be specified for port {opts.grxport}')
        burl = f'http://127.0.0.1:{opts.grxport}'
        auth = DEFAULT_AUTH
        services = read_all_services(burl, auth)
        if 'dashboards' in services:
            for item in services['dashboards']:
                if 'dashboard' in item:
                    dashboard = item['dashboard']
                    if dashboard['id'] == opts.dashid:
                        # This strips off the wrapper scaffolding.
                        dash = dashboard
                        break
        if not dash:
            err(f'could not find dashboard with id: {opts.dashid}')
    return dash


def strip_wrapper(dash: dict, template: dict) -> dict:
    '''Strip the wrapper scaffolding.

    Args:
        dash: The dashboard that is to be stripped.
        template: The scaffolding template.

    Returns:
        dashout: The dashboard with the wrapper scaffolding stripped.
    '''
    key = template['meta']['dkey']
    if key in dash:
        # The template tells us that this is where the
        # template dashboard data is found.
        return dash[key]

    # This is likely the special case where the scaffolding was
    # already stripped.
    return dash


def get_vname_key(template: dict) -> str:
    '''Find the key that contains the reference to the variable name.

    This information is used later when searching the live data.

    There can be more than one but only one is needed.

    Args:
        template: The scaffolding template.

    Returns:
        vkey: The variable key.
    '''
    for key, var in template['datasource'].items():
        if '{{PGNM}}' in var:
            vkey = key
            break  # only need the first one

    if not vkey:
        # Something is wrong with the template.
        # This could also occur because the path is deeper than one
        # but that is not supported yet.
        err('invalid template: cannot find a key that references the name variable {{PGNM}}')

    return vkey


def get_vnames(opts: argparse.Namespace) -> List[str]:
    '''Get the variable names from the command line.

    These names are used find the variables to delete.

    Args:
        opts: The command line arguments.

    Returns:
        list: The list of variable names.
    '''
    vnames = []
    for variable in opts.vardefs:
        if '=' in variable:
            warn(f'the value is not needed and is ignored for {variable}')
            name, _ = variable.split('=', 1)
        else:
            name = variable
        vnames.append(name)

    if not vnames:
        err('no datasource variable name specified')

    return vnames


def strip_scaffolding(opts: argparse.Namespace, dash: dict, template: dict) -> dict:
    '''Strip the scaffolding from the dashboard.

    The input dashboard can can some or all of the scaffolding
    already stripped so we have to be careful.

    Args:
        opts: The command line arguments.
        dash: The dashboard that is to be stripped.
        template: The scaffolding template.

    Returns:
        dashout: The stripped dashboard.
    '''
    info('strip_scaffolding')

    new_dash = strip_wrapper(dash, template)
    vkey = get_vname_key(template)
    vnames = get_vnames(opts)

    # The heart of the matter.
    # Find the variables to delete by comparing
    # key names that contain the variable names
    # with the variable names specified in the
    # command line.
    vkey0 = template['meta']['vkey0']
    vkey1 = template['meta']['vkey1']
    try:
        vlist = new_dash[vkey0][vkey1]
        to_delete = []
        for i, vdef in enumerate(vlist):
            if vkey not in vdef:
                continue
            for vname in vnames:
                if vname in vdef[vkey]:
                    to_delete.append(i)
                    break
        # This only works for descending order.
        for i in reversed(to_delete):
            del new_dash[vkey0][vkey1][i]
    except KeyError:
        pass

    return new_dash


def main():
    '''Dashout command main.

    This is the command line entry point for the dash command.

    Export a single grafana dashboard to JSON and remove the
    scaffolding added by the dashin command so that it can be exported
    to an external grafana server.
    '''
    opts = getopts()
    initv(opts.verbose)
    info('dashout')

    # The template definition specifies what needs to be removed.
    template = read_template(opts)
    dash = read_local_dashboard(opts)
    new_dash = strip_scaffolding(opts, dash, template)
    write_dash(opts, new_dash)
#    write_to_grafana(opts, new_dash)
    info('done')
