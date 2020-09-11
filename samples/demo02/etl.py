#!/usr/bin/env python3
'''
Total hack to populate the database with public data downloaded from
the Economist web site:

   https://github.com/TheEconomist/covid-19-excess-deaths-tracker

The ETL logic will be different for different datasets.
'''
import csv as csvmod
import os
import sys
import time
import psycopg2


def load(path: str) -> list:
    '''
    Load the file.

    Args:
        path - The file path.
    Results:
        Returns the CSV as a list of lists.
    '''
    print(f'\x1b[34mINFO: loading the data from {path}\x1b[0m')
    csv = []
    with open(path) as ifp:
        reader = csvmod.reader(ifp)
        for row in reader:
            assert isinstance(row, list)
            csv.append(row)
    return csv


def build_sql(conf: dict, csv: list) -> str:  # pylint: disable=too-many-locals
    '''
    Build the sql command.

    Args:
        conf - The configuration data.
        csv - The CSV data.
    Returns:
        The SQL command string.
    '''
    print('\x1b[34mINFO: building the sql commands\x1b[0m')
    path = conf['path']
    tname = os.path.basename(os.path.splitext(path)[0])
    ctmap = {
        'year': 'INT',
        'month': 'INT',
        'week': 'INT',
        'deaths': 'INT',
        #'expected_deaths': 'INT',
        #'excess_deaths': 'INT',
        'population': 'NUMERIC',
        'total_deaths': 'NUMERIC',
        'covid_deaths': 'NUMERIC',
        'expected_deaths': 'NUMERIC',
        'excess_deaths': 'NUMERIC',
        'non_covid_deaths': 'NUMERIC',
        'covid_deaths_per_100k': 'NUMERIC',
        'excess_deaths_per_100k': 'NUMERIC',
        'excess_deaths_pct_change': 'NUMERIC',
        }

    sqls = []

    # Drop the old table.
    sqls.append(f'DROP TABLE IF EXISTS "{tname}" CASCADE ;')

    # Create the new table.
    colmap = []  # map by index
    sqls.append(f'CREATE TABLE "{tname}" (')
    sqls.append('  id SERIAL PRIMARY KEY,')
    for col in csv[0]:
        ctype = ctmap.get(col, 'TEXT')
        colmap.append(ctype)
        line = f'  {col} {ctype},'
        sqls.append(line)
    sqls[-1] = sqls[-1].replace(',', ');')  # fix the last line

    # Insert.
    line = f'INSERT INTO {tname} ('
    for col in csv[0]:
        line += col + ', '
    line = line[:-2] + ')'  # fix the last entry
    sqls.append(line)
    sqls.append('VALUES')
    for row in csv[1:]:  # skip the header.
        line = '  ('
        for j, col in enumerate(row):
            ctype = colmap[j]
            #sqls.append(f'-- DEBUG: j={j}, ctype={ctype}, col="{col}", quote=' + str("'" in col))
            if ctype == 'INT':
                try:
                    val = int(col)
                except ValueError:
                    val = 0
            elif ctype == 'NUMERIC':
                try:
                    val = float(col)
                except ValueError:
                    val = 0
            else:
                if "'" in col:
                    col = col.replace("'", "''")
                val = f"'{col}'"
            if j:
                line += ', '
            line += str(val)

        line += '),'
        sqls.append(line)
    # fix the last line
    line = sqls[-1][:-2] + ');'
    sqls[-1] = line

    # Create the view.
    view = f'{tname}_view'
    sqls.append(f'DROP VIEW IF EXISTS "{view}";')
    sqls.append(f'''\
CREATE VIEW \"{view}\" AS
  SELECT *,
  to_date(year::text || ' ' || week::text, 'IYYYIW') AS time
FROM {tname}
WHERE
  year > 2000 AND week > 0
;
''')

    # Capture locally for debugging.
    sql = '\n'.join(sqls)
    fname = tname.replace('/', '-')
    with open(f'{fname}.sql', 'w') as ofp:
        ofp.write(sql)
    return sql


def dbwrite(conf: dict, sql: str):
    '''
    Write the database.

    Args:
        conf - The configuration data.
        sql - SQL commands to create the database.
    '''
    print('\x1b[34mINFO: updating the database\x1b[0m')
    port = conf['port']
    okflag = 0
    for i in range(1, 11):
        try:
            conn = psycopg2.connect(dbname=conf['dbname'],
                                    user=conf['user'],
                                    password=conf['password'],
                                    host=conf['host'],
                                    port=port)
            okflag = i
            break
        except psycopg2.OperationalError as exc:
            print(f'WARNING: try #{i+1} failed: {exc}')
            time.sleep(5)
    if not okflag:
        sys.stderr.write('\x1b[31mERROR: could not connect!\x1b[0m\n')
        sys.exit(1)
    elif okflag:
        print('\x1b[34mINFO: successfully connected!\x1b[0m')
    with conn.cursor() as cursor:
        cursor.execute(sql)
    conn.commit()


def get_conf() -> dict:
    '''
    Get the configuration.
    '''
    print('\x1b[34mINFO: loading conf\x1b[0m')
    conf = {
        'table': 'all_weekly_excess_deaths',
        'path': 'all_weekly_excess_deaths.csv',
        'host': 'localhost',
        'port': 4411,
        'dbname': 'postgres',
        'user': 'postgres',
        'password': 'password'
    }
    return conf


def main():
    'main'
    conf = get_conf()
    csv = load(conf['path'])
    sql = build_sql(conf, csv)
    dbwrite(conf, sql)
    print('\x1b[34mINFO: done\x1b[0m')


if __name__ == '__main__':
    main()
