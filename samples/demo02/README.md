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

In an interactive environment you would mostly likely make all of the
changes in grafana and the database directly.

To run the demo:
```bash
$ ./run.sh
```

When the run has completed, you will be able navigate to
http://localhost:4410 to see the newly created dashboard.

It looks like this:
!['demo02'](/img/demo02.png)

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

The raw data in `all_weekly_excess_deaths.csv` was manually
downloaded from
[this](https://raw.githubusercontent.com/TheEconomist/covid-19-excess-deaths-tracker/master/output-data/excess-deaths/all_weekly_excess_deaths.csv)
site.
