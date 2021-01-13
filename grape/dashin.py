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

When you are finished working on the dashboard you can export
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
import os
import sys

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info
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
    #            it in the tree dump.
    #            The -g option says to write to a project.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -g 4600 -j dash.json -D CUSTOM_DS=myprojectpg
        $ {2} tree -g 4600

    # ------------------------------------------------
    # Example 3: Import a grafana dashboard JSON file
    #            into a local JSON file.
    #            The -f option says to write to a file.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -f newdash.json -j dash.json -D CUSTOM_DS=myprojectpg

    # ------------------------------------------------
    # Example 4: Import a grafana dashboard JSON file
    #            (dash.json) into a grape project.
    #            Change it in the grafana UI and then
    #            export it to newdash.json.
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
        $ {2} {0} -g 4600 -j dash.json -D CUSTOM_DS=myprojectpg
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
    add_common_args(parser, '-f', '-g', '-i', '-s')
    opts = parser.parse_args()
    return opts


def main():
    '''Dashin command main.

    This is the command line entry point for the dash command.

    Import a JSON description of a dashboard.
    '''
    opts = getopts()
    initv(opts.verbose)
    info('dashin')
#    container = check_port(opts.grxport)
#    burl = f'http://127.0.0.1:{opts.grxport}'
#    name = container.name + ':' + str(opts.grxport)
#    top = collect(burl, DEFAULT_AUTH, name)
#    if opts.fname:
#        with open(opts.fname, 'w') as ofp:
#            print_tree(opts, ofp, top)
#    else:
#        print_tree(opts, sys.stdout, top)
