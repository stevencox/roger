# Roger

Roger is an automated graph-data curation pipeline. It takes biomedical dataset metadata (dbGaP data dictionaries, study descriptions, common data elements) and turns it into two searchable products:

1. **Elasticsearch indexes** of variables, studies, sections, concepts, and knowledge-graph answers — what the [Dug](https://github.com/helxplatform/dug) semantic search UI queries.
2. **A FalkorDB/RedisGraph knowledge graph** built from [KGX](https://github.com/biolink/kgx) files, queried via TranQL.

Everything runs as [Apache Airflow](https://airflow.apache.org/) 3.x DAGs. Roger is part of the [HeLx](https://helx.renci.org/) platform.

---

## Start here: the two workflows

Roger has two largely independent pipelines. Knowing which one you're looking at is the fastest way to orient yourself.

### 1. `annotate_and_index` — metadata → Elasticsearch

Per dataset (TopMed, BDC, AnVIL, HEAL, RADx, …):

```
annotate ──> crawl_tranql ──┐
     │                      ├──> [wipe ES] ──> index_variables ──> validate
     └──> make_kgx          │                  index_concepts  ──> validate
                            └─────────────────────────────────────────────>
```

- **annotate** — parse source files into Dug elements, annotate free text against ontologies (via a normalizer/synonym service), producing concepts.
- **crawl_tranql** — expand each concept through the knowledge graph via TranQL, attaching "kg answers".
- **make_kgx** — emit KGX nodes/edges so annotations can flow into the graph build.
- **index / validate** — push into Elasticsearch, then run search queries asserting the documents are actually findable.

### 2. `knowledge_graph_build` — KGX → FalkorDB

```
get ──> merge ──> schema ──> bulk create ──> bulk load ──> validate ──> check tranql
```

- **get** — fetch KGX files for a configured data version.
- **merge** — deduplicate nodes across files, unioning their properties.
- **schema** — infer the property set and type of every node/edge category.
- **bulk create** — write CSVs for the FalkorDB bulk loader.
- **bulk load** — load the graph.
- **validate** — run timed test queries as a sanity check.

A third DAG, `index_only`, re-runs just the Elasticsearch half from artifacts already stored in LakeFS — useful after promoting data from dev to prod without re-annotating anything.

---

## Repo tour

```
src/roger/            the actual package (Docker sets PYTHONPATH here)
├── tasks.py          ALL Airflow glue: config injection, LakeFS I/O,
│                     incremental state, DAG/task-group builders.
│                     The densest file in the repo — read it second.
├── pipelines/        one class per dataset, all subclassing DugPipeline
│   ├── base.py       DugPipeline: annotate, crawl_tranql, index_*, validate_*
│   └── README.md     how to add a new dataset  <-- read this to contribute
├── core/             graph side: base.py orchestrator, bulkload.py,
│                     redis_graph.py, storage.py (all path conventions)
├── models/kgx.py     KGX merge + schema inference rules
├── config/           config.yaml (+ dev-config.yaml, test-config.yaml)
└── cli.py            run the graph build without Airflow

dags/                 DAG definitions only; logic lives in src/roger
├── annotate_and_index.py
├── knowledge_graph_build.py
└── index_only.py

scripts/              one-off maintenance tooling
tests/unit/           the fast tests; start here
bin/                  Helm/k8s deployment helpers (bin/roger init|start|stop)
```

Reading order for a new contributor: this file → `src/roger/pipelines/README.md` → `src/roger/tasks.py` → the dataset pipeline you care about.

---

## Quickstart

Requires Docker, Docker Compose, Make, and Python 3.12 if you want to run anything on the host.

```shell
make stack.init    # one-time: docker-compose up airflow-init
make stack         # bring everything up
```

That gives you Airflow UI on `:8080`, Postgres, Elasticsearch on `:9200`, and Redis Stack / FalkorDB on `:6379`. Open the UI, pick a DAG, and hit trigger.

Without Make:

```shell
mkdir -p logs plugins local_storage/elastic
docker-compose up airflow-init
docker-compose up
```

To wipe local state between runs: `make clean` (removes logs and `local_storage`).

For a no-Airflow local run driven entirely by the CLI and Makefiles, see **`roger-cli-steps.md`**.

---

## Running the tests

There are **no Roger dependencies installed on your host** and the dependency set is awkward (Dug needs Python 3.12; several deps install from git). Don't fight it — use a container.

If you have a built Roger image:

```shell
docker run --rm -v $PWD:/repo:ro -w /repo --user root \
  --entrypoint bash containers.renci.org/helxplatform/roger:<tag> -c \
  "pip install -q pytest flake8; \
   PYTHONPATH=/repo/src python -m pytest tests/unit -q; \
   flake8 --ignore=E,W dags"
```

Otherwise a `python:3.12-slim-trixie` container plus `pip install -r requirements.txt` works; budget ~5 minutes for the git dependencies.

Make targets (`make test.unit`, `make test.lint`, `make test`) assume the deps are already importable, so they're really for CI and for inside the image.

---

## Configuration

`RogerConfig` loads `src/roger/config/config.yaml`, then overlays environment variables prefixed `ROGER_`. Dots in the config path become `_`, and a literal underscore in a key name is escaped by doubling it:

```shell
ROGER_REDISGRAPH_HOST=localhost                      # redisgraph.host
ROGER_ELASTICSEARCH_HOST=localhost                   # elasticsearch.host
ROGER_LAKEFS__CONFIG_ENABLED=true                    # lakefs_config.enabled
ROGER_DUG__INPUTS_DATA__SETS=topmed:v2.0,anvil:v1.0  # which pipelines to build
```

That last one is the important knob: it's a comma-separated list of `pipeline_name:version`, read directly by the DAG files. The name selects a class from `src/roger/pipelines/`; the version is the external LakeFS ref that pipeline reads from (often a **tag**, not a branch). Point `ROGER_CONFIG_FILE` at a different file to swap the whole config.

Main sections: `redisgraph`, `kgx`, `dug_inputs`, `bulk_loader`, `annotation`, `indexing`, `elasticsearch`, `lakefs_config`, `validation`.

---

## Concepts you'll hit early

### LakeFS is the source of truth

When `lakefs_config.enabled` is on, every task pulls its inputs from a LakeFS repo/branch, works in a task-specific local directory, writes its outputs back, and commits them on a temp branch that gets merged on success. Outputs are addressed by task id, so `annotate_and_index/{group}.{task}/…` is where a task's results live. Nothing is passed between tasks in memory.

### Runs are incremental

Re-annotating every dataset on every run is prohibitively expensive, so each task records the last source commit it successfully consumed (in an Airflow Variable) and only processes what changed since. If nothing changed, the task skips and the group still completes green.

Force a full run with DAG params: `{"incremental": false}`.

### Elasticsearch is derived, not authoritative

The ES indexes are shared across all datasets, and they're wiped and rebuilt from whatever files remain in LakeFS. That's deliberate: it means a source file deleted upstream disappears from search without any per-document bookkeeping. It also means a run that reaches the wipe but fails partway leaves the indexes incomplete until the next good run.

### Artifacts are jsonpickle, and that has teeth

Intermediate files (`elements.txt`, `concepts.txt`, `expanded_concepts.txt`) are jsonpickle-encoded Python objects, so they embed fully-qualified class paths. If a Dug release moves those classes, old artifacts silently decode to plain dicts instead of raising, and you get a confusing `'dict' object has no attribute 'id'` during indexing. Fix is `scripts/migrate_pickled_classes.py`, not re-annotation. See `CLAUDE.md` for the runbook.

---

## KGX merge and schema rules

Worth knowing before debugging a weird graph load:

- Duplicate nodes across files are merged, keeping the union of their properties.
- Every node of a given type must end up with exactly the same property set, so the schema step resolves conflicts:
  - a property flip-flopping between bool / float / int becomes **string**
  - a property that is ever a string and never a list becomes **string**
  - a property that is ever a list becomes a **list**
- The FalkorDB bulk loader requires every column populated, so entities are grouped by which attributes actually have values and written to separate CSVs: `data/bulk/nodes/<type>.csv-<group>-<hash>`. Column separator is `0x1E`.

---

## Adding a dataset

Add a subclass of `DugPipeline` in `src/roger/pipelines/`, set `pipeline_name` (and usually `parser_name` and `input_version`), then add it to `ROGER_DUG__INPUTS_DATA__SETS`. The DAGs build task groups for whatever is listed there — no DAG edits needed.

Full walkthrough with the customization hooks: **`src/roger/pipelines/README.md`**.

---

## Deploying to Kubernetes

Roger installs via [Helm](https://helm.sh). Prerequisites:

1. **A persistent volume** — create a `ReadWriteMany` PVC named `roger-data-pvc` for Roger's data directory.
2. **Git SSH secrets** — `airflow-secrets` (key `gitSshKey`, used by `AIRFLOW__KUBERNETES__GIT_SSH_KEY_SECRET_NAME`) and `airflow-git-keys` (`id_rsa`, `id_rsa.pub`, `known_hosts`, used by `airflow.dags.git.secret`), both base64-encoded.

Then:

```shell
cd bin/
export NAMESPACE=<your namespace>
export RELEASE_NAME=<install name, e.g. airflow>
export CLUSTER_DOMAIN=cluster.local
./roger init     # initialize helm dependencies (airflow + redis charts)
./roger start    # install; follow the printed notes for port-forwarding
```

`./roger stop` tears it down, `./roger restart` cycles it. Trigger config for a run targeting a specific graph:

```json
{"redisgraph": {"host": "<redis-master-service-name>", "port": 6379, "graph": "graph-name"}}
```

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `'dict' object has no attribute 'id'` during indexing | LakeFS artifacts written by an older Dug; run `scripts/migrate_pickled_classes.py` |
| `'NoneType' object has no attribute 'es'` | An ES method ran before `search_obj`/`index_obj` were lazily built |
| Tasks skip with "No changes in source refs" | Working as intended — incremental found nothing new. Re-run with `{"incremental": false}` to force |
| Search results missing after a partial run | The ES wipe ran but a rebuild task failed; re-run the DAG |
| `make build` fails on a missing version file | Known: the Makefile reads `dags/_version.py`, which no longer exists. Version lives in `setup.cfg` |

---

## Further reading

- **`CLAUDE.md`** — deep architecture notes: incremental state machine, deletion propagation, LakeFS task wiring, the Dug data-model migration runbook, and accumulated gotchas.
- **`src/roger/pipelines/README.md`** — adding and customizing dataset pipelines.
- **`roger-cli-steps.md`** — local deployment driven by the CLI instead of Airflow.
- **`bin/Readme.md`** — deployment helper scripts.

## Key dependencies

[Dug](https://github.com/helxplatform/dug) (annotation and search) · `dug_data_model` (the shared data classes) · [avalon](https://github.com/helxplatform/avalon) (LakeFS client) · `falkordb` + `falkordb-bulk-loader` · `bmt` (Biolink Model Toolkit) · Apache Airflow 3.2.0

## License

See [LICENSE](LICENSE).
