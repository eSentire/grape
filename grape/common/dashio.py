# pylint: disable=line-too-long
'''
Common stuff for dashin and dashout.

When an dashboard is exported from an grafana server for use in a
local development environment with a different data source, it cannot
be directly imported for two reasons: 1) it is missing some JSON
scaffolding that defines it as a dashboard for import and it is
missing a definition for the data source (a variable definition). This
makes it hard to import and export dashboards because the developer
has to fiddle with the raw JSON.

The dashin translates a dashboard JSON file exported from an external
grafana server into a dashboard in a grape grafana server by adding
the scaffolding and the data source variable.

The scaffolding and data source variable definition are defined by the
DEFAULT_TEMPLATE defined below. It can be overwritten by specifying
the -t option. This is primitive attempt to future proof this
functionality as Grafana evolves.

When this operation completes, the dashboard will be available in
the users local grape development environment.

When the user has finished making changes to the dashboard, it
can be re-formatted by using the dashout command which removes
the scaffolding and variable definitions to allow it to be
added to the external grafana server.

Note that the grape 'status' and 'tree' commands are very useful
for finding local grape servers and folder ids.

Here is an example of how to import an external dashboard JSON file
using dashin and store the result in a local JSON file that can later
be imported into the local grafana server manually.

   $ grape dashin -j external-dashboard.json -D COOL_DS=myprojectgr -f local.json

Here is an example of how to load the external dashboard JSON file
directly into the local grafana server.

   $ grape dashin -j external-dashboard.json -D COOL_DS=myprojectgr -g 5400 -u

You might need to use the status and tree commands to get information about
local grape projects.

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

   $ # Create the updated dashboard JSON file.
   $ # It must be manually imported in the external grafana server
   $ # because grape does not understand the authn/z protocols for
   $ # external servers.
   $ grape dashout -g 4640 -d 4 -f updated-external-dashboard.json -D COOL_DS
'''
# pylint: enable=line-too-long
import argparse
import json

from grape.common.log import info, err


# The default template settings.
#
# The user can override this with the -t option.
#
# The same template definition must be used for both dashin and
# dashout.
#
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
    },
    "meta": {
        # Variable that references the list where the datasource
        # variables are stored.
        "vkey0": 'templating',  # dashboard['templating']
        "vkey1": 'list',  # dashboard['templating']['list']

        # Variable the tells where the dashboards data is stored.
        "dkey": "dashboard",

        "version": 1,  # schema version
    }
}


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


def write_dash(opts: argparse.Namespace, dash: dict):
    '''Write out the dashboard data.

    This is only done if -f is specified.

    Args:
        opts: The command line arguments.
        dash: The unwrapped initial dashboard.
    '''
    if not opts.fname:
        return
    info(f'writing dashboard JSON to {opts.fname}')
    with open(opts.fname, 'w') as ofp:
        string = json.dumps(dash, indent=opts.indent, sort_keys=True)
        ofp.write(string + '\n')
