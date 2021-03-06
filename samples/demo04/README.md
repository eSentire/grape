# demo04
This demo shows how to build time series and table datasets in panels
without changing the database.

It is really useful for creating mocks of dashboards to see how users
will respond.

To run the demo:
```bash
$ ./run.sh
```

When the run has completed, you will be able navigate to
http://localhost:4430 to see the newly created dashboard.

It looks like this:
!['demo04'](/img/demo04.png)

It relies on these two simple tricks: create a single value or create
multiple values.

Here is an example of a single value for a gauge or stat panel.
```sql
SELECT
  NOW() AS "time",
  'Percent Complete' AS "metric",
  93.2 AS "value"
```

Here is an example of multiple values for a time series display that
can be displayed in a gauge, stat, graph or any other time series
panel.
```sql
SELECT
  time, metric, value
FROM
  (VALUES
    (NOW(), 'metric1', 23),
    (NOW(), 'metric2', 3.14),
    (NOW(), 'metric3', 2.71))
  AS x(time, metric, value)
```

Here is an example of table that can be displayed in a table
widget.
```sql
SELECT
  id, color, meaning
FROM
  (VALUES
    (1, 'green', 'all tests passed'),
    (2, 'yellow', 'some tests failed but all critical tests passed'),
    (3, 'red', 'at least one critical test failed'))
  AS x(id, color, meaning)
```

Heatmaps count the number of values for a given time and display
a color based on the count.

This example shows how to manually create a very simple of data set
where the number of entries at each time dictates the color on the
color map.
```sql
-- Really simple example that shows different colors
-- for the different times for the value.
SELECT
  time, metric, value
FROM
  (VALUES
    (NOW(), 'metric1', 1.0),
    (NOW(), 'metric1', 1.0),
    (NOW(), 'metric1', 1.0),
    (NOW(), 'metric1', 1.0),
    (NOW(), 'metric1', 1.0),
    (NOW(), 'metric1', 1.0),
    (NOW(), 'metric1', 1.0),

    (NOW() - INTERVAL '1 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '1 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '1 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '1 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '1 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '1 SECOND', 'metric1', 1.0),

    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '2 SECOND', 'metric1', 1.0),

    (NOW() - INTERVAL '3 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '3 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '3 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '3 SECOND', 'metric1', 1.0),

    (NOW() - INTERVAL '4 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '4 SECOND', 'metric1', 1.0),
    (NOW() - INTERVAL '4 SECOND', 'metric1', 1.0))
  AS x(time, metric, value)
```
