# import
This directory contains a sample that is _not_ fully contained.
It shows how to import an external grafana service into a local
development environment but to use it you must provide a `import.yaml`
file because external services require user names and passwords.

There is a file named `import.yaml.example` that you can use as a
starting point to insert your credentials.

To run the demo:
```bash
$ cp import.yaml.example import.yaml
$ edit import.yaml
$ ./run.sh
```

When the run has completed, you will be able navigate to
http://localhost:4500 to see the imported environment.
