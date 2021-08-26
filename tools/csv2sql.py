#!/usr/bin/env python
'''
This is a standalone tool to read a CSV data file with a header
row and convert it to SQL instructions to create and populate a table
generically.

It is generic because it figures out the field types by analyzing the
data.

There are a number of options for specifying the output, how to
convert certain values and what SQL types to use for integers,
floats, dates and strings.

It is useful for adding CSV data to your dashboards.

See the help (-h) for more detailed information.
'''
import argparse
import csv as csvmod
import inspect
import os
from pathlib import Path
import sys
from typing import List, Tuple, TextIO
from dateutil.parser import parse as parse_date


# The program version.
__version__ = '0.1.0'

# Set by getargs.
VERBOSE = 0


def infov(msg: str, level: int=1, ofp: TextIO = sys.stderr):
    '''Output an info message.

    Args:
        msg: The information message.
        level: Stack level which is used to determin which line number
            of report. The default is the parent.
        ofp: Output file pointer. The default is stderr.
    '''
    if VERBOSE:
        lineno = inspect.stack()[level].lineno
        ofp.write('\x1b[34m')
        ofp.write(f'INFO:{lineno}: {msg}')
        ofp.write('\x1b[0m\n')


def err(msg: str, level: int=1, ofp: TextIO = sys.stderr, xcode: int = 1):
    '''Output an info message.

    Args:
        msg: The information message.
        level: Stack level which is used to determin which line number
            of report. The default is the parent.
        ofp: Output file pointer. The default is stderr.
    '''
    lineno = inspect.stack()[level].lineno
    ofp.write('\x1b[31m')
    ofp.write(f'ERROR:{lineno}: {msg}')
    ofp.write('\x1b[0m\n')
    sys.exit(xcode)


def args_get_text(string: str):
    '''Convert to argparse section titles upper case to make things
    consistent.

    Args:
        string: The string from argparse.

    Returns:
        string: The string in uppercase if it matches known patterns.
    '''
    lookup = {
        'usage: ': 'USAGE:',
        'positional arguments': 'POSITIONAL ARGUMENTS',
        'optional arguments': 'OPTIONAL ARGUMENTS',
        'show this help message and exit': 'Show this help message and exit.\n ',
    }
    return lookup.get(string, string)


def getargs() -> argparse.Namespace:
    '''
    Get the command line options.

    Returns:
        args: The arguments.
    '''
    argparse._ = args_get_text  # type: ignore
    base = os.path.basename(sys.argv[0])
    usage = '\n {0} [OPTIONS] [CSV]'.format(base)
    desc = 'DESCRIPTION:{0}'.format('\n  '.join(__doc__.split('\n')))
    epilog = '''
EXAMPLES:
    # ------------------------------------------------
    # Example 1: Help.
    # ------------------------------------------------
        $ {0} -h

    # ------------------------------------------------
    # Example 2: Generate SQL using the default table name.
    #            The table name will be "my_data".
    # ------------------------------------------------
        $ {0} my-data.csv > my-data.sql

    # ------------------------------------------------
    # Example 3: Generate SQL using the default table name
    #            to an explicit file.
    #            The table name will be "my_data".
    # ------------------------------------------------
        $ {0} -o my-data.sql my-data.csv

    # ------------------------------------------------
    # Example 4: Generate SQL using an explicit table name.
    # ------------------------------------------------
        $ {0} -t cool_data -o my-data.sql my-data.csv

    # ------------------------------------------------
    # Example 5: Generate SQL using an explicit table name.
    #            Convert NA to 0.
    # ------------------------------------------------
        $ {0} -c NA=0 -t cool_data -o my-data.sql my-data.csv

    # ------------------------------------------------
    # Example 6: Only generate the table creation header.
    #            Very useful for checking types.
    # ------------------------------------------------
        $ {0} -H -c NA=0 -t cool_data -o my-data.sql my-data.csv

    # ------------------------------------------------
    # Example 7: Specify the SQL types explicitly.
    # ------------------------------------------------
        $ {0} -H -c NA=0 -d TIMESTAMP -i INT -f FLOAT -s TEXT -o my-data.sql my-data.csv

VERSION:
   {1}
'''.format(base, __version__).strip()
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog.rstrip() + '\n ')

    parser.add_argument('-c', '--conversion',
                        action='append',
                        help='''\
Define conversion substitutions.

This is a key/value pair of the
form: KEY=VALUE.

It can be used to map strings like ZERO
or NA to a number like 0 for cases where
there are strings in a column that is
known to be integers or floats.
 ''')

    parser.add_argument('-d', '--date',
                        action='store',
                        dest='sql_date_type',
                        default='TIMESTAMP',
                        help='''\
The SQL date type to use.

The default is %(default)s.
 ''')

    parser.add_argument('-f', '--float',
                        action='store',
                        dest='sql_float_type',
                        default='NUMERIC',
                        help='''\
The SQL float type to use.

The default is %(default)s.
 ''')

    parser.add_argument('-i', '--int',
                        action='store',
                        dest='sql_int_type',
                        default='INT',
                        help='''\
The SQL integer type to use.

The default is %(default)s.
 ''')

    parser.add_argument('-H', '--header',
                        action='store_true',
                        dest='header_only',
                        default='',
                        help='''\
Only print the header.

This is useful for verifying that
the type analysis worked.
 ''')

    parser.add_argument('-o', '--out',
                        action='store',
                        default='',
                        help='''\
The output file name.

If not specified, the output is
written to stdout.
 ''')

    parser.add_argument('-s', '--str',
                        action='store',
                        dest='sql_str_type',
                        default='TEXT',
                        help='''\
The SQL string type to use.

The default is %(default)s.
 ''')

    parser.add_argument('-t', '--table',
                        action='store',
                        default='',
                        help='''\
The SQL table name.

If not specified the default name
is derived from the CSV file name.
 ''')

    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='''\
Increase the level of verbosity.
 ''')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s version {0}'.format(__version__),
                        help='''\
Show program's version number and exit.
 ''')

    parser.add_argument('CSV',
                        action='store',
                        nargs=1,
                        help='''\
The CSV file to read.
''')

    args = parser.parse_args()
    if not args.table:
        path = args.CSV[0]
        args.table = Path(path).stem

    if args.conversion:
        for cvt in args.conversion:
            if '=' not in cvt:
                err(f'invalid conversion specification: "{cvt}", '
                    'it must have an equals sign')

    globals()['VERBOSE'] = args.verbose
    return args


def load(path: str) -> list:
    '''Load the CSV file.

    Args:
        path - The file path.

    Results:
        Returns the CSV as a list of lists.
    '''
    infov(f'loading CSV data from "{path}"')
    csv = []
    with open(path, encoding='utf-8') as ifp:
        reader = csvmod.reader(ifp)
        for row in reader:
            assert isinstance(row, list)
            csv.append(row)
    return csv


def define_column_recs(hdr: list) -> Tuple[int, list]:
    '''Define the columns.

    At this point the type is not known.

    Args:
        hdr: The first line of the CSV. It is assumed to contain the headers.

    Returns:
        maxc: The maximum column title size.
        list: The list of type records.
    '''
    maxc = 0
    crecs = []
    for i, col in enumerate(hdr):
        crecs.append({
            'index': i,
            'title': col,
            'type': '?',
            'quote': False,
        })
        maxc = max(maxc, len(col))
    return maxc, crecs


def convert_col(args: argparse.Namespace, col: str) -> str:
    '''Convert the column value if necessary.

    Args:
        args: The command line arguments.
        col: The column value.

    Returns:
        value: The updated value.
    '''
    if args.conversion:
        for cvt in args.conversion:
            key, value = cvt.split('=', 1)
            if col == key:
                col = value
                break  # first match
    return col


def is_int(col: str) -> bool:
    '''Is this column value an integer?

    Args:
        col: The column value.

    Returns:
        flag: True if it is an int or false otherwise.
    '''
    flag = False
    try:
        int(col)
        flag = True
    except ValueError:
        pass
    return flag


def is_float(col: str) -> bool:
    '''Is this column value a float?

    Args:
        col: The column value.

    Returns:
        flag: True if it is a float or false otherwise.
    '''
    flag = False
    try:
        float(col)
        flag = True
    except ValueError:
        pass
    return flag


def is_date(col: str) -> bool:
    '''Is this column value a date?

    Args:
        col: The column value.

    Returns:
        flag: True if it is a date or false otherwise.
    '''
    flag = False
    try:
        parse_date(col)
        flag = True
    except (ValueError, OverflowError):
        pass
    return flag


def compute_col_ctype(args: argparse.Namespace,
                      col: str, prev: str) -> Tuple[str, str, bool]:
    '''Figure out the type.

    This is tricky because "1" can be an integer, a float or a string.

    Args:
        args: The command line arguments.
        col: The current column value.
        prev: The previous setting for the column type.

    Returns:
        col: The updated column value.
        type: The updated column type.
        quote: The boolean that tells the SQL generator whether to quote this column.
    '''
    tmap = {
        'date': {'type': args.sql_date_type, 'quote': True, 'matches': False},
        'float': {'type': args.sql_float_type, 'quote': False, 'matches': False},
        'int': {'type': args.sql_int_type, 'quote': False, 'matches': False},
        'str': {'type': args.sql_str_type, 'quote': True, 'matches': True},
    }
    col = convert_col(args, col)
    key = 'str'

    # Short circuit if we already know that we have a string.
    if prev == 'str':
        # We cannot refine it further.
        ctype : str = tmap[key]['type']  # type: ignore
        quote : bool = tmap[key]['quote']  # type: ignore
        return col, ctype, quote


    if is_int(col):
        # Mark this column as an int if it has the characteristics of an
        # integer.
        tmap['int']['matches'] = True
        if prev in ['TIMESTAMP', 'TEXT']:  # INT is fine
            # We have something like this in the same column:
            #    2020-01-01
            #    foo
            #    3
            key = 'str'
        elif prev in ['FLOAT']:
            # float is a superset of int
            key = 'float'
        else:
            key = 'int'

    elif is_float(col):
        # Mark this column as a float if it has the characteristics of a
        # float and it is not an int.
        # It must not be an int to be considered.
        tmap['float']['matches'] = True  # for future reference

        # Check for a case like this:
        #    2020-01-01
        #    1.7
        key = 'str' if prev in ['TIMESTAMP', 'TEXT'] else 'float'

    elif is_date(col):
        # Mark this column as a date if it has the characteristics of a
        # date if it is not an int or a float.
        tmap['date']['matches'] = True  # for future reference

        # Check for a case like this:
        #    3
        #    1.7
        #    2020-01-01
        key = 'str' if prev in ['NUMERIC', 'INT', 'TEXT'] else 'date'

    if prev == '?':
        # This field has not been defined.
        ctype : str = tmap[key]['type']  # type: ignore
        quote : bool = tmap[key]['quote']  # type: ignore
        return col, ctype, quote

    ctype : str = tmap[key]['type']  # type: ignore
    quote : bool = tmap[key]['quote']  # type: ignore
    return col, ctype, quote


def set_column_types(args: argparse.Namespace, csv: list, crecs: list):
    '''Figure out the column types and set them in the column records.

    All of the rows are analyzed to determine the column type.

    Args:
        args: The command line arguments.
        csv: The CSV data. First line is a header line.
        crecs: The column types from the define_column_recs call.
    '''
    # Collect the column type data.
    for i, row in enumerate(csv[1:], start=1):  # skip the header
        for j, col in enumerate(row):
            prev = crecs[j]['type']
            col, ctype, quote = compute_col_ctype(args, col, prev)
            crecs[j]['type'] = ctype
            crecs[j]['quote'] = quote
            csv[i][j] = col  # update col values


def create_sql_table(stmts: list, crecs: list, tname: str, maxc: int):
    '''Create the SQL table commands.

    Updates the statements with the SQL commands.

    Args:
        stmts: The SQL statement list.
        crecs: The column records with the types populated.
        tname: The table name.
        maxc: The maximum column title width.

    Usage:
        stmts = []
        create_sql_table(stmts, crecs)
        print(''.join(stmts))
    '''
    stmts.append(f'DROP TABLE IF EXISTS {tname};\n')
    stmts.append(f'CREATE TABLE {tname} (\n')
    stmts.append(f'  {"id":<{maxc}} SERIAL PRIMARY KEY')
    for col in crecs:
        title = col['title']
        ctype = col['type']
        stmts.append(f',\n  {title:<{maxc}} {ctype}')
    stmts.append(');\n')


def create_sql_insert_values(stmts: list, csv: list, crecs: list, tname: str):
    '''Create the SQL insert commands.

    Updates the statements with the SQL commands.

    Args:
        stmts: The SQL statement list.
        csv: The CSV data.
        crecs: The column records with the types populated.
        tname: The table name.

    Usage:
        stmts = []
        create_sql_table(stmts, crecs)
        create_insert_values(stmts, crecs)
        print(''.join(stmts))
    '''
    # Insert values into the table.
    # First define the insert columns.
    stmts.append(f'INSERT INTO {tname} (')
    for j, col in enumerate(crecs):
        pre = ', ' if j else ''
        title = col['title']
        stmt = f'{pre}\n  {title}'
        stmts.append(stmt)
    stmts.append(')\n')

    # Second, insert the values.
    stmts.append('VALUES')
    for i, row in enumerate(csv[1:]):  # skip header
        stmt = ''
        if i:
            stmt += ','
        stmt += '\n  ('
        for j, col in enumerate(row):
            pre = ', ' if j else ''
            if crecs[j]['quote']:
                col = col.replace("'", "''")
                stmt += f"{pre}'{col}'"
            else:
                stmt += f'{pre}{col}'
        stmt += ')'
        stmts.append(stmt)
    stmts.append(';\n')


def sql(args: argparse.Namespace, csv: list, ofp: TextIO):
    '''Generate the SQL.

    This assumes that the first line is the header.
    It then analyzes all of the rows to figure out the types.

    Args:
        args: The command line arguments.
        csv: The comma separated variable data.
    '''
    tname = args.table
    maxc, crecs = define_column_recs(csv[0])
    set_column_types(args, csv, crecs)

    # Define and populate the SQL table.
    stmts : List[str] = []
    create_sql_table(stmts, crecs, tname, maxc)

    if not args.header_only:
        create_sql_insert_values(stmts, csv, crecs, tname)

    # Print it.
    ofp.write(''.join(stmts) + '\n')


def main():
    'main'
    args = getargs()
    path = args.CSV[0]
    csv = load(path)
    if args.out:
        infov(f'writing to "{args.out}"')
        with open(args.out, 'w', encoding='utf-8') as ofp:
            sql(args, csv, ofp)
    else:
        sql(args, csv, sys.stdout)
    infov('done')


if __name__ == '__main__':
    main()
