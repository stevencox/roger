# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Roger Is

Roger is an automated graph-data curation pipeline that transforms KGX (Knowledge Graph Exchange) files into a FalkorDB/RedisGraph database, orchestrated by Apache Airflow (3.x). It processes biomedical datasets (TopMed, BDC, AnVIL, dbGaP, HEAL, RADx, SPARC, NIDA, KFDRC, CRDC, CTN, BACPAC, etc.) through annotation (via Dug), Elasticsearch indexing, KGX merge/normalization, schema inference, and bulk loading.

Two largely independent workloads live here:

1. **`annotate_and_index`** — per-dataset Dug annotation, TranQL concept expansion, KGX conversion, and Elasticsearch indexing. This is the incremental one (see below).
2. **`knowledge_graph_build`** — the KGX merge → schema → bulk-load → validate chain into FalkorDB.

## Commands

```bash
make install            # pip install -r requirements.txt (Python 3.12 in CI/Docker)
make test.lint          # flake8 dags  (CI uses: flake8 --ignore=E,W dags)
make test.unit          # pytest tests/unit
make test.integration   # pytest tests/integration
make test               # unit + integration

# Single test
python3 -m pytest tests/unit/test_config.py::test_merge -v

# Local stack (Airflow UI on :8080, Postgres, Elasticsearch :9200, Redis Stack/FalkorDB :6379)
make stack.init         # docker-compose up airflow-init (first time)
make stack              # docker-compose up

make clean              # wipe logs and local_storage
```

The package source lives in **`src/roger/`**; the Docker image sets `PYTHONPATH=/opt/airflow/dags/repo/src/` so DAGs can import it.

### Broken/stale Makefile targets

- `make build` and anything using `VERSION` read `./dags/_version.py`, **which does not exist**. The real version is `version = 0.10.4.2` in `setup.cfg`. Bump that and build/tag the image manually, or restore `dags/_version.py` (note `dags/__init__.py` still does `from ._version import version as __version__`, so that import is also dead).
- `test.doc` and parts of `rm_dirs` reference a removed `dags/roger/` copy.

### Running tests without a local environment

There are **no roger dependencies installed on the host** — no Airflow, no Dug, no avalon. The system `python3` is 3.11 and Dug requires 3.12 (`typing.override`). Run everything in a container instead.

Fastest path is the already-built roger image, which has every dependency including the exact Dug/`dug_data_model` versions in production:

```bash
docker run --rm -v $PWD:/repo:ro -w /repo --user root \
  --entrypoint bash containers.renci.org/helxplatform/roger:<tag> -c \
  "pip install -q pytest flake8; PYTHONPATH=/repo/src python -m pytest tests/unit -q; \
   flake8 --ignore=E,W dags"
```

Alternative (no image handy): a `python:3.12-slim-trixie` container plus a full `pip install` of `requirements.txt`'s git dependencies — works, but takes ~5 minutes with a cold pip cache.

Notes:
- `dags/__pycache__` is root-owned by docker, so host `py_compile` of `dags/` fails with EACCES. Use `ast.parse` for a syntax-only check.
- Mount `:ro` for reading/tests; mount read-write and pass `--user $(id -u):$(id -g)` for anything that writes, so files stay owned by you.

## Architecture

### Knowledge graph build data flow

```
GET KGX files → MERGE nodes (dedup) → CREATE SCHEMA (type inference)
  → CREATE BULK CSVs → BULK LOAD into FalkorDB → VALIDATE (test queries) → CHECK TRANQL
```

### Layers

- **`src/roger/core/`** — graph operations. `base.py` has the `Roger` orchestrator class and top-level functions (`get_kgx`, `merge_nodes`, `create_schema`, `create_bulk_load`, `bulk_load`, `validate`). `bulkload.py` generates CSVs for the FalkorDB bulk loader; `redis_graph.py` wraps the `falkordb` SDK; `storage.py` owns all path conventions and file globbing.
- **`src/roger/models/kgx.py`** — KGX merge and schema inference. Type-conflict rules: bool/float/int conflicts → string; any list value → list.
- **`src/roger/pipelines/`** — one class per dataset, all inheriting `DugPipeline` (`base.py`). A pipeline defines `pipeline_name`, optional `parser_name`, `input_version`, file discovery, and the annotate/crawl/index/KGX-convert steps. See `src/roger/pipelines/README.md` for adding a new dataset.
- **`src/roger/tasks.py`** — all Airflow glue: config injection, LakeFS I/O, incremental state, and the DAG-building helpers. The biggest and most subtle file in the repo.
- **`dags/`** — `knowledge_graph_build.py`, `annotate_and_index.py`, `index_only.py`.
- **`src/roger/cli.py`** — non-Airflow CLI: `python3 -m roger --get-kgx --merge-kgx --create-schema --create-bulk --insert --validate -d <data_dir>`.
- **`scripts/`** — one-off maintenance tooling; see the data-model migration section.

### `annotate_and_index` DAG shape

File-producing work and Elasticsearch work are deliberately **separate task groups**, because lakefs is the source of truth and ES is a derived index that gets rebuilt wholesale:

```
init
  └─> {name}_dataset_pipeline_task_group      (one per dataset, incremental)
          annotate_{name}_files
            ├─> make_kgx_{name}
            └─> crawl_{name}
                  └─> complete_{name}          (trigger_rule="none_failed")
  └─> wipe_es_indexes                          (ONE global task, all datasets)
        └─> {name}_es_index_task_group          (one per dataset, always full)
              index_{name}_variables ─> validate_{name}_index_variables
              index_{name}_concepts  ─> validate_{name}_index_concepts
                  └─> complete_{name}
                        └─> finish              (trigger_rule="none_failed")
```

Why it is split this way:

- ES index names are **global and shared across every dataset** (see `indexing.*_index` in `config.yaml`). A per-dataset wipe would destroy sibling datasets' documents, so there is exactly one `wipe_es_indexes` task sitting between the file groups and the ES groups.
- The file groups run incrementally. The ES groups are built with `incremental_pull=False`, so they always pull the *complete* set of annotate/crawl outputs from lakefs and reindex from scratch. That is what makes upstream **deletions** work: a file removed from a source repo is removed from lakefs, so it simply isn't there during the rebuild and its documents never come back. No per-document ES bookkeeping.
- ES document ids are stable (`element.id`, `concept_id`), so reindexing is an upsert and retries are safe.

**Caveat:** the wipe is unconditional. Every run that reaches it empties all indexes and then repopulates them. If a file group fails and its ES group is skipped, the indexes end up partially populated until the next successful run.

### `index_only` DAG

`dags/index_only.py` re-indexes Elasticsearch from `annotate_and_index` outputs **already committed to the runtime repo** — for example after merging the dev runtime branch into prod. No annotate or crawl re-runs. `create_index_only_taskgroup` pulls inputs by explicit path (`{ANNOTATE_DAG_ID}/{group_id}.{task_id}/`) from the configured runtime repo/branch, with `params={"incremental": False}`.

Note the input pairing, which is easy to get wrong: `validate_indexed_variables` reads only annotated elements, while `validate_indexed_concepts` pairs expanded concepts (crawl output) against annotated elements (annotate output) and asserts matching counts — so it needs **both** prefixes.

## Incremental ingestion

The problem: `annotate_{slug}_files` downloads from external LakeFS repos that keep growing, and re-annotating everything on every run is expensive for no gain. Since lakefs is version-oriented, each task instead diffs against the last commit it successfully consumed.

### State storage

Per-task Airflow Variables, keyed by `incremental_state_key()`:

```
roger_incr::{dag_id}::{task_id}::{repo}@{branch}
```

Use `from airflow.sdk import Variable` — `airflow.models.Variable` does direct DB access and is blocked on Airflow 3.x workers (`tasks.py` imports the SDK one with a fallback).

State is **only advanced after a successful commit+merge**, inside
`avalon_commit_callback`'s try block, so a failed merge can never mark
unprocessed commits as consumed. That merge failure is re-raised rather than
logged and dropped: the `clean_up` at the end of the callback deletes the
local output, so swallowing it destroyed the work *and* reported success.

### Flow through one task

1. **`setup_input_data`** (the `pre_execute` hook) groups the task's configured repos by `(repo, branch)`. For each group it resolves the ref tip, reads the last-consumed commit from the Variable, and diffs.
2. **`resolve_ref_tip`** uses `refs_api.log_commits(ref, amount=1)` — **not** `branches_api.get_branch`, because dataset version refs (e.g. `topmed:v2.0`) are frequently **tags, not branches**.
3. **`get_changed_files`** does the diff roger-side via `refs_api.diff_refs` + `pagination_helper`, keeping `removed` entries (avalon's own `get_changes` drops them) and prefix-filtering with trailing-slash normalization. `'*'` or empty means no filter; `conflict`/`prefix_changed` are ignored.
4. Downloads are pinned to the **resolved tip commit**, not the branch name, so a push mid-run can't produce a torn read.
5. First run, `incremental=False`, `incremental_pull=False`, or a `NotFoundException` all fall back to a full `get_files(changes_only=False)`.
6. If nothing changed in any group, the task raises `AirflowSkipException`, which skips it and cascades through the group. `complete_{name}` and `finish` use `trigger_rule="none_failed"` so a skipped group still finishes green.
7. `write_state_file` persists the resolved tips to a JSON file next to the task dir (`generate_dir_name_from_task_instance(..., suffix='state')`). This file is the channel from `pre_execute` to the success callback — the callback must **never** re-resolve the branch itself, or commits that landed mid-run would be marked consumed without being processed.

Downstream tasks are incremental the same way, diffing roger's own output-repo prefixes (`{dag_id}/{upstream_task_id}/`).

### Deletion propagation

When the diff reports removals, `avalon_commit_callback` maps them to derived outputs and deletes those on the temp branch before the merge, so removals land atomically with the rest of the commit:

- `removed_bases()` maps a removed source path to a base name — first path segment under `{dag}/{task}/` for roger-repo paths, basename minus extension for external repos.
- `stale_output_paths()` matches existing outputs as `rel.startswith(base + '/')` or `rel == f"{base}_kgx.json"`.
- Deletion goes through `objects_api.delete_objects(PathList(...))` + a `commits_api.commit`.

This is a **heuristic**, deliberately fail-safe: archive-style sources (one tarball expanding into many files) won't map 1:1, so nothing is deleted for them rather than the wrong thing being deleted. A `.removed_files.json` manifest is also written on every run with state — as a dotfile, because `storage.py` readers glob `*.json`/`**/*.json` over pulled task outputs and glob skips dotfiles. Writing it every run (not just on removals) guarantees `put_files` has content even on a removal-only run.

### dbGaP sibling files

`find_sibling_files()` handles a wrinkle specific to dbGaP data dicts: the parser needs a sibling `GapExchange_<dir>` file in the same lakefs directory for study name/description, but an incremental diff only carries the changed data dicts. So each affected directory is listed and any marker file not already downloaded is pulled in.

### Turning it off

`params={"incremental": false}` on a DAG run forces a full pull everywhere. Per-task, `create_python_task(..., incremental_pull=False)` opts a single task out permanently (this is what the ES groups use).

## Annotation cost, caching, and resume

Annotation is the dominant cost in the whole repo, and two structural facts
explain nearly all of it.

**dbGaP parsers emit the study element into every data-dict file.** So a study
with 55,000 data dicts annotates its study description 55,000 times.
Measured on `bdc-parent` (61,597 XML files, **24 distinct studies**; Framingham
`phs000007.v35.p16` alone is 54,986 files):

| | per file |
|---|---|
| study element (the same one every time) | ~53.5 s |
| variable element (what the file actually contributes) | ~1.4 s |

That is 55 s/file, 39 days for the dataset, **96% of it recomputing 24
answers**.

**Dug's cached session cached only one of its four calls.**
`DugFactory.build_http_session` returns `requests_cache.CachedSession`, whose
`allowable_methods` defaults to `('GET', 'HEAD')`. Of the four annotation
calls, only node normalization is a GET (`DefaultNormalizer.make_request`,
`dug/core/annotators/_base.py`); nemo token classification, sapbert, and
name-resolution synonyms are all **POST** and so were never cached.

`roger.utils.http_utils.enable_post_caching` fixes it
(`annotation.cache_post_requests`, on by default). The request body is part of
requests_cache's key for POST, so this is correct, not a heuristic. Faster
annotator endpoints do not help here: the bottleneck is call *count*.

The same function also sets `expire_after`, which dug never did — so the
normalizer GETs that *were* being cached had no expiry and grew unbounded.
See the eviction note below.

Keep `annotation.http_cache_expire_seconds` **nonzero** (default 30 days).
requests_cache's redis backend writes entries with `SETEX` only when an expiry
is set. That makes annotation cache keys volatile while the FalkorDB graph keys
in the same redis stay permanent — so redis can be given a `maxmemory` with
`volatile-lru` and will evict cache before it ever touches the graph. With no
expiry the cache is permanent and unbounded, and under `noeviction` (the
deployed default, with `maxmemory 0`) it grows until the pod is OOMKilled,
taking the loaded graph with it.

`annotation.annotate_workers` (default 4) threads `annotate_files` over input
files. Files are wholly independent — own parse, own `Crawler`, own output dir
— and the work is nearly all HTTP wait, so this scales despite the GIL. Each
worker gets its own session and annotator via
`DugPipeline.thread_annotation_context`; the response cache is shared, so
workers still see each other's annotations. Element-level concurrency is not
possible without changing dug: `Crawler.annotate_elements` is a serial loop,
and inside it `AnnotateSapbert.__call__` does one classify call, then a sapbert
call per entity, then a normalize *and* a synonym call per identifier, all
sequentially. Log volume scales with worker count — see the ephemeral-storage
history in `roger.logger`.

### Resume

Task output only reaches lakefs on task *success*, so a 39-day task that died
at file 40,000 used to discard all of it and restart at zero. Three pieces make
retries resume:

- `DugPipeline.annotation_is_complete` skips input files whose `elements.txt`
  **and** `concepts.txt` both exist and are non-empty. Both are required: they
  are written in sequence, so a kill between them leaves a directory that looks
  started but is unusable.
- `clean_up(..., keep_output=True)` is the failure callback, so the dead try's
  output survives.
- `reuse_prior_try_outputs` (from `setup_input_data`) hard-links earlier tries'
  outputs into the current try's dir — necessary because
  `generate_dir_name_from_task_instance` stamps the try number into the path, so
  a retry otherwise starts in an empty directory. The successful commit then
  includes everything, and `clean_up(..., all_tries=True)` clears every try dir.

This covers retries within a dag run. It does **not** checkpoint mid-task: a
single try that never succeeds commits nothing, and a fresh dag run gets a new
`run_id` and therefore new dirs. Sharding a dataset across mapped tasks is the
next step if that becomes the binding constraint.

## LakeFS integration (via the `avalon` library)

When `ROGER_LAKEFS__CONFIG_ENABLED=true`, each task pulls inputs from a LakeFS repo/branch (`get_files()`), works in a task-specific local dir (named by `generate_dir_name_from_task_instance`), writes outputs back (`put_files()`), and commits via a temp branch merged after task success (`Merge(strategy="source-wins")`). Without LakeFS, tasks read/write a shared local data root.

`create_python_task()` wires the callbacks:

| flag | effect |
|---|---|
| `no_input_files=True` | skip the `pre_execute` download entirely (used by `wipe_es_indexes`) |
| `no_output_files=True` | `post_execute` runs `record_state_callback` (advances state only) instead of `avalon_commit_callback` (commits output) |
| `incremental_pull=False` | always download full inputs, even when the DAG run is incremental |
| `pass_conf` | whether the DAG run conf is forwarded into the callable |

Output is committed from **`post_execute`**, not `on_success_callback`.
Airflow runs `post_execute` inside `_execute_task`, before it records
`end_date` and releases downstream; success callbacks run later, in
`finalize()`. Committing there let downstream tasks read the branch before the
output landed — `BulkLoad` loaded an edgeless graph 105s early, and
`make_kgx` built KGX from annotations 4.8 hours stale, both green. Airflow
also only *logs* exceptions raised by state-change callbacks
(`_run_task_state_change_callbacks`), so a failed upload or merge left the
task successful; from `post_execute` it fails the task.

`on_failure_callback` and `on_skipped_callback` both run `clean_up` — the skip variant matters because `pre_execute` creates the input dir *before* it can raise `AirflowSkipException`.

## Dug data model and jsonpickle

Dug's data classes were extracted into a separate **`dug_data_model`** library: `DugElement` (`v2.base`), `DugConcept` (`v2.concept`), `DugVariable` (`v2.variable`), `DugStudy` (`v2.study`), `DugSection` (`v2.section`). `DugIdentifier` still lives in `dug.core.annotators._base`.

Intermediate artifacts (`elements.txt`, `concepts.txt`, `expanded_concepts.txt`) are **jsonpickle-encoded**, meaning they embed fully-qualified class paths like `"py/object": "dug_data_model.v2.concept.DugConcept"`.

**The trap:** when a stored class's module fails to import, jsonpickle does *not* raise — it silently returns the raw dict. The failure surfaces much later and much more confusingly, as `'dict' object has no attribute 'id'` inside ES indexing. The old `dug.core.parsers._base` module is exactly this case: it no longer imports at all (circular import via `dug.core.loaders.InputFile`).

This interacts badly with incremental ingestion: artifacts are only rewritten when their source changes, so they can sit in lakefs across multiple Dug upgrades, pinned to long-dead class paths.

**Do not fix this by re-annotating** — that is a month of compute. Use the migration:

```bash
lakectl local clone lakefs://<runtime-repo>/<branch>/ ./roger-out

# what's in there, and does any stored field lack a home in the current model?
docker run --rm -v $PWD:/w -w /w --entrypoint python \
  containers.renci.org/helxplatform/roger:<tag> \
  /w/scripts/migrate_pickled_classes.py --scan ./roger-out

# rewrite in place (note the --user flag; the image user does not own your files)
docker run --rm -v $PWD:/w -w /w --user $(id -u):$(id -g) --entrypoint python \
  containers.renci.org/helxplatform/roger:<tag> \
  /w/scripts/migrate_pickled_classes.py --fix ./roger-out

lakectl local commit ./roger-out -m "restamp pickled dug classes"
```

`--scan` prints each stored class as `ok`/`STALE`, then a field-drift table with the count of objects inspected per class. Two lines gate the migration:

- `!! no current class named: [...]` — a class was renamed, not just moved; needs an explicit mapping.
- `!! stored but not declared -> [...]` — a *field* was renamed or dropped; migrating would silently lose those values.

`--fix` aliases the dead modules, decodes, fills in fields added since (via `model_construct()` defaults, because `__setstate__` assigns `__dict__` wholesale and new fields would otherwise just be absent), and re-encodes with current class paths. It is idempotent and skips already-current files. `--self-check` round-trips a synthetic legacy payload with no lakefs data needed.

Repeat per dataset prefix. Any future Dug release that moves data classes needs the same pass.

## Configuration

`RogerConfig` loads `src/roger/config/config.yaml` (override file via `ROGER_CONFIG_FILE`), then applies env vars prefixed `ROGER_`. Dots in the config path map to `_`, and literal underscores in key names are escaped as `__`:

```bash
ROGER_REDISGRAPH_HOST=...             # redisgraph.host
ROGER_KGX_DATA__SETS=topmed:v1.0      # kgx.data_sets
ROGER_LAKEFS__CONFIG_ENABLED=true     # lakefs_config.enabled
ROGER_DUG__INPUTS_DATA__SETS=topmed:v2.0,anvil:v1.0   # which pipelines the DAGs build
```

`ROGER_DUG__INPUTS_DATA__SETS` is read directly by the DAG files as `name:version` pairs; the version becomes each pipeline class's `input_version`, i.e. the external lakefs ref (branch **or tag**) it pulls from.

Main sections: `redisgraph`, `kgx`, `dug_inputs`, `bulk_loader`, `annotation` (annotator type + normalizer/synonym service URLs), `indexing` (ES index names, TranQL queries, `element_mapping`), `elasticsearch`, `lakefs_config`, `validation` (test queries). `dev-config.yaml` and `test-config.yaml` sit alongside the default. `RogerConfig.to_dug_conf()` bridges Roger config to Dug.

## Bulk load CSV quirks

The FalkorDB bulk loader requires every column populated, so `bulkload.py` groups entities by which attributes have values — output files look like `data/bulk/nodes/<type>.csv-<group>-<hash>`. Values are cast per the inferred schema; the column separator is `0x1E` (configurable as `bulk_loader.separator`).

## Key External Dependencies

- **Dug** (helxplatform/dug, `DugModel2.0` branch) — annotation, indexing, concept expansion
- **dug_data_model** — the extracted Dug data classes (see the jsonpickle section)
- **avalon** (`lakefs-1.71.0` fork) — LakeFS client, wrapping `lakefs_sdk` 1.12
- **falkordb** + `falkordb-bulk-loader` — graph database (not the old redisgraph package)
- **bmt** — Biolink Model Tools (model version pinned in `kgx.biolink_model_version`)
- **apache-airflow 3.2.0**
- **jsonpickle** — unpinned; 4.x deprecation warnings about `keys` defaulting to True in 5.0 are expected noise

## Gotchas worth remembering

- `DugPipeline.search_obj` / `.index_obj` are lazily built. Any method that touches Elasticsearch first in a task must initialize them (`clear_index` does this) or you get `'NoneType' object has no attribute 'es'`.
- Dataset version refs are often **tags**. Never assume branch APIs work on them.
- Incremental state Variables have no compare-and-swap, so `annotate_and_index` and `index_only` both set `max_active_runs=1`.
- Task ids encode the group (`{name}_dataset_pipeline_task_group.annotate_{name}_files`), and lakefs output paths are built from those ids — renaming a task or group orphans its previous outputs and resets its incremental state.
- Pre-existing lint noise that is not worth "fixing" blind: `F401` unused imports in `dags/__init__.py` and `tasks.py`, `F824` unused `nonlocal` in `storage.py`.

## CI

GitHub Actions (`.github/workflows/`): `code-checks.yml` runs flake8 + pytest on Python 3.12 and a Docker build test; dev images push on `develop` branch; Trivy scans PRs. Default PR target branch is `develop`.
