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
from typing import Any, Callable, Iterable, List, Optional, TextIO, Tuple

import docker  # type: ignore
from docker.models.containers import Container  # type: ignore

from grape.common.args import CLI, add_common_args, args_get_text
from grape.common.log import initv, info, err
from grape.common.gr import read_all_services
from grape.common.conf import DEFAULT_AUTH
from grape import __version__


class TreeReportNode:
    '''Report tree nodes.

    The tree structure is used for the reporting data in tree
    format.

    You use it by first constructing a tree like this:
        top = TreeReportNode('top')
        node1 = TreeReportNode('node:1', top)
        node2 = TreeReportNode('node:2', top)
        node11 = TreeReportNode('node:1.1', node1)
        node12 = TreeReportNode('node:1.2', node1)
        node21 = TreeReportNode('node:1.1', node2)
        node22 = TreeReportNode('node:1.2', node2)

    Once the tree is constructed, you generate the tree report
    like this:
        for prefix, value in top.walk():
            print(f'{prefix}{value}')

    The output will look like this:
        top
          ├─ node:1
          │   ├─ node:1.1
          │   └─ node:1.2
          └─ node:2
              ├─ node:2.1
              └─ node:2.2

    You can also sort the output:
        for prefix, value in top.sort().walk():
            print(f'{prefix}{value}')

    It can accept any type of data because the data is simply passed
    through unless the caller wants to sort the data.

    If the user wants to sort the data and the data cannot be
    stringified, then the user must be careful to define the sort
    function argument to define a function that imposes order.
    '''
    def __init__(self, value: Any, parent : Optional[TreeReportNode] = None):
        '''Create a node.

        This is the only way to add a node to the tree. At present
        there is no way to remove a node.

        The is_last flag is used to determine the prefix when building
        the tree display.

        Args:
            value: The value of the node.
            parent: The parent node. This is optional but only for the
                root of the tree.

        Returns:
            node: A tree node object.
        '''
        self._value = value
        self._children : List[TreeReportNode] = []
        self._parent : Optional[TreeReportNode] = parent
        self._is_last = True
        if parent:
            parent._children.append(self)
            if len(parent._children) > 1:
                parent._children[-2]._is_last = False

    @property
    def value(self) -> Any:
        'value'
        return self._value

    @property
    def parent(self) -> Optional[TreeReportNode]:
        'parent'
        return self._parent

    @property
    def children(self) -> List[TreeReportNode]:
        'children'
        return self._children

    @property
    def is_last(self) -> bool:
        'is this the last child?'
        return self._is_last

    def sort(self, scmp: Callable[[Any], str] = lambda x: str(x.value).lower()) -> TreeReportNode:
        '''Sort in place.

        The sort function can work for any data type but for types
        that do not support being stringified or for cases where being
        stringified does not create the desired ordering, a sort
        compare function must be defined.

        For example, if the user wanted to compare integers then a
        function like this would make more sense than the default:
        "lambda x: x" to enable integer comparisons.

        For complex objects like class variables or dictionaries, the
        lambda function would choose the appropriate fields.  For
        example, a class with a foo member could be compared by
        creating a function like this: "lambda x: x.foo". A similar
        approach would be used for a dictionary or a list.

        Args:
            scmp: Sort comparator.

        Usage:
            def sort_string(root: TreeReportNode):
                'string type thing sorter'
                fct = lambda x: str(x.value).lower()
                root.sort(fct)

            def sort_integer(root: TreeReportNode):
                'integer thing sorter'
                assert isinstance(root.value, int)
                fct = lambda x: x
                root.sort(fct)
        '''
        if self._children:
            self._children = sorted(self._children, key=scmp)
            for child in self._children:
                child.sort()
                child._is_last = False  # pylint: disable=protected-access
            self._children[-1]._is_last = True  # pylint: disable=protected-access
        return self

    def __lt__(self, other: TreeReportNode) -> bool:
        'compare lt for sort'
        return self._value < other._value

    def __eq__(self, other: object) -> bool:
        'compare eq for sort'
        if isinstance(other, TreeReportNode):
            return self._value == other._value
        return False

    def __str__(self) -> str:
        'string representation of the object'
        sortable = str(self._value) + ','.join([str(x._value) for x in self._children])
        return sortable

    def prefix(self, indent: int=3) -> str:
        '''Define the prefix for the tree report.

        This is used by the walk() generator.

        Args:
            indent: The indentation level for the report.

        Returns:
            prefix: The prefix as a string.
        '''
        prefixes = []
        if self.parent:
            left = ''
            right0 = ''
            right1 = ''
            half = indent // 2
            if half:
                blanks = ' ' * half
                left = blanks
                if indent % 2:
                    left += ' '
                right0 = blanks
                right1 = '\u2500' * half

            if self._is_last:
                symbol = '\u2514'  # L
            else:
                symbol = '\u251c'  # |-
            prefix = f'{left}{symbol}{right1}'
            prefixes.append(prefix)

            # Children.
            node = self._parent
            while node:
                if node.parent:
                    if node.is_last:
                        symbol = ' '
                    else:
                        symbol = '\u2502'  # |
                    prefix = f'{left}{symbol}{right0}'
                    prefixes.append(prefix)
                node = node.parent
                # The following check is meant to detect
                # unexpected errors that result from building
                # the tree.
                # It should never be deeper than 3 levels.
                # top -> folders -> dashboards
                assert len(prefixes) < 4

        # Write out the node.
        prefix = ''.join(reversed(prefixes))
        if self.parent:
            prefix += ' '
        return prefix

    def walk(self, indent: int=3) -> Iterable[Tuple[str, Any]]:
        '''Generator that walks over the tree.

        Args:
            indent: The indentation level for the report.

        Returns:
            prefix: The prefix.
            value: The value.

        Usage:
            def print_tree(tree: TreeReportNode):
                'print the tree'
                for prefix, value in tree.walk():
                    print(f'{prefix}{str(value)}')
        '''
        prefix : str = self.prefix(indent)
        yield prefix, self.value
        for child in self._children:
            yield from child.walk(indent)


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
    add_common_args(parser, '-f', '-g', '-i', '-s')
    opts = parser.parse_args()
    return opts


def collect_datasources(root: TreeReportNode, services: dict):
    '''Collect the datasources nodes.

    Args:
        root: The root of the display tree.
        services: The dictionary of grafana services from
            read_all_services.
    '''
    datasources = TreeReportNode('datasources', root)
    for obj in services['datasources']:
        name = obj['name']
        did = obj['id']
        dtype = obj['type']
        key = f'{name}:id={did}:type={dtype}'
        TreeReportNode(key, datasources)


def collect_folders(root: TreeReportNode, services: dict):
    '''Collect the folder nodes.

    Args:
        root: The root of the display tree.
        services: The dictionary of grafana services from
            read_all_services.
    '''
    folders = TreeReportNode('folders', root)
    for obj in services['folders']:
        title = obj['title']
        fid = obj['id']
        key = f'{title}:id={fid}'
        folder = TreeReportNode(key, folders)
        dashboards = TreeReportNode('dashboards', folder)
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
            TreeReportNode(key, dashboards)


def collect(burl: str, auth: Tuple[str, str], name: str) -> TreeReportNode:
    '''List the grafana structure.

    Args:
        burl: The base URL for the grafana service.
        auth: The grafana authorization.
        name: The name of the top level tree node.

    Returns:
        tree: The root of the display tree.
    '''
    services = read_all_services(burl, auth)
    root = TreeReportNode(name)
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

    If a port is not valid, the program exits.

    Args:
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


def print_tree(opts: argparse.Namespace, ofp: TextIO, root: TreeReportNode):
    '''Print out the tree view.

    Args:
        opts: The command line options.
        ofp: The output file pointer.
        root: The root node of the tree.
    '''
    if opts.sort:
        root.sort()
    for prefix, value in root.walk(opts.indent):
        ofp.write(prefix)
        ofp.write(value)
        ofp.write('\n')


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
    root = collect(burl, DEFAULT_AUTH, name)
    if opts.fname:
        with open(opts.fname, 'w') as ofp:
            print_tree(opts, ofp, root)
    else:
        print_tree(opts, sys.stdout, root)
    info('done')
