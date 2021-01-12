#!/usr/bin/env python
'''
Tree like dump of the grafana data.

Typically this would be used with the status operation where the
status operations reports the available ports as follows:

   $ pipenv run grape state -v  # see the available projects
   $ pipenv run grape tree -g 4600
'''
from __future__ import annotations
import argparse
import os
import sys
from typing import List, Optional, TextIO, Tuple

import docker  # type: ignore
from docker.models.containers import Container  # type: ignore

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err
from grape.common.gr import read_all_services
from grape.common.conf import DEFAULT_AUTH
from grape import __version__


class TreeNode:
    '''Report tree nodes.

    The tree structure is used for the reporting the data in tree
    format.
    '''
    def __init__(self, value: str, parent : Optional[TreeNode] = None):
        '''Create a node.

        This is the only way to add a node to the tree.
        At present there is no way to remove a node.

        The endmost is flag is used to determine the prefix when
        building the tree display.

        Args:
            value: The value of the node.
            parent: The parent node. This is optional but only for the
                root of the tree.

        Returns:
            node: A tree node object.
        '''
        self._value = value
        self._children : List[TreeNode] = []
        self._parent : Optional[TreeNode] = parent
        self._islast = True
        if parent:
            parent._children.append(self)
            if len(parent._children) > 1:
                parent._children[-2]._islast = False

    @property
    def value(self) -> str:
        'value'
        return self._value

    @property
    def parent(self) -> Optional[TreeNode]:
        'parent'
        return self._parent

    @property
    def children(self) -> List[TreeNode]:
        'children'
        return self._children

    @property
    def islast(self) -> bool:
        'is this the last child?'
        return self._islast

    def get(self, value: str) -> Optional[TreeNode]:
        'get child by name'
        for child in self._children:
            if child.value == value:
                return child
        return None

    def sort(self) -> TreeNode:
        'sort in place'
        if self._children:
            self._children = sorted(self._children, key=lambda x: x.value.lower())
            for child in self._children:
                child.sort()
                child._islast = False  # pylint: disable=protected-access
            self._children[-1]._islast = True  # pylint: disable=protected-access
        return self

    def __lt__(self, other: TreeNode) -> bool:
        'compare lt'
        return self._value < other._value

    def __eq__(self, other: object) -> bool:
        'compare eq'
        if isinstance(other, TreeNode):
            return self._value == other._value
        return False

    def __str__(self) -> str:
        'sortable'
        sortable = self._value + ','.join([x._value for x in self._children])
        return sortable

    def prefix(self, indent: int=3) -> str:
        'get the indent prefix'
        prefixes = []
        if self.parent:
            left = ''
            right0 = ''
            right1 = ''
            half = indent // 2
            if half:
                blanks = ''.join([' ' for _ in range(half)])
                left = blanks
                if indent % 2:
                    left += ' '
                right0 = blanks
                right1 = ''.join(['\u2500' for _ in range(half)])

            if self._islast:
                symbol = '\u2514'  # L
            else:
                symbol = '\u251c'  # |-
            prefix = f'{left}{symbol}{right1}'
            prefixes.append(prefix)

            # Children.
            node = self._parent
            while node:
                if node.parent:
                    if node.islast:
                        symbol = ' '
                    else:
                        symbol = '\u2502'  # |
                    prefix = f'{left}{symbol}{right0}'
                    prefixes.append(prefix)
                node = node.parent
                assert len(prefixes) < 64

        # Write out the node.
        prefix = ''.join(reversed(prefixes))
        return prefix

    def dump(self, level: int=0, ofp: TextIO = sys.stdout, indent: int=3):
        'dump the tree'
        prefix = self.prefix(indent)
        ofp.write(prefix)
        if level:
            ofp.write(' ')
        ofp.write(self.value)
        ofp.write('\n')

        # Process the children.
        for child in self._children:
            child.dump(level+1, ofp, indent)


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
    # Example 2: Tree representation for a grafana server.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -g 4600

    # ------------------------------------------------
    # Example 3: With indent level 4.
    # ------------------------------------------------
        $ {2} status -v
        $ {2} {0} -i 4 -g 4600

VERSION:
   {1}
'''.format(base, __version__, CLI).strip()
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog.rstrip() + '\n ')
    parser.add_argument('-i', '--indent',
                        action='store',
                        type=int,
                        default=3,
                        help='''\
Indent level.
Default is %(default)s.
 ''')
    add_common_args(parser)
    opts = parser.parse_args()
    return opts


def collect_datasources(root: TreeNode, services: dict):
    '''Collect the datasources nodes.

    Args:
        root: The root of the display tree.
        services: The dictionary of services.
    '''
    datasources = TreeNode('datasources', root)
    for obj in services['datasources']:
        name = obj['name']
        did = obj['id']
        dtype = obj['type']
        key = f'{name}:{did}:{dtype}'
        TreeNode(key, datasources)


def collect_folders(root: TreeNode, services: dict):
    '''Collect the folder nodes.

    Args:
        root: The root of the display tree.
        services: The dictionary of services.
    '''
    folders = TreeNode('folders', root)
    for obj in services['folders']:
        title = obj['title']
        fid = obj['id']
        key = f'{title}:{fid}'
        folder = TreeNode(key, folders)
        dashboards = TreeNode('dashboards', folder)
        for dashboard in services['dashboards']:
            #print(json.dumps(dashboard, indent=4))
            assert 'dashboard' in dashboard
            assert 'folderId' in dashboard
            assert 'meta' in dashboard
            dfid = dashboard['folderId']
            if fid == dfid:
                continue
            dash = dashboard['dashboard']
            title = dash['title']
            did = dash['id']
            uid = dash['uid']
            num = len(dash['panels'])
            key = f'{title}:id={did}:uid={uid}:panels={num}'
            TreeNode(key, dashboards)


def collect(burl: str, auth: Tuple[str, str], name: str) -> TreeNode:
    '''List the grafana structure.

    Args:
        opts: The command line options.
        container: The container object.
        name: The name of the top level node.

    Returns:
        tree: The root of the display tree.
    '''
    services = read_all_services(burl, auth)
    root = TreeNode(name)
    collect_datasources(root, services)
    collect_folders(root, services)
    return root


def get_external_ports(container: Container) -> list:
    '''Get the external ports associated with a container.

    Args:
        container: The container object.

    Returns:
        list: A list of ports.
    '''
    # Add the ports.
    ports = []
    pobjs = container.attrs['HostConfig']['PortBindings']
    for attrs in pobjs.values():
        for attr in attrs:
            if 'HostPort' in attr:
                value = attr['HostPort']
                ports.append(value)
    return ports


def check_port(port: int) -> Container:  # pylint: disable=inconsistent-return-statements
    '''Check to see if a port is valid.

    A port is valid if it shows up as an external port
    for a grafana docker container.

    If a valid port is not, the program exits.

    Args:
        containers: The list of containers to search.
        port: The external port to look for.

    Returns:
        object: The container object if found.
    '''
    client = docker.from_env()
    containers = client.containers.list(filters={'label': 'grape.type'})
    for container in sorted(containers, key=lambda x: x.name.lower()):
        ports = get_external_ports(container)
        if ports and int(ports[0]) == port:
            ctype = container.labels['grape.type']
            if ctype == 'gr':
                return container
    err(f'no grape grafana containers found that expose port: {port},\n\t'
        'try running "pipenv run grape status -v"')


def main():
    '''Tree command main.

    This is the command line entry point for the tree command.

    It presents a tree view of one or more grafana servers.
    '''
    opts = getopts()
    initv(opts.verbose)
    info('tree')
    container = check_port(opts.grxport)
    burl = f'http://127.0.0.1:{opts.grxport}'
    name = container.name + ':' + str(opts.grxport)
    top = collect(burl, DEFAULT_AUTH, name)
    if opts.fname:
        with open(opts.fname, 'w') as ofp:
            top.sort().dump(ofp=ofp, indent=opts.indent)
    else:
        top.sort().dump(ofp=sys.stdout, indent=opts.indent)
