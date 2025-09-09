# Deployment with Roger CLI

## QUICK Local Set Up

This is list steps to produce a local deployment of Roger. This set up does NOT use airflow and instead only uses the Roger CLI via **Makefile** commands.

### Prerequsite Steps

- Set up Roger dependencies by ensuring that the `.env` has all the correct information.
- Run the following docker compose commands
  - `docker compose up tranql -d`: starts up tranql which is the API handlerfor redis graph in the `graph` stage
  - `docker compose up redis -d`: starts up redis which will be used via redis graph for the `graph` stage
  - `docker compose up dug -d`: starts up dug API to work as the API handler for elastic search in the `index` stage
  - `docker compose up elasticsearch -d`: starts up elastic search for the `index` stage

### Roger CLI Steps

1) `python3 -m venv ~/.environments/roger`
2) `source ~/.environments/roger/bin/activate`
3) `pip install -r requirements.txt`
4) `export PYTHONPATH=$PWD/dags`
5) Change the elasticsearch and redisgraph `host` values to localhost in `dags/roger/config/config.yaml`
6) Get the S3 Bucket credentials (access_key, bucket, host, secret_key) and export them as environment variables with ROGER_S3_ in the front of the value like: `ROGER_S3_ACCESS__KEY=XXXXKEYXXXX`
7) `cd bin/` and here either run `make all` OR separate the commands into three steps:
   1) `make annotate`: executes the CLI related commands found in `bin/dug_annotate/Makefile`
   2) `make graph`: executes the CLI related commands found in `bin/roger_graph_build/Makefile`
   3) `make index`: executes the CLI related commands found in `bin/dug_index/Makefile`
