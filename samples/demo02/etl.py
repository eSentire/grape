#!/usr/bin/env python
'''
Read the raw CSV data and convert to SQL instructions to create and
populate a table generically.

It is generic because it figures out the field types by analyzing the
data.

There is one non-generic hack, if it sees a 'NA' in a column that
is otherwise a number, it will set the value to zero.

Here is how it is run:
   ./etl.py CSV_FILE [TABLE_NAME]

Where CSV_FILE is the name of the CSV file and TABLE_NAME is the
name of the SQL table. If the TABLE_NAME is not specified, the
file name root is used.

The SQL is output to stdout.

Here is an example run:
   $ ./etl.py raw.csv raw_table > raw.sql

Here is how to check the integrity of the code:
   $ pylint ./etl.py
   $ mypy ./etl.py
'''
import csv as csvmod
from pathlib import Path
import sys
from typing import List, Tuple
import dateutil
from dateutil.parser import parse as parse_date


def load(path: str) -> list:
    '''
    Load the file.

    Args:
        path - The file path.

    Results:
        Returns the CSV as a list of lists.
    '''
    #print(f'\x1b[34mINFO: loading the data from {path}\x1b[0m')
    csv = []
    with open(path) as ifp:
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


def compute_col_ctype(col: str, prev: str) -> Tuple[str, str, bool]:  # pylint: disable=too-many-branches
    '''Figure out the type.

    This is tricky because "1" can be an integer, a float or a string.

    Args:
        col: The current column value.
        prev: The previous setting for the column type.

    Returns:
        col: The updated column value.
        type: The updated column type.
        quote: The boolean that tells the SQL generator whether to quote this column.
    '''
    tmap = {
        'date': {'type': 'TIMESTAMP', 'quote': True, 'matches': False},
        'float': {'type': 'NUMERIC', 'quote': False, 'matches': False},
        'int': {'type': 'INT', 'quote': False, 'matches': False},
        'str': {'type': 'TEXT', 'quote': True, 'matches': True},
    }

    try:
        if col == 'NA':  # hack for NA
            col = '0'
        int(col)
        tmap['int']['matches'] = True
    except ValueError:
        pass

    try:
        if '.' in col:
            float(col)
            tmap['float']['matches'] = True
    except ValueError:
        pass

    # pylint: disable=protected-access
    try:
        if '-' in col and not col.startswith('-'):
            # Ignore tokens like "2020" even if they are valid dates.
            parse_date(col)
            tmap['date']['matches'] = True
    except dateutil.parser._parser.ParserError:  # type: ignore
        pass
    # pylint: enable=protected-access

    if prev == '?':
        # This field has not been defined.
        key = 'str'
        #print(f'DEBUG: col={col}, prev={prev}')
        if tmap['date']['matches']:
            assert not tmap['float']['matches']
            assert not tmap['int']['matches']
            key = 'date'
        elif tmap['float']['matches']:
            key = 'float'
        elif tmap['int']['matches']:
            key = 'int'

        ctype : str = tmap[key]['type']  # type: ignore
        quote : bool = tmap[key]['quote']  # type: ignore
        return col, ctype, quote

    # The field has already been defined. Use the previous type
    # to figure out the precedence.
    key = 'str'
    if tmap['date']['matches']:
        key = 'date'
        if prev in ['NUMERIC', 'INT', 'TEXT']:
            # We have something like this in the same column:
            #    3
            #    1.7
            #    2020-01-01
            #    foo
            key = 'str'
    elif tmap['float']['matches']:
        key = 'float'
        if prev in ['TIMESTAMP', 'TEXT']:  # INT is fine
            # We have something like this in the same column:
            #    3
            #    1.7
            #    2020-01-01
            #    foo
            key = 'str'
    elif tmap['int']['matches']:
        key = 'int'
        if prev in ['TIMESTAMP', 'TEXT']:  # INT is fine
            # We have something like this in the same column:
            #    3
            #    1.7
            #    2020-01-01
            #    foo
            key = 'str'
        elif prev in ['FLOAT']:
            # float is a superset of int
            key = 'float'

    ctype : str = tmap[key]['type']  # type: ignore
    quote : bool = tmap[key]['quote']  # type: ignore
    return col, ctype, quote


def set_column_types(csv: list, crecs: list):
    '''Figure out the column types and set them in the column records.

    All of the rows are analyzed to determine the column type.

    Args:
        csv: The CSV data. First line is a header line.
        crecs: The column types from the define_column_recs call.
    '''
    # Collect the column type data.
    for i, row in enumerate(csv[1:], start=1):  # skip the header
        for j, col in enumerate(row):
            prev = crecs[j]['type']
            col, ctype, quote = compute_col_ctype(col, prev)
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


def sql(csv: list, tname: str):
    '''Generate the SQL.

    This assumes that the first line is the header.
    It then analyzes all of the rows to figure out the types.

    Args:
        csv: The comma separated variable data.
        tname: The SQL table name.
    '''
    maxc, crecs = define_column_recs(csv[0])
    set_column_types(csv, crecs)

    # Define and populate the SQL table.
    stmts : List[str] = []
    create_sql_table(stmts, crecs, tname, maxc)
    create_sql_insert_values(stmts, csv, crecs, tname)

    # Print it.
    print(''.join(stmts))


def getargs() -> Tuple[str, str]:
    '''Get the command line arguments.

    Returns:
        path: The CSV file.
        tname: The SQL table name.
    '''
    if len(sys.argv) < 2:
        print('ERROR: missing the CSV_FILE argument')
        sys.exit(1)

    path = sys.argv[1]
    tname = sys.argv[2] if len(sys.argv) > 2 else Path(path).stem
    return path, tname


def main():
    'main'
    path, tname = getargs()
    csv = load(path)
    sql(csv, tname)


if __name__ == '__main__':
    main()
