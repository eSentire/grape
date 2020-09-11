# demo01
This directory contains a sample that is fully contained. It will create
a demo01 grafana system on host port 4400 that reads data from the associated
database.

The purpose is to show how to create an environment from scratch and then
modify it. In the sample the modification comes from the `grafana.json`
file but in an interactive environment you would mostly likely make all
of the changes in grafana itself, save them in grafana and then use the
`grape` tool to save them to a zip file that can later be used to load
into another system.

To run the demo:
```bash
$ ./run.sh
```

When the run has completed, you will be able navigate to
http://localhost:4400 to see the newly created dashboard.
It looks like this:

![step-01](/img/demo01-01-welcome.png)

Enter username `admin` and password `admin` and click `Log In` to log in.

![step-02](/img/demo01-02-login.png)

You will then be directed to a page that asks you to change the password. Go ahead and skip it by clicking on the `Skip` button.

![step-03](/img/demo01-03-skip-new-password.png)

At this point you will be in Grafana. Hover your mouse over the `Dashboard` icon and a menu will pop up with a `Manage` option.
Click on that.

![step-04](demo01-04-dashboards-manage.png)

The `Manage` screen will down the `Demo01 Folder`. Click on it to see the associated dashboards.

![step-05](demo01-05-folder.png)

You will now see the dashboard `Demo01 Dashboard`. Click on it.
![step-06](demo01-06-folder-dash.png)

At this point you are in the newly created dashboard:
![step-07](demo01-07-dashboard.png)

Although it looks really simple, this demo shows an automatically generated dashboard that connects
to the automatically generated database and displays its contents.

From here you can play around. You can add additional tables and data to the database.
You can create new panels, folders and dashboards.

Here is how you can access the database in the docker container using `psql`.

```bash
$ docker exec -it demo01pg psql -U postgres -d postgres
psql (12.3 (Debian 12.3-1.pgdg100+1))
Type "help" for help.

postgres=# \d
         List of relations
 Schema |  Name  | Type  |  Owner   
--------+--------+-------+----------
 public | demo01 | table | postgres
(1 row)

postgres=# \dS+ demo01
                                     Table "public.demo01"
 Column | Type | Collation | Nullable | Default | Storage  | Stats target |    Description     
--------+------+-----------+----------+---------+----------+--------------+--------------------
 name   | text |           | not null |         | extended |              | A unique key name.
 value  | text |           | not null |         | extended |              | A key value.
Indexes:
    "demo01_name_key" UNIQUE CONSTRAINT, btree (name)
Access method: heap

postgres=# select * from demo01;
 name  |   value   
-------+-----------
 title | Demo01
 color | darkgreen
(2 rows)

postgres=# \q
```

Note that the `grafana.json` file was originally created by manually developing
the dashboard and saving it in grafana and then running the `grape`
save command to create a local zip file where it was extracted from
the `gr.json` file and copied to `grafana.json`.
