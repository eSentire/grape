# demo03
This directory contains a sample that displays time series data in
multiple ways.

It will create a demo03 grafana system on host port 4410 that reads
data from the associated database managed by the `demo03pg` container.

The purpose is to show how to create an environment from scratch and then
modify it. In the sample the modifications come from the `grafana.json`
file. The `init.sql` file was created by the `gen.py` file.

In an interactive environment you would mostly likely make all of the
changes in grafana and the database directly.

To run the demo:
```bash
$ ./run.sh
```

When the run has completed, you will be able navigate to
http://localhost:4420 to see the newly created dashboard.

It looks like this:
!['demo03'](/img/demo03.png)
