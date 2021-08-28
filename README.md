# grape
[![Releases](https://img.shields.io/github/release/eSentire/grape.svg?style=flat)](https://github.com/eSentire/grape/releases)
![Build](https://github.com/esentire/grape/workflows/CI/badge.svg?branch=master)

Grafana Prototyping Environment

<details><summary>Table of Contents</summary>

### Table of Contents
1. [Prequisities](#prerequisites)
1. [Setup](#setup)
1. [Help](#help)
1. [Create](#create)
1. [Delete](#delete)
1. [Populate Database](#populate-database)
1. [Save](#save)
1. [Load](#load)
1. [Import](#import)
1. [Export](#export)
1. [Status](#status)
1. [Tree](#tree)
1. [Tools](#tools)
   1. [csv2sql.py](#csv2sqlpy)
   1. [runpga.sh](#runpgash)
   1. [upload-json-dashboard.sh](#upload-json-dashboardsh)
1. [Samples](#samples)
   1. [demo01](#demo01)
   1. [demo02](#demo02)
   1. [demo03](#demo03)
   1. [demo04](#demo04)
1. [Miscellaneous](#miscellaneous)
   1. [Grafana](#grafana)
   1. [Postres](#postgres)
   1. [pgAdmin](#pgadmin)
1. [Acknowledgments](#acknowledgments)

</details>


### Overview
This repository contains a tool named `grape` that allows you to
create a local Grafana visualization model prototype using docker
containers, save an existing model and load a saved environment
without having to install any Grafana or database specific software.

It can also be used to import external environments, modify them and
then export them back to enable isolation for development. The state
data can be stored in a repository to enable version control.

In addition, a set of samples is provided that demonstrate how to use
the tool for common operations.

The audience for this tool is folks who want to play around with
Grafana without having to set it up. As long as you have docker
you are good to go.

I use it to experiment on production environments by using the
import capability to duplicate the system of interest locally
(on my laptop) with the caveat that you must know the passwords
for the data sources because Grafana filters them out of the REST
responses.

I also use it to test out new ideas. Typically i spin up an environment
populate the database with modeling data and start playing with
visualization ideas.

Here is a screenshot from `demo02`:
!['demo02'](/img/demo02.png)

See [demo01](/samples/demo01)
and [demo02](/samples/demo02)
for additional grafana screenshots and database access details using `psql`.

This tool has been tested on Mac OSX 10.15.6, Ubuntu 18.04 and Windows 10.


### Prerequisites
To use this you must have:
1. docker (https://docs.docker.com/get-docker/)
   1. The `docker` group must be available on linux.
1. bash
   1. If you are running on windows you will need WSL2 or a linux VM.
   1. It is only needed for the samples.
1. python-3.8 or later
   1. This is because the log module uses the logger stacklevel argument.
1. pipenv
1. A recent version of git
1. gnu make
   1. If you are running on windows you will need WSL2 or a linux VM.
1. unzip
   1. If you are running on windows you will need WSL2 or a linux VM.
1. sudo
   1. On linux, the program must be able to rm the database volume mount.


### Setup
Do these steps to get started:
```bash
$ git clone https://github.com/eSentire/grape.git
$ cd grape
$ make
```
> This can take awhile to run.

To see all of the available make targets: `make help`.

> On windows you may have to run something like dos2unix
> to convert the bash shell scripts or use WSL2 or a linux VM
> to run > the demos in `samples/*/run.sh`. This will enable
>  commands like `make demo01` to work.


### Help
Program help is available via the `-h` command:

```bash
$ pipenv run grape help
```

To get help about the available make commands type: `make help`.


### Create
To create the infrastructure:
```bash
$ pipenv run grape create -v -g 4600 -n example
```

This will create two docker containers: `examplegr` which is the
grafana server and `examplepg` which is the postgresql server.and then
connects them so that the postgresql container database becomes a datasource
in the grafana container.

If the docker containers were previously killed because of something
like a system crash, `grape create` will restart them in the same
state. The grafana dashboards and postgresql database contents will
not be lost. Beware that the `grape delete` operation _will_ destroy the
state data.

It will also create and map the local `example/pg/mnt/pgdata` directory
to the database container to save database results and
`example/gr/mnt/grdata` to the grafana container to save the grafana
dashboard data. This is done so that if the container is restarted for
any reason the postgresql database and grafana dashboards are not
lost. And, finally, it will connect the database as a source in the
grafana server.

This is what the persistent storage looks like on the host:
```
$ tree -L 3 example
example
├── gr
│   ├── mnt
│   │   └── grdata
│   └── start.sh
└── pg
    ├── mnt
    │   └── pgdata
    └── start.sh

6 directories, 2 files
```

This the persistent storage looks like from the containers.

```
$ docker exec -it examplepg ls -l /mnt
total 0
drwxr-xr-x  5 506 dialout 160 Aug 27 17:04 grdata
drwx------ 26 506 dialout 832 Aug 27 17:04 pgdata
$ docker exec -it examplegr ls -l /mnt
total 0
drwxr-xr-x    5 506      dialout        160 Aug 27 17:04 grdata
drwx------   26 506      dialout        832 Aug 27 17:04 pgdata
```

It also creates the database container start script in
`example/gr/start.sh` and the grafana container start script in
`example/pg/start.sh`.  These scripts contain the raw docker
commands to start the database and grafana containers with all
existing data if either container is killed. Once started the
containers _may_ take up to 30 seconds to initialize.

This is what the automatically generated scripts look like on the host:

```
$ tree -L 2 example
example
├── gr
│   ├── mnt
│   └── start.sh
└── pg
    ├── mnt
    └── start.sh

4 directories, 2 files
```

You can now access the empty dashboard at http://localhost:4600 in your
browser. The username is `admin` and the password is `admin`.

At this point you can create grafana visualizations using datasources,
folders and dashboards as well as database tables.


### Delete
The delete operation deletes all artifacts created by the
create operation.
```bash
$ pipenv run grape delete -v -n example
```

It will remove the containers and the local database storage.


### Populate Database
You can access the database using `psql` interactively like this:

```bash
$ docker exec -it examplepg psql -d postgres -U postgres
```

You can also load batch commands like this by taking care to
make them visible to the tool
```bash
$ edit x.sql
$ cp x.sql example/mnt/  # makes it visible as /mnt/x.sql
$ docker exec -it examplepg psql -d postgres -U postgres -1 < /mnt/x.sql
```


### Save
The save operation captures the specified model in a zip file.
It is what you use to capture changes.

```bash
$ pipenv run grape save -v -n example -g 4760 -f /mnt/save.zip
```


### Load
The load operation updates the model from a saved state (zip file).

```bash
$ pipenv run grape load -v -n example -g 4600 -f /mnt/save.zip
```


### Import
The import operation captures an external grafana environment for the
purposes of experimenting or working locally.

It imports rhe datasources without passwords because grafana never
exports passwords which means that they have to be updated manually
after the import operation completes or by specifying the passwords in
the associated conf file. It does not import databases.

The import operation creates a zip file that can be used by a load
operation. It requires a conf file that is specified by the -x option.


#### Operations
Here is the sequence of operations that define an import
flow:

1. create the external conf file
1. import the external grafana
1. load it into the local model


#### Commands
Below are the actual commands for downloading an external
grafana service into the local `foo` model.

```bash
$ rm -rf foo.zip
$ edit import.yaml  # to set the external access parameters.
$ time pipenv run grape del -v -g 4800 -n foo
$ time pipenv run grape import -v -x import.yaml -f foo.zip
$ time pipenv run grape load -v -f foo.zip -n foo -g 4800
```

Once the above steps are complete, you will be able to
access the local version at http://localhost:4800.


#### External Conf YAML
This is what a sample external conf file looks like:
```yaml
# Data to access an external grafana server.
# If any fields are not present, then the user
# will be prompted for them.
url: 'https://official.grafana.server'
username: 'bigbob'
password: 'supersecret'

# The passwords for each database can optionally
# be specified. If they are not specified, then
# they must be entered manually because grafana
# does not export them.
databases:
  - name: 'PostgreSQL'
    password: 'donttellanyone'
  - name: 'InfluxDB'
    password: 'topsecret!'
```

### Export
The export operation is the inverse of the import operation.
You use it to update an external grafana server.


#### Operations
The sequence of operations to perform an export operation are:

1. create the external conf file
1. save the local grafana service to a zip file
1. export to the external service.


#### Commands
Here are the commands:

```bash
$ edit export.yaml
$ time pipenv run grape save -v -n foo -g 4800 -f foo.zip
$ time pipenv run grape export -v -x export.yaml -f foo.zip
```


#### External Conf YAML
This is what a sample external conf file looks like:
```yaml
# Data to access an external grafana server.
# If any fields are not present, then the user
# will be prompted for them.
url: 'https://official.grafana.server'
username: 'bigbob'
password: 'supersecret'

# The passwords for each database can optionally
# be specified. If they are not specified, then
# they must be entered manually because grafana
# does not export them.
databases:
  - name: 'PostgreSQL'
    password: 'donttellanyone'
  - name: 'InfluxDB'
    password: 'topsecret!'
```


### Status
Generate a status report of all docker containers associated with
grape.
```bash
$ grape status -v
INFO 2021-01-11 16:36:14,134 status.py:187 - status
  Name           Type  Version  Status   Started                         Elapsed   Id          Image              Created                         Port
  grape_test1gr  gr    0.4.3    running  2021-01-12T00:34:48.618074371Z  00:01:25  f85986a629  sha256:9ad3ce931a  2021-01-12T00:34:48.259793436Z  4700
  grape_test1pg  pg    0.4.3    running  2021-01-12T00:34:49.13129136Z   00:01:25  28e4372c1b  sha256:0b0b68fee3  2021-01-12T00:34:48.673554391Z  4701
  grape_test2gr  gr    0.4.3    running  2021-01-12T00:35:11.212822109Z  00:01:02  632389a8d8  sha256:9ad3ce931a  2021-01-12T00:35:10.865475598Z  4710
  grape_test2pg  pg    0.4.3    running  2021-01-12T00:35:11.692884845Z  00:01:02  65b9b2186b  sha256:0b0b68fee3  2021-01-12T00:35:11.256244428Z  4711
  jbhgr          gr    0.4.3    running  2021-01-11T16:47:24.427558155Z  07:48:49  5368be647f  sha256:9ad3ce931a  2021-01-11T16:47:24.099948853Z  4640
  jbhpg          pg    0.4.3    running  2021-01-11T16:47:24.907664979Z  07:48:49  7cf96782d7  sha256:0b0b68fee3  2021-01-11T16:47:24.459861004Z  4641
INFO 2021-01-11 16:36:14,221 status.py:222 - done
```


### Tree
Generate a tree view of a grape grafana server datasources, folders and dashboards.
```bash
$ pipenv run grape tree -g 4640
jbhgr:4640
  ├─ datasources
  │   └─ jbhpg:1:postgres
  └─ folders
      ├─ JBH:1
      │   └─ dashboards
      │       ├─ Northstar Dashboard Mock:id=5:uid=lC0QCuaMz:panels=33
      │       └─ OKR Initiatives Health:id=6:uid=peAwjuaMk:panels=6
      └─ Northstar:2
          └─ dashboards
              ├─ Jenkins Build Health Details:id=4:uid=ir0QjX-Mz:panels=9
              └─ Jenkins Build Health:id=3:uid=6Q0QCuaGk:panels=70
```


### Tools
This section describes the tools in the local `tools` directory. They
are not integrated into `grape` at this time because they don't
fit the grape idiom but that is a completely subjective decision
which can be revisitied at any time.


#### csv2sql.py
This is a standalone tool to read a CSV data file with a header
row and convert it to SQL instructions to create and populate a table
generically.

It is generic because it figures out the field types by analyzing the
data.

There are a number of options for specifying the output, how to
convert certain values and what SQL types to use for integers,
floats, dates and strings.

It is useful for adding CSV data to your dashboards.

See the help (`-h`) for more detailed information.


#### runpga.sh
There is script called `tools/runpga.sh` that will create a pgAdmin
container for you.

For `demo01` you would run it like this:

```bash
$ tools/runpga.sh demo01pg
```

When it completes it prints out the information necessary to
login into the pgAdmin and connect to the database.


#### upload-json-dashboard.sh
There is a script called `tools/upload-json-dashboard.sh` that will upload
a JSON dashboard to a Grafana server from the command line.

The upload is limited to servers with simple authentication based on a
username and password unless you override it using `-x` and `-n`.

The local dashboard JSON file is creatined by exporting the dashboard
from the Grafana UI with the "Export for sharing externally" checkbox
checked.

This script is useful for transferring a single dashboard from one
server to another.

Although the same function can be accomplished in the UI, this script
allows updates to be automated from the command line.

This script requires that "curl" is installed.

See the script help (`-h`) for more information and examples.


### Samples
There are different samples of how to use this system
in the samples directory tree. Each sample is in its
own directory with a `README.md` that describes what
it does and how to use it.


#### demo01
[This](/samples/demo02)
demo is very basic. It shows, in detail, how to create a simple
model with grafana and a database. There is more information in the
demo README.

Here is how to run it.
```bash
$ make demo01
```

> Note that you must have bash installed for it to work.

The demo01 dashboard looks like this.

!['demo01'](/img/demo01-07-dashboard.png)

Although it looks really simple, this demo shows an automatically generated dashboard that connects to the automatically
generated database and displays its contents.

Click [here](/samples/demo01/README.md) for more information.


#### demo02
[This](/samples/demo02)
demo is more realistic. It shows how to create a model from
a publicly available dataset. There is more information in the
demo README.

Here is how to run it.
```bash
$ make demo02
```
The demo02 dashboard looks like this.
!['demo02'](/img/demo02.png)

Click [here](/samples/demo02/README.md) for more information.


#### demo03
[This](/samples/demo03)
demo shows how to create a dashboard from local data.
There is more information in the README.

Here is how to run it.
```bash
$ make demo03
```
The demo03 dashboard looks like this.
!['demo03'](/img/demo03.png)

Click [here](/samples/demo03/README.md) for more information.


#### demo04
[This](/samples/demo04)
demo shows how to create mock data in a panel which
allows you to prototype dashboards without touching the
database. It is a very powerful idiom.

Here is how to run it.
```bash
$ make demo04
```
The demo04 dashboard looks like this.
!['demo04'](/img/demo04.png)

Click [here](/samples/demo04/README.md) for more information.


### Miscellaneous
This section contains miscellaneous information.


#### Grafana
Grafana was chosen because it is a commonly used open source resource for querying, visualizing,
alerting on, and exploring metrics you are interested in. Many organizations use it for
understanding metrics related to business and engineering operations.


#### Postgres
Postgres was chosen for this project because it a popular database that supports relational data,
time series data and document (NoSQL) data cleanly which supports experimenting with different
data storage models. Other possibilities, like InfluxDB, tend to be more focused in a specific
data storage model like time series data.


#### pgAdmin
For folks that like to use GUI interfaces to databases like `pgAdmin` or `DBeaver`, it is trivial
to create such connections.

If you have `pgAdmin` installed on the host you can connect to the database as
host `localhost:4401` for demo01 or `localhost:4411` for demo02.

If you would prefer to run `pgAdmin` from a local container, you need to get
the gateway IP address of `pgAdmin` container and use that to connect to
port `4401` or `4402`. The gateway is a proxy for the host `localhost`. Here
is how to obtain that for `pgAdmin`:

```bash
$ docker run -d -e PGADMIN_DEFAULT_EMAIL=me@example.com -e PGADMIN_DEFAULT_PASSWORD=password -h pgadmin4 --name pgadmin4 -p 4450:80 dpage/pgadmin4
$ docker inspect pgadmin4 | jq '.[]|.NetworkSettings.Networks.bridge.Gateway'
"172.17.0.1"
```

For the above example, the database host would be `172.17.0.1:4401`
or demo01 or `172.17.0.1L4411` for demo02 when referenced from the
`pgAdmin` docker container created above: `http://localhost:4450`.


### Acknowledgments

* Many thanks to Deron Ferguson for helping me track down and debug problems on windows 10.
* Many thanks to Rob Rodrigues for helping me track down and debug problems on linux as well as his work to add the integration work flow.
