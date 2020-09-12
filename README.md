# grape
[![Releases](https://img.shields.io/github/release/eSentire/grape.svg?style=flat)](https://github.com/eSentire/grape/releases)

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
1. [Samples](#samples)
   1. [demo01](#demo01)
   1. [demo02](#demo02)
   1. [demo03](#demo03)
   1. [demo04](#demo04)
1. [Miscellaneous](#miscellaneous)
   1. [Grafana](#grafana)
   1. [Postres](#postgres)
   1. [pgAdmin](#pgadmin)
   1. [runpga.sh](#runpgash)

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

See [demo01](https://github.com/jlinoff/grape/tree/master/samples/demo01)
and [demo02](https://github.com/jlinoff/grape/tree/master/samples/demo02)
for additional grafana screenshots and database access details using `psql`.


## Prerequisites
To use this you must have:
1. docker (https://docs.docker.com/get-docker/)
1. bash
   1. If you are running on windows you need a run-time like cygwin.
   1. It is only needed for the samples.
1. python-3.8 or later
1. pipenv
1. git (https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
1. make
   1. If you are running on windows you need a run-time like cygwin.


### Setup
Do these steps to get started:
```bash
$ git clone git@git.eng.esentire.com:jlinoff/grape.git
$ cd grape
$ make
```
> This can take awhile to run.

To see all of the available make targets: `make help`.

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

This will create two docker containers: `examplegr` and
`examplepg`. It will also map the local `examplepg` directory to the
database container to save database results if the container is
restarted for any reason and, finally, it will connect the database as
a source in the grafana sercer.

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
$ cp x.sql examplepg/tmp  # makes it visible as /tmp/x.sql
$ docker exec -it examplepg psql -d postgres -U postgres -1 < /tmp/x.sql
```

### Save
The save operation captures the specified model in a zip file.
It is what you use to capture changes.

```bash
$ pipenv run grape save -v -n example -g 4760 -f /tmp/save.zip
```

### Load
The load operation updates the model from a saved state (zip file).

```bash
$ pipenv run grape load -v -n example -g 4600 -f /tmp/save.zip
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

### Samples
There are different samples of how to use this system
in the samples directory tree. Each sample is in its
own directory with a `README.md` that describes what
it does and how to use it.

#### demo01
The first demo is very basic. It shows, in detail, how to create a simple
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

#### demo02
The second demo is more realistic. It shows how to create a model from
a publicly available dataset. There is more information in the
demo README.

Here is how to run it.
```bash
$ make demo02
```
The demo02 dashboard looks like this.
!['demo02'](/img/demo02.png)


#### demo03
This demo shows how to create a dashboard from local data.
There is more information in the README.

Here is how to run it.
```bash
$ make demo03
```
The demo03 dashboard looks like this.
!['demo03'](/img/demo03.png)

#### demo04
This demo shows how to create mock data in a panel which
allows you to prototype dashboards without touching the
database. It is a very powerful idiom.

Here is how to run it.
```bash
$ make demo04
```
The demo04 dashboard looks like this.
!['demo04'](/img/demo04.png)


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

#### runpga.sh
There is script called `tools/runpga.sh` that will create a pgAdmin
container for you.

For `demo01` you would run it like this:

```bash
$ tools/runpga.sh demo01pg
```

When it completes it prints out the information necessary to
login into the pgAdmin and connect to the database.
