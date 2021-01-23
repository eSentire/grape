# demo02
This directory contains a sample that is fully contained that is a bit
more realistic than demo01 because it shows graph data from a public
datasurce.

It will create a demo02 grafana system on host port 4410 that reads
data from the associated database managed by the `demo02pg` container.

The purpose is to show how to create an environment from scratch and then
modify it. In the sample the modification comes from the `grafana.json`
file and the `etl.py` tool that converts the downloaded data to database
tables and views.

### How to run it
In an interactive environment you would mostly likely make all of the
changes in grafana and the database directly.

To run the demo:
```bash
$ ./run.sh
```

> Note that this script uses `grape/tools/upload-json-dashboard.sh`
> to load the dashboard into the server.

### Result
When the run has completed, you will be able navigate to
http://localhost:4410 to see the newly created dashboard.

It looks like this:
!['demo02'](/img/demo02.png)

### Discussion
This demo analyzes an open-source dataset from the Economist that
allows it to grab information about COVID-19 mortality along with
information about excess deaths. It then uses that information to
build a crude model to estimate how many of the deaths were
characterized as non-covid when they were actually Covid (using the
excess deaths as a baseline).

Please note that this demo is _not_ about the metholodogy or the
results, which may well be flawed. Instead it is meant as a to help
you understand how to do visualizations.

Also note that this is not meant to be guide to using postgres or
grafana in any detail. It will merely help you set it up so that you
can figure out things yourself.

This document only shows simple time series data in the graph but be
aware that you can include moving averages and other trend analysis by
creating appropriate SQL queries.

### Raw Data
The raw data in `all_weekly_excess_deaths.csv` was manually
downloaded from
[this](https://raw.githubusercontent.com/TheEconomist/covid-19-excess-deaths-tracker/master/output-data/excess-deaths/all_weekly_excess_deaths.csv)
site.

### ETL
The `etl.py` program is pretty interesting because it, for the most part,
parses a generic CSV file with a single header row and creates a database
table by analyzing the data.

There is one non-generic hack, if it sees a `NA` in a column that
is otherwise a number, it will set the value to zero.

Here is how it is run: `./etl.py CSV_FILE [TABLE_NAME] > [SQL_FILE]`.

Where `CSV_FILE` is the name of the CSV file and `TABLE_NAME` is the
name of the SQL table. If the `TABLE_NAME` is not specified, the
file name root is used.

The SQL is output to stdout.

Here is an example run:
```bash
   $ ./etl.py raw.csv raw_table > raw.sql
```

It is very useful for translating generic CSV data to SQL.

### SQL Query
The SQL query used for the time series graph looks like this:
```sql
WITH bigtime AS
  (SELECT
    *,
    to_date(year::text || ' ' || week::text, 'IYYYIW') AS time,
    -- uncounted_deaths is the number of unexpected deaths minus the covid_deaths
    -- which assumes that all covid death are unexpected
    -- if total_deaths < expected_deaths then this is not accurate
    total_deaths - expected_deaths as unexpected_deaths,
    greatest(total_deaths - expected_deaths - covid_deaths, 0) as uncounted_deaths
    FROM all_weekly_excess_deaths)
SELECT
  $__timeGroup(time, '1w'),
--  total_deaths as "Total Deaths",
--  expected_deaths as "Expected Deaths",
  covid_deaths as "COVID Deaths Reported",
  uncounted_deaths as "COVID Deaths Not Reported",
  'weekly:' as metric
FROM
  bigtime
WHERE
  $__timeFilter(time)
  AND country in ($country)
  AND region in ($region)
GROUP BY
  time,
  total_deaths,
  expected_deaths,
  unexpected_deaths,
  uncounted_deaths,
  non_covid_deaths,
  covid_deaths
ORDER BY
  time,
  total_deaths,
  expected_deaths,
  unexpected_deaths,
  uncounted_deaths,
  non_covid_deaths,
  covid_deaths ASC
```
