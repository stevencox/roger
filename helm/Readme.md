Roger helm chart 
----

### Introduction

This chart can be used to run Roger (graph curation pipeline) interfaced with
 [tranql](https://github.com/NCATS-Tangerine/tranql) used as a query engine.


![image](https://user-images.githubusercontent.com/45075777/107399084-54983300-6ace-11eb-929d-0d8113405cce.png)

This chart has Airflow and Redis added as dependencies. 

### Pre-install Volumes and Secrets

##### PVC


This installation requires a PVC `roger-data-pvc` to store Roger pipeline data. Here is a template
to create the PVC:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: roger-data-pvc
spec:
  storageClassName:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 20Gi
```

---

#### Secrets:

There are two secrets for airflow required for Git syncronization.

This is used by `airflow.airflow.config.AIRFLOW__KUBERNETES__GIT_SSH_KEY_SECRET_NAME`
 ```yaml
    kind: Secret
    apiVersion: v1
    metadata:
      name: airflow-secrets
    data:
      gitSshKey: >-
        ######
    type: Opaque
 ```

This used by `airflow.dags.git.secret`

```yaml
kind: Secret
apiVersion: v1
metadata:
  name: airflow-git-keys 
data:
  id_rsa: <private-key-base64-encoded>    
  id_rsa.pub: <public-key-base64-encoded>
  known_hosts: <known-hosts>
type: Opaque
```

### Parameters

#### Tranql

| Parameter | Description | Default |
| --------- | ----        | ----    | 
| `tranql.image` |  Docker image | `renciorg/tranql-app`
| `tranql.imageTag` | Docker image tag  | `develop-test`
| `tranql.replicas` | Web server replicas  | `1`
| `tranql.port` | Web server port  | `8081`
| `tranql.gunicorn.workerCount` | Gunicorn worker thread counts | `4`
| `tranql.gunicorn.workerTimeout` | Gunicorn worker timeout  | `300`
| `tranql.service.type` |  Tranql service | `ClusterIP`


#### Airflow 

For more details on these defaults and additional customization,
please refer to [Airflow helm docs](https://github.com/helm/charts/tree/master/stable/airflow).

> **Note**: We use a custom build airflow image(`renciorg/apache-airflow-1.10.14-python-3.8-git`) to support pip installs form git.


| Parameter |  Default |
| --------- |  ----    | 
| `airflow.airflow.image.repository` | `renciorg/apache-airflow-1.10.14-python-3.8-git`
| `airflow.airflow.image.tag` | `latest`
| `airflow.airflow.executor` | `KubernetesExecutor`
| `airflow.airflow.fernetKey` | `7T512UXSSmBOkpWimFHIVb8jK6lfmSAvx4mO6Arehnc=`
| `airflow.airflow.config.AIRFLOW__CORE__SECURE_MODE` | `True`
| `airflow.airflow.config.AIRFLOW__API__AUTH_BACKEND` | `airflow.api.auth.backend.deny_all`
| `airflow.airflow.config.AIRFLOW__WEBSERVER__EXPOSE_CONFIG` | `False`
| `airflow.airflow.config.AIRFLOW__WEBSERVER__RBAC` | `False`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__GIT_REPO` | `ssh://git@github.com/helxplatform/roger.git`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__GIT_SSH_KEY_SECRET_NAME` | `airflow-secrets`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__GIT_BRANCH` | `develop`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__GIT_DAGS_FOLDER_MOUNT_POINT` | `/opt/airflow/dags`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__GIT_SYNC_DEST` | `roger`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__DAGS_VOLUME_SUBPATH` | `roger`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__DELETE_WORKER_PODS` | `FALSE`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__WORKER_CONTAINER_REPOSITORY` | `renciorg/roger-executor`
| `airflow.airflow.config.AIRFLOW__KUBERNETES__WORKER_CONTAINER_TAG` | `0.26`
| `airflow.airflow.config.AIRFLOW__CORE__LOAD_EXAMPLES` | `False`
| `airflow.airflow.config.GUNICORN_CMD_ARGS` | `--log-level WARNING`
| `airflow.airflow.extraPipPackages` | `['Babel==2.8.0', 'biolink-model==1.2.5', 'biolinkml==1.5.8', 'redisgraph==2.1.5', 'git+https://github.com/RedisGraph/redisgraph-bulk-loader.git', 'flatten-dict', 'git+https://github.com/stevencox/kgx.git']`
| `airflow.airflow.extraVolumeMounts` | `[{'name': 'roger-data', 'mountPath': '/dags/roger/data'}]`
| `airflow.airflow.extraVolumes` | `[{'name': 'roger-data', 'emptyDir': {}}]`
| `airflow.web.service.type` | `ClusterIP`
| `airflow.workers.replicas` | `1`
| `airflow.dags.git.url` | `ssh://git@github.com/helxplatform/roger.git`
| `airflow.dags.git.ref` | `redis-helm`
| `airflow.dags.git.secret` | `airflow-git-keys`
| `airflow.dags.git.privateKeyName` | `id_rsa`
| `airflow.dags.git.repoHost` | `github.com`
| `airflow.dags.git.repoPort` | `22`
| `airflow.dags.git.gitSync.enabled` | `True`
| `airflow.dags.git.gitSync.refreshTime` | `60`
| `airflow.dags.installRequirments` | `True`
| `airflow.postgresql.enabled` | `True`
| `airflow.redis.enabled` | `False`


#### Redis 

For more details on these values and additional configuration options please
refer to this [Redis helm chart](https://github.com/bitnami/charts/tree/master/bitnami/redis).

| Parameter |  Default |
| --------- |  ----    | 
| `redis.image.repository` | `redislabs/redisgraph`
| `redis.image.tag` | `2.2.13`
| `redis.redis.command` | `redis-server`
| `redis.clusterDomain` | `cluster-domain`
| `redis.cluster.slaveCount` | `1`
| `redis.usePassword` | `False`
| `redis.master.command` | `nil`
| `redis.master.readinessProbe.enabled` | `False`
| `redis.master.livenessProbe.enabled` | `False`
| `redis.master.extraFlags` | `['--loadmodule /usr/lib/redis/modules/redisgraph.so']`
| `redis.slave.command` | `nil`
| `redis.slave.readinessProbe.enabled` | `False`
| `redis.slave.livenessProbe.enabled` | `False`
| `redis.slave.extraFlags` | `['--loadmodule /usr/lib/redis/modules/redisgraph.so']`

 
### Installation

To install `my-release` to kubernetes.

```shell script
$ helm dependency update . 
$ helm install my-release . 
```


### Upgrading

To upgrade `my-release` with an example change to `tranql.imageTag` value.

```shell script
$ helm upgrade --set tranql.imageTag=0.33 my-release . 
```


### Uninstalling

To remove `my-release`

```shell script
$ helm uninstall my-release
```