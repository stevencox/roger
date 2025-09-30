### Running Roger

This document outlines some of the ways that Roger can be run. 

### Roger Configuration

Configuration is mainly managed through `roger/roger/config.yaml`.
Each values in this config file can be overridden by shell environment
variables. For instance to override the following : 

```
 kgx:
    biolink_model_version: 1.5.0
    dataset_version: v1.0
``` 

Overridding variables can be exported as:

```shell script
export ROGERENV_KGX_BIOLINK__MODEL__VERSION=1.6
export ROGERENV_KGX_DATASET__VERSION=v1.1
```
Some things to note are: 
* Environment variables should be prefixed by `ROGERENV_`
* Single Underscore `_` character denotes sub-key in the yaml
* Double Underscores `__` are treated as regular underscore
* Keys in yaml are in lower and environment variables that override them should be in upper case. 

### Deploy Script

`roger/bin/deploy` script can be used to deploy Roger's dependencies in either docker or kubernetes.
For full capabilities use:
```shell script
cd roger/bin
./deploy help 
```

##### Docker

For local development we can use docker containers to run backend services that roger depends on.
These are Redis store, Elastic search and Tranql web service.

Eg: 
```shell script
cd roger/bin
./deploy docker config  # to display the configuration (port address and passwords)
./deploy docker start # to start
./deploy help # for help on commands
```

##### Kubernetes

For running on k8s we can configure git branch and docker images by exporting:
```shell script
export NAMESPACE=your-namespace
export RELEASE=roger
export CLUSTER_DOMAIN=cluster.local
export WORKING_GIT_BRANCH=develop
```
deploy using :

```shell script
cd roger/bin
./deploy k8s config  # to display the configuration 
./deploy k8s start # to start
./deploy k8s help # for help on commands
``` 

### Local Development

##### Setup python virtual env

```shell script
cd roger 
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt  
```

##### Configuration

Refer to configuration section to override server names and passwords to 
passwords etc.. to the backend servers. 

For development there is a dev.env file in `roger/bin/` directory with some start
up variables. Modify as needed. The following command can be used to export them into
shell.
```shell script
export $(grep -v'^#' bin/dev.env | xargs 0)
```


##### Run a task 

To run a single task : 

```shell script
python cli.py -l # runs annotatation task 
python cli.py -h # see the full list of available arguments.
```

##### Using the Makefiles

Another way to run roger is as a pipeline, where each task is 
In `roger/roger/bin/` there is a root make file and in the `roger/roger/bin/dug_annotate`,
`roger/roger/bin/dug_indexing` and `roger/roger/bin/roger_graph_build`. 

Running all pipelines end to end:

```shell script
cd roger/roger/bin/
make all
```

Running annotation pipeline:

```shell script
cd roger/roger/bin/
make annotate
```

Running graph pipeline:

```shell script
cd roger/roger/bin/
make graph
```

Running index pipeline:

```shell script
cd roger/roger/bin/
make index
```


