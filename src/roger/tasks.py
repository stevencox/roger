# Tasks and methods related to Airflow implementations of Roger

import os
import json
from datetime import datetime
from functools import partial
from typing import Union
from pathlib import Path
import glob
import shutil

# Airflow 3.x - prefer provider imports and new public types
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.exceptions import AirflowSkipException
from airflow.sdk import TaskGroup
from airflow.models import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.providers.standard.operators.bash import BashOperator
from airflow.utils.context import Context  # type: ignore
try:
    # Task SDK Variable works on Airflow 3.x workers (no direct DB access)
    from airflow.sdk import Variable
except ImportError:
    from airflow.models import Variable

from roger.config import config, RogerConfig
from roger.logger import get_logger
from roger.pipelines.base import DugPipeline
from avalon.mainoperations import put_files, LakeFsWrapper, get_files
from lakefs_sdk.configuration import Configuration
from lakefs_sdk.models.merge import Merge
from lakefs_sdk.models.path_list import PathList
from lakefs_sdk.models.commit_creation import CommitCreation
from lakefs_sdk.exceptions import NotFoundException

logger = get_logger()

default_args = {
    'owner': 'RENCI',
    'start_date': datetime(2025, 1, 1)
}

# dotfile: storage.py readers glob '*.json' / '**/*.json' over pulled task
# outputs (e.g. kgx_objects) and glob skips dotfiles, so this never gets
# parsed as pipeline data
REMOVED_FILES_MANIFEST = ".removed_files.json"


def task_wrapper(python_callable, **kwargs):
    """
    Overrides configuration with config from airflow.
    :param python_callable:
    :param kwargs:
    :return:
    """
    # get dag config provided
    dag_run = kwargs.get('dag_run')
    pass_conf = kwargs.get('pass_conf', True)
    if config.lakefs_config.enabled:
        # get input path
        input_data_path = generate_dir_name_from_task_instance(
            kwargs['ti'],
            roger_config=config,
            suffix='input'
        )
        # get output path from task id run id dag id combo
        output_data_path = generate_dir_name_from_task_instance(
            kwargs['ti'],
            roger_config=config,
            suffix='output'
        )
    else:
        input_data_path, output_data_path = None, None
    # cast it to a path object
    func_args = {
        'input_data_path': input_data_path,
        'output_data_path': output_data_path,
        'to_string': kwargs.get('to_string')
    }
    logger.info(f"Task function args: {func_args}")
    # overrides values
    config.dag_run = dag_run
    # splat, so this works for both callable shapes: roger.core functions
    # (bulk_load, merge_nodes, ...) and execute_pipeline_method
    if pass_conf:
        return python_callable(**func_args, config=config)
    return python_callable(**func_args)


def get_executor_config(data_path='/opt/airflow/share/data'):
    """ Get an executor configuration.
    :param annotations: Annotations to attach to the executor.
    :returns: Returns a KubernetesExecutor if K8s configured, None otherwise.
    """
    env_var_prefix = config.OS_VAR_PREFIX
    # based on environment set on scheduler pod, make secrets for worker pod
    secrets_map = [{
        "secret_name_ref": "ELASTIC_SEARCH_PASSWORD_SECRET",
        "secret_key_ref": "ELASTIC_SEARCH_PASSWORD_SECRET_KEY",
        "env_var_name": f"{env_var_prefix}ELASTIC__SEARCH_PASSWORD"
    }, {
        "secret_name_ref": "REDIS_PASSWORD_SECRET",
        "secret_key_ref": "REDIS_PASSWORD_SECRET_KEY",
        "env_var_name": f"{env_var_prefix}REDISGRAPH_PASSWORD"
    }]
    secrets = []
    for secret in secrets_map:
        secret_name = os.environ.get(secret["secret_name_ref"], False)
        secret_key_name = os.environ.get(secret["secret_key_ref"], False)
        if secret_name and secret_key_name:
            secrets.append({
                "name": secret["env_var_name"],
                "valueFrom": {
                    "secretKeyRef": {
                        "name": secret_name,
                        "key": secret_key_name
                    }
                }})

    k8s_executor_config = {
        "KubernetesExecutor": {
            "envs": secrets,
        }
    }
    return k8s_executor_config


def memory_override(limit: str, request: str = None) -> dict:
    """executor_config bumping only this task's memory.

    Everything else (image, volumes, env, service account) is inherited from
    the chart's worker pod template; this patches the 'base' container so one
    heavy task does not force the default up for every task. Keep request
    well under limit: the namespace quota counts requests.memory and
    limits.memory separately.
    """
    from kubernetes.client import models as k8s
    return {"pod_override": k8s.V1Pod(spec=k8s.V1PodSpec(containers=[
        k8s.V1Container(
            name="base",
            resources=k8s.V1ResourceRequirements(
                requests={"memory": request or "1Gi"},
                limits={"memory": limit}))]))}


def init_lakefs_client(config: RogerConfig) -> LakeFsWrapper:
    configuration = Configuration()
    configuration.username = config.lakefs_config.access_key_id
    configuration.password = config.lakefs_config.secret_access_key
    configuration.host = config.lakefs_config.host
    the_lake = LakeFsWrapper(configuration=configuration)
    return the_lake


def pagination_helper(page_fetcher, **kwargs):
    """Helper function to iterate over paginated results"""
    while True:
        resp = page_fetcher(**kwargs)
        yield from resp.results
        if not resp.pagination.has_more:
            break
        kwargs['after'] = resp.pagination.next_offset


def incremental_state_key(dag_id: str, task_id: str, repo: str,
                          branch: str) -> str:
    """Airflow Variable key holding the last source commit consumed by a
    task. task_id is the group-qualified id, unique within a dag."""
    return f"roger_incr::{dag_id}::{task_id}::{repo}@{branch}"


def get_state_file_path(task_instance: TaskInstance) -> Union[str, None]:
    path = generate_dir_name_from_task_instance(
        task_instance, roger_config=config, suffix='state')
    return str(path) if path else None


def read_state_file(task_instance: TaskInstance) -> dict:
    path = get_state_file_path(task_instance)
    if path and os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {}


def write_state_file(task_instance: TaskInstance, state: dict):
    path = get_state_file_path(task_instance)
    if not path:
        return
    with open(path, 'w') as f:
        json.dump(state, f)


def resolve_ref_tip(client: LakeFsWrapper, repo: str, ref: str) -> str:
    """Resolve any ref (branch, tag or commit id) to a commit id.

    Tags are tried first. lakefs validates log_commits' ref argument as a
    *branch id*, so a tag whose name is not a legal branch name -- the
    dotted versions this pipeline uses, e.g. kgx.data_sets
    'baseline-graph:v7.0' -- is rejected with a 400 before the tag is ever
    looked up. branches_api.get_branch has the same problem, which is why
    neither API alone is enough.
    """
    try:
        return client._client.tags_api.get_tag(repository=repo, tag=ref).commit_id
    except NotFoundException:
        pass  # not a tag; a branch or commit id then
    results = client._client.refs_api.log_commits(
        repository=repo, ref=ref, amount=1).results
    return results[0].id if results else ref


def get_changed_files(client: LakeFsWrapper, repo: str, from_ref: str,
                      to_ref: str, prefixes=None) -> dict:
    """Diff two refs, returning paths bucketed as added/changed/removed.

    Unlike avalon's get_changes this keeps 'removed' entries and filters by
    path prefixes. Prefixes are normalized with a trailing '/' so that
    'a/task' does not match 'a/task_b/...'; '*' or empty means no filter.
    """
    changes = {'added': [], 'changed': [], 'removed': []}
    if not prefixes or '*' in prefixes:
        norm = None
    else:
        norm = tuple(p if p.endswith('/') else p + '/' for p in prefixes)
    for diff in pagination_helper(client._client.refs_api.diff_refs,
                                  repository=repo, left_ref=from_ref,
                                  right_ref=to_ref):
        if norm and not diff.path.startswith(norm):
            continue
        if diff.type in changes:
            changes[diff.type].append(diff.path)
    return changes


def find_sibling_files(client: LakeFsWrapper, repo: str, ref: str,
                       downloaded, marker="GapExchange_") -> list:
    """dbGaP data dicts need a sibling GapExchange_<dir> file in the same
    lakefs directory for study name/description. Incremental diffs only
    carry the changed data dicts, so list each affected dir and pull any
    marker file not already downloaded."""
    extra = set()
    seen_dirs = set()
    for path in downloaded:
        d = path.rsplit('/', 1)[0] if '/' in path else ''
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        list_prefix = d + '/' if d else ''
        for obj in pagination_helper(
                client._client.objects_api.list_objects,
                repository=repo, ref=ref, prefix=list_prefix,
                delimiter='/', amount=1000):
            name = obj.path.rsplit('/', 1)[-1]
            if name.startswith(marker) and obj.path not in downloaded:
                extra.add(obj.path)
    return sorted(extra)


def removed_bases(removed: dict, dag_id: str, upstream_ids) -> set:
    """Map removed source paths to the dataset base names their derived
    outputs are keyed by.

    External-repo sources use annotate's convention (filename minus last
    extension); roger-repo sources use the first path segment under the
    upstream task dir (e.g. {dag}/{task}/<base>/elements.txt -> <base>).
    """
    bases = set()
    roger_repo = config.lakefs_config.repo
    for src_repo, paths in removed.items():
        for p in paths:
            if src_repo == roger_repo:
                rel = p
                for uid in upstream_ids:
                    prefix = f"{dag_id}/{uid}/"
                    if p.startswith(prefix):
                        rel = p[len(prefix):]
                        break
                base = rel.split('/')[0]
                if base == rel:
                    # top-level file, not a dataset dir
                    base = '.'.join(rel.split('.')[:-1])
            else:
                base = '.'.join(os.path.basename(p).split('.')[:-1])
            if base and not base.startswith('.'):
                bases.add(base)
    return bases


def orphaned_output_paths(existing, remote_path: str, local_path: str) -> list:
    """Remote objects under this task's prefix that the local output dir no
    longer holds.

    The bulk-load CSV names encode data-dependent counters
    ({type}.csv-{group}-{flush}), so every run writes new names and put_files
    never overwrites the previous ones. Left alone they pile up and the
    loader sees the same node id in files from several runs.
    """
    local = set()
    for root, _, files in os.walk(local_path):
        for name in files:
            local.add(os.path.relpath(os.path.join(root, name), local_path))
    orphans = []
    for f in existing:
        rel = f[len(remote_path):] if f.startswith(remote_path) else f
        if rel not in local:
            orphans.append(f)
    return orphans


def delete_objects(client: LakeFsWrapper, repo: str, branch: str,
                   paths: list, message: str):
    "Delete paths on branch and commit. Chunked; lakefs caps the path list."
    for i in range(0, len(paths), 1000):
        client._client.objects_api.delete_objects(
            repository=repo, branch=branch,
            path_list=PathList(paths=paths[i:i + 1000]))
    client._client.commits_api.commit(
        repository=repo, branch=branch,
        commit_creation=CommitCreation(message=message))


def stale_output_paths(existing, remote_path: str, bases: set) -> list:
    """Pick output objects derived from removed sources: anything under
    <base>/ or the <base>_kgx.json flat file make_kg_tagged emits."""
    stale = []
    for f in existing:
        rel = f[len(remote_path):] if f.startswith(remote_path) else f
        for b in bases:
            if rel.startswith(b + '/') or rel == f"{b}_kgx.json":
                stale.append(f)
                break
    return stale


def _get_last_consumed(key: str) -> Union[str, None]:
    try:
        return Variable.get(key, default=None)
    except TypeError:
        try:
            return Variable.get(key, default_var=None)
        except Exception:
            return None
    except Exception:
        return None


def _advance_state_variables(state: dict):
    for key, entry in state.get('entries', {}).items():
        Variable.set(key, entry['commit_id'])
        logger.info("Recorded last ingested commit %s for %s",
                    entry['commit_id'], key)


def _merge_had_no_changes(exc):
    """True when lakefs rejected a merge because there was nothing to apply.

    lakefs answers an empty merge with 400 `update branch <b>: no changes`.
    That is what a task produces when its output already matches the branch,
    which is normal for deterministic work over unchanged input -- not a
    failure, and it must not fail the task.
    """
    return (getattr(exc, "status", None) == 400
            and "no changes" in str(exc))


def avalon_commit_callback(context: Context, **kwargs):
    client: LakeFsWrapper = init_lakefs_client(config=config)
    state = read_state_file(context['ti'])
    # now files have been processed,
    # this part should
    # get the out path of the task
    local_path = str(generate_dir_name_from_task_instance(
        context['ti'],
        roger_config=config,
        suffix='output')).rstrip('/') + '/'
    task_id = context['ti'].task_id
    dag_id = context['ti'].dag_id
    run_id = context['ti'].run_id
    # normalize run/dag/task ids for branch name
    run_id_normalized = run_id.replace('-', '_').replace(':', '_').replace('+', '_').replace('.', '_')
    dag_id_normalized = dag_id.replace('-', '_').replace(':', '_').replace('+', '_').replace('.', '_')
    task_id_normalized = task_id.replace('-', '_').replace(':', '_').replace('+', '_').replace('.', '_')
    temp_branch_name = f'{dag_id_normalized}_{task_id_normalized}_{run_id_normalized}'
    remote_path = f'{dag_id}/{task_id}/'

    branch = config.lakefs_config.branch
    repo = config.lakefs_config.repo

    # record source-data removals alongside outputs; rewritten every run so
    # the committed manifest always reflects the latest diff window. Also
    # guarantees put_files has at least one file on removal-only runs.
    if state:
        os.makedirs(local_path, exist_ok=True)
        with open(local_path + REMOVED_FILES_MANIFEST, 'w') as f:
            json.dump(state.get('removed', {}), f, indent=2)

    # real source commit(s) consumed by this task, recorded by
    # setup_input_data; falls back to branch name for runs without state
    # (e.g. manual repository_id overrides)
    consumed = ",".join(sorted(
        {e['commit_id'] for e in state.get('entries', {}).values()}))

    logger.info("Pushing local path %s to %s@%s in %s dir",
                local_path, repo, temp_branch_name, remote_path)
    put_files(
        local_path=local_path,
        remote_path=remote_path,
        task_name=task_id,
        task_args=[""],
        pipeline_id=dag_id,
        task_docker_image="docker-image",
        s3storage=False,
        lake_fs_client=client,
        branch=temp_branch_name,
        repo=repo,
        commit_id=consumed or branch,
        source_branch_name=branch
    )

    # tasks whose output filenames shift between runs must mirror the local
    # dir, not accumulate; otherwise consumers read several runs at once
    if kwargs.get('clear_output_prefix'):
        existing = client.get_filelist(repository=repo,
                                       branch=temp_branch_name,
                                       remote_path=remote_path)
        orphans = orphaned_output_paths(existing, remote_path, local_path)
        if orphans:
            logger.info("Deleting %d output(s) from previous runs under %s",
                        len(orphans), remote_path)
            delete_objects(client, repo, temp_branch_name, orphans,
                           f"drop superseded {task_id} outputs")

    # drop derived outputs whose source files were deleted upstream; done on
    # the temp branch so the removal merges atomically with this run's
    # outputs and propagates to downstream tasks via their input diffs
    if state.get('removed'):
        bases = removed_bases(state['removed'], dag_id,
                              context['ti'].task.upstream_task_ids)
        existing = client.get_filelist(repository=repo,
                                       branch=temp_branch_name,
                                       remote_path=remote_path)
        stale = stale_output_paths(existing, remote_path, bases)
        if stale:
            logger.info("Deleting %d stale outputs for removed sources: %s",
                        len(stale), stale)
            delete_objects(client, repo, temp_branch_name, stale,
                           f"remove stale {task_id} outputs "
                           f"for deleted sources")

    for diff in pagination_helper(client._client.refs_api.diff_refs,
                                  repository=repo, left_ref=branch,
                                  right_ref=temp_branch_name):
        logger.info("Diff: " + str(diff))

    try:
        merge = Merge(**{"strategy": "source-wins"})
        client._client.refs_api.merge_into_branch(repository=repo,
                                                  source_ref=temp_branch_name,
                                                  destination_branch=branch,
                                                  merge=merge
                                                  )

        logger.info(f"merged branch {temp_branch_name} into {branch}")
        # only advance incremental state once outputs are safely merged; a
        # failed merge leaves the Variables untouched so the next run
        # re-processes the same commit window (idempotent)
        _advance_state_variables(state)
    except Exception as e:
        if _merge_had_no_changes(e):
            # lakefs 400s an empty merge. It means the output we just
            # produced is byte-identical to what is already on the branch,
            # which is a correct outcome, not a failure -- deterministic
            # annotation over unchanged input lands here every time. State
            # still advances: the input was consumed and the branch holds
            # the right content.
            logger.info("Nothing to merge from %s into %s; branch already "
                        "matches this output", temp_branch_name, branch)
            _advance_state_variables(state)
        else:
            # never swallow anything else: the clean_up below deletes the
            # local output, so a logged-and-ignored merge failure destroyed
            # the work and still reported success. Raising from post_execute
            # fails the task, which keeps the output (on_failure_callback
            # passes keep_output=True) so the retry resumes from it.
            logger.error(e)
            raise
    finally:
        client._client.branches_api.delete_branch(
            repository=repo,
            branch=temp_branch_name
        )

        logger.info(f"deleted temp branch {temp_branch_name}")
        logger.info(f"deleting local dir {local_path}")

    # cleanup local dirs, including any left by earlier tries whose outputs
    # were hard-linked into this one and are now committed
    clean_up(context, all_tries=True, **kwargs)


def record_state_callback(context: Context, **kwargs):
    """Success callback for tasks with no lakefs output: advance the
    incremental state Variables and clean local dirs."""
    state = read_state_file(context['ti'])
    _advance_state_variables(state)
    if state.get('removed'):
        logger.warning("Upstream removals not propagated to indexes: %s",
                       state['removed'])
    clean_up(context, all_tries=True, **kwargs)


def try_dir_pattern(task_instance: TaskInstance, suffix: str):
    """Glob matching this task's dir for every try of the current dag run.

    generate_dir_name_from_task_instance stamps the try number into the path,
    so a retry gets a fresh directory and cannot see what the previous try
    produced. This is how we find the previous tries.
    """
    root_data_dir = os.getenv("ROGER_DATA_DIR", "").rstrip('/')
    return (f"{root_data_dir}/{task_instance.dag_id}_{task_instance.task_id}"
            f"_{task_instance.run_id}_*_{suffix}")


def reuse_prior_try_outputs(task_instance: TaskInstance):
    """Hard-link outputs from earlier tries of this task into the current one.

    Annotation is the expensive step -- tens of seconds per input file, weeks
    for a large dbGaP study -- and its output is only committed to lakefs when
    the whole task succeeds. So a task that died at file 40,000 of 61,597 used
    to discard all 40,000 finished files, and the retry began again at zero.

    Making the finished work visible in the current try's output dir means the
    pipeline's own skip check (DugPipeline.annotation_is_complete) passes over
    it, and the eventual successful commit includes it. Hard links keep this
    free in both time and disk; a copy is the fallback for filesystems that
    refuse them (nothing in-cluster does, but the local dev path is a bind
    mount).

    Returns the number of files made available.
    """
    current = str(generate_dir_name_from_task_instance(
        task_instance, roger_config=config, suffix='output'))
    if not current:
        return 0
    reused = 0
    for prior in sorted(glob.glob(try_dir_pattern(task_instance, 'output'))):
        if os.path.abspath(prior) == os.path.abspath(current):
            continue
        for src in glob.glob(prior.rstrip('/') + '/**', recursive=True):
            if not os.path.isfile(src):
                continue
            dest = os.path.join(current,
                                os.path.relpath(src, prior))
            if os.path.exists(dest):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                os.link(src, dest)
            except OSError:
                shutil.copy2(src, dest)
            reused += 1
    if reused:
        logger.info("Reused %d output file(s) from earlier tries of %s",
                    reused, task_instance.task_id)
    return reused


def clean_up(context: Context, keep_output=False, all_tries=False, **kwargs):
    """Remove this task's local input and output dirs.

    :param keep_output: leave the output dir in place. Used on failure, so a
        retry can pick up the work already done (see
        reuse_prior_try_outputs); the successful commit cleans it up.
    :param all_tries: also remove the dirs left behind by earlier tries of
        this task, whose contents have by then been hard-linked into this
        try's output dir and committed.
    """
    task_instance = context['ti']
    input_dir = str(generate_dir_name_from_task_instance(
        task_instance, roger_config=config, suffix='input')).rstrip('/') + '/'
    output_dir = str(generate_dir_name_from_task_instance(
        task_instance, roger_config=config, suffix='output')).rstrip('/') + '/'

    dirs_to_clean = [input_dir]
    if all_tries:
        dirs_to_clean += glob.glob(try_dir_pattern(task_instance, 'input'))
    if not keep_output:
        dirs_to_clean.append(output_dir)
        if all_tries:
            dirs_to_clean += glob.glob(try_dir_pattern(task_instance,
                                                       'output'))
    else:
        logger.info("Keeping %s so a retry can resume from it", output_dir)

    files_to_clean = []
    for a_dir in dict.fromkeys(dirs_to_clean):
        files_to_clean += glob.glob(a_dir.rstrip('/') + '/**', recursive=True)
        files_to_clean.append(a_dir)
    for f in files_to_clean:
        if os.path.exists(f):
            shutil.rmtree(f, ignore_errors=True)
    state_file = get_state_file_path(task_instance)
    if state_file and os.path.isfile(state_file):
        os.remove(state_file)


def generate_dir_name_from_task_instance(task_instance: TaskInstance,
                                         roger_config: RogerConfig, suffix: str):
    # if lakefs is not enabled just return none so methods default to using
    # local dir structure.
    if not roger_config.lakefs_config.enabled:
        return None
    root_data_dir = os.getenv("ROGER_DATA_DIR").rstrip('/')
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    run_id = task_instance.run_id
    try_number = task_instance.try_number
    return Path(
        f"{root_data_dir}/{dag_id}_{task_id}_{run_id}_{try_number}_{suffix}")


def setup_input_data(context: Context, exec_conf):
    logger.info("""
        - Figures out the task name and id,
        - find its data dependencies
        - clean up and create in and out dir
        - put dependency data in input dir
        - if for some reason data was not found raise an exception
          """)
    logger.info(">>> context")
    logger.info(context)

    task_instance: TaskInstance = context['ti']
    input_dir = str(generate_dir_name_from_task_instance(
        task_instance, roger_config=config, suffix="input"))
    os.makedirs(input_dir, exist_ok=True)

    # a retry starts in a fresh try dir; carry forward whatever earlier tries
    # of this same task already finished so it resumes instead of restarting
    reuse_prior_try_outputs(task_instance)

    client = init_lakefs_client(config=config)
    repos = exec_conf.get('repos', [])
    dag_params = context.get("params", {})
    dag_id = task_instance.dag_id
    task_id = task_instance.task_id

    if dag_params.get("repository_id"):
        logger.info(">>> repository_id supplied. Overriding repo.")
        repos = [{
            'repo': dag_params.get("repository_id"),
            'branch': dag_params.get("branch_name"),
            'commitid_from': dag_params.get("commitid_from"),
            'commitid_to': dag_params.get("commitid_to")
        }]

    if not repos or len(repos) == 0:
        branch = config.lakefs_config.branch
        repo = config.lakefs_config.repo
        upstream_ids = task_instance.task.upstream_task_ids
        repos = [{
            'repo': repo,
            'branch': branch,
            'path': f'{dag_id}/{upstream_id}',
            'commitid_from': None,
            'commitid_to': None
        } for upstream_id in upstream_ids]

    for r in repos:
        if not r.get('path'):
            r['path'] = '*'
        if not os.path.exists(input_dir + f'/{r["repo"]}'):
            os.mkdir(input_dir + f'/{r["repo"]}')
    logger.info(f"repos : {repos}")

    logger.info(">>> start of downloading data")
    if dag_params.get("repository_id"):
        # manual override: honor the explicit repo/branch/commit range,
        # bypassing incremental state entirely
        for r in repos:
            logger.info("downloading %s from %s@%s to %s",
                        r['path'], r['repo'], r['branch'], input_dir)
            get_files(
                local_path=input_dir + f'/{r["repo"]}',
                remote_path=r['path'],
                branch=r['branch'],
                repo=r['repo'],
                changes_only=r.get("commitid_from") is not None,
                changes_from=r.get("commitid_from"),
                changes_to=r.get("commitid_to"),
                lake_fs_client=client
            )
        logger.info(">>> end of downloading data")
        return

    incremental = (bool(dag_params.get("incremental"))
                   and exec_conf.get('incremental_pull', True))
    # one tip resolution / state key / diff per source ref, even when a task
    # pulls several upstream paths from the same repo+branch
    groups = {}
    for r in repos:
        groups.setdefault((r['repo'], r['branch']), []).append(r['path'])

    state = {'entries': {}, 'removed': {}}
    any_change = False
    for (repo, branch), prefixes in groups.items():
        local_path = input_dir + f'/{repo}'
        tip = resolve_ref_tip(client, repo, branch)
        key = incremental_state_key(dag_id, task_id, repo, branch)
        last = _get_last_consumed(key) if incremental else None
        changes = None
        if last and last == tip:
            logger.info("No new commits on %s@%s since %s", repo, branch, tip)
        elif last:
            try:
                changes = get_changed_files(client, repo, last, tip, prefixes)
            except NotFoundException:
                logger.warning(
                    "Commit %s not found on %s; falling back to full "
                    "download", last, repo)
                last = None
        if last and changes is not None:
            to_download = changes['added'] + changes['changed']
            logger.info("Incremental %s@%s %s..%s: %d added, %d changed, "
                        "%d removed", repo, branch, last, tip,
                        len(changes['added']), len(changes['changed']),
                        len(changes['removed']))
            if to_download:
                siblings = find_sibling_files(client, repo, tip, to_download)
                if siblings:
                    logger.info("Adding %d sibling file(s): %s",
                                len(siblings), siblings)
                    to_download = to_download + siblings
                client.download_files(
                    remote_files=to_download,
                    local_path=local_path,
                    repository=repo,
                    branch_or_commit_id=tip)
            if changes['removed']:
                state['removed'].setdefault(
                    repo, []).extend(changes['removed'])
            if to_download or changes['removed']:
                any_change = True
        elif not last:
            # first run, incremental disabled, or unreachable last commit:
            # full download pinned to the resolved tip
            for prefix in prefixes:
                logger.info("downloading %s from %s@%s to %s",
                            prefix, repo, tip, input_dir)
                get_files(
                    local_path=local_path,
                    remote_path=prefix,
                    branch=tip,
                    repo=repo,
                    changes_only=False,
                    lake_fs_client=client
                )
            any_change = True
        state['entries'][key] = {
            'repo': repo, 'branch': branch, 'commit_id': tip}
    logger.info(">>> end of downloading data")

    if incremental and not any_change:
        raise AirflowSkipException(
            "No changes in source refs since last successful run")
    write_state_file(task_instance, state)


def create_python_task(dag, name, a_callable, func_kwargs=None,
                       external_repos=None, pass_conf=True,
                       no_output_files=False, no_input_files=False,
                       incremental_pull=True, clear_output_prefix=False,
                       memory=None, resumable=False):
    """ Create a python task.
    :param func_kwargs: additional arguments for callable.
    :param dag: dag to add task to.
    :param name: The name of the task.
    :param a_callable: The code to run in this task.
    :param no_input_files: skip the lakefs input download entirely.
    :param resumable: keep the output dir when the task fails, so a retry
        can pick up where it left off. Only true for annotate, which is
        the one task with a skip check (annotation_is_complete). For the
        others the retained output is never reused and is pure disk cost:
        three failed crawls held 47GB and filled the shared volume, which
        is what made them fail in the first place.
    :param incremental_pull: when False the task always downloads its full
        inputs even if the dag runs with incremental=True (needed for tasks
        that rebuild state from scratch, e.g. ES indexing after a wipe).
    :param clear_output_prefix: mirror the local output dir into lakefs,
        deleting objects from previous runs. Needed when output filenames
        vary run to run (the bulk-load CSVs) and would otherwise accumulate.
    :param memory: memory limit for this task's pod, e.g. '15Gi'. Omit to
        take the chart's worker default.
    """

    if external_repos is None:
        external_repos = {}

    # these are actual arguments passed down to the task function
    op_kwargs = {
        "python_callable": a_callable,
        "to_string": True,
        "pass_conf": pass_conf
    }
    if func_kwargs is None:
        func_kwargs = {}
    op_kwargs.update(func_kwargs)

    python_operator_args = {
        "task_id": name,
        "python_callable": task_wrapper,
        # executor_config example left commented; fill if needed
        "dag": dag,
    }
    if memory:
        python_operator_args["executor_config"] = memory_override(memory)

    if config.lakefs_config.enabled:
        pre_exec_conf = {
            'repos': [],
            'incremental_pull': incremental_pull
        }
        if external_repos:
            pre_exec_conf['repos'] = [{
                'repo': r['name'],
                'branch': r['branch'],
                'path': r.get('path', '*')
            } for r in external_repos]

        if not no_input_files:
            pre_exec = partial(setup_input_data, exec_conf=pre_exec_conf)
            # pre_execute will be called with context -> partial keeps exec_conf fixed
            python_operator_args['pre_execute'] = pre_exec

        # pass fixed kwargs into partials so resulting callback accepts (context,)
        # keep the output dir on failure: the next try hard-links it in and
        # skips the work already done (annotation is the expensive step)
        python_operator_args['on_failure_callback'] = partial(
            clean_up, keep_output=resumable, **op_kwargs)
        # pre_execute creates the input dir before it can raise
        # AirflowSkipException; clean it up on skip too
        python_operator_args['on_skipped_callback'] = partial(clean_up, **op_kwargs)
        # post_execute, not on_success_callback. Airflow runs post_execute
        # inside _execute_task, before it records end_date and releases
        # downstream; success callbacks run in finalize(), after. Committing
        # there meant downstream tasks read the branch before the output
        # landed -- BulkLoad loaded an edgeless graph 105s early, and
        # make_kgx built kgx from annotations 4.8h stale. Airflow also
        # swallows exceptions from state-change callbacks (it only logs
        # them), so a failed upload or merge used to leave the task green;
        # from post_execute it fails the task instead.
        if not no_output_files:
            commit = partial(avalon_commit_callback,
                             clear_output_prefix=clear_output_prefix,
                             **op_kwargs)
        else:
            commit = partial(record_state_callback, **op_kwargs)
        # the hook is called as (context, result); our callbacks take context
        python_operator_args['post_execute'] = (
            lambda context, result=None, _c=commit: _c(context))

    python_operator_args["op_kwargs"] = op_kwargs

    return PythonOperator(**python_operator_args)

def execute_pipeline_method(pipeline_class, configparam, method_name,
                            input_data_path=None, output_data_path=None,
                            to_string=False, **pipeline_kwargs):
    """
    Lazy execution wrapper.
    Initializes the heavy pipeline class and executes the method ONLY inside the K8s worker pod.
    """
    logger.info(f"Initializing {pipeline_class.__name__} for method {method_name}")

    # 1. The class initialization happens safely here, ignored by the Scheduler
    with pipeline_class(config=configparam, **pipeline_kwargs) as pipeline:

        # 2. Grab the requested method (e.g., pipeline.annotate)
        method_to_call = getattr(pipeline, method_name)

        # 3. Run it with the Airflow context args
        return method_to_call(input_data_path=input_data_path,
                              output_data_path=output_data_path,
                              to_string=to_string)



def file_task_group_id(name):
    return f"{name}_dataset_pipeline_task_group"


def create_pipeline_taskgroup(
        dag,
        pipeline_class: type,
        configparam: RogerConfig,
        **kwargs):
    """Emit the file-based (lakefs-committed, incremental) task group for
    the specified pipeline_class: annotate -> crawl, make_kgx.

    ES indexing/validation lives in create_es_taskgroup and runs after a
    global index wipe, rebuilding elastic from the files left in lakefs."""
    name = pipeline_class.pipeline_name
    input_dataset_version = pipeline_class.input_version

    with TaskGroup(group_id=file_task_group_id(name)) as tg:

        # --- 1. Annotate Task ---
        annotate_callable = partial(
            execute_pipeline_method,
            pipeline_class=pipeline_class,
            configparam=configparam,
            method_name='annotate',
            **kwargs
        )
        annotate_task = create_python_task(
            dag,
            f"annotate_{name}_files",
            annotate_callable,
            external_repos=[{
                'name': getattr(pipeline_class, 'pipeline_name'),
                'branch': input_dataset_version
            }],
            # annotate_workers threads each hold a whole parsed file; the
            # chart default was sized for the serial annotator
            memory=configparam.annotation.annotate_memory,
            # the only task that can resume: annotation_is_complete skips
            # input files whose output already exists
            resumable=True,
            pass_conf=False)

        # --- 2. Make KGX Task ---
        make_kgx_callable = partial(
            execute_pipeline_method,
            pipeline_class=pipeline_class,
            configparam=configparam,
            method_name='make_kg_tagged',
            **kwargs
        )
        make_kgx_task = create_python_task(
            dag,
            f"make_kgx_{name}",
            make_kgx_callable,
            # holds every element of the dataset in memory to build the kgx;
            # OOMKilled at the 2Gi chart default on bdc-recover
            memory=configparam.annotation.annotate_memory,
            pass_conf=False)
        make_kgx_task.set_upstream(annotate_task)

        # --- 3. Crawl Task ---
        crawl_callable = partial(
            execute_pipeline_method,
            pipeline_class=pipeline_class,
            configparam=configparam,
            method_name='crawl_tranql',
            **kwargs
        )
        crawl_task = create_python_task(
            dag,
            f"crawl_{name}",
            crawl_callable,
            # expands every concept through tranql, accumulating answers
            memory=configparam.annotation.annotate_memory,
            pass_conf=False)
        crawl_task.set_upstream(annotate_task)

        # --- 4. Complete Task ---
        # none_failed: a group skipped for "no new data" still completes
        # green; genuine failures still propagate as upstream_failed
        complete_task = EmptyOperator(task_id=f"complete_{name}",
                                      trigger_rule="none_failed")
        complete_task.set_upstream((make_kgx_task, crawl_task))

    return tg


def create_es_wipe_task(dag, pipeline_class: type, configparam: RogerConfig,
                        **kwargs):
    """Single task that wipes all ES indexes before the per-dataset rebuild
    tasks repopulate them from lakefs. Any pipeline class works: index names
    come from shared config."""
    wipe_callable = partial(
        execute_pipeline_method,
        pipeline_class=pipeline_class,
        configparam=configparam,
        method_name='clear_all_es_indexes',
        **kwargs
    )
    return create_python_task(
        dag,
        "wipe_es_indexes",
        wipe_callable,
        pass_conf=False,
        no_output_files=True,
        no_input_files=True)


def create_es_taskgroup(
        dag,
        pipeline_class: type,
        configparam: RogerConfig,
        **kwargs):
    """Emit the elastic task group for a pipeline: full (non-incremental)
    pulls of this run's file outputs from lakefs, indexed into the freshly
    wiped indexes so ES always mirrors what lakefs holds."""
    name = pipeline_class.pipeline_name
    repo = config.lakefs_config.repo
    branch = config.lakefs_config.branch
    file_group = file_task_group_id(name)
    # Everything ES needs lives in the crawl output: expanded_concepts.txt
    # AND an elements.txt whose optional_terms carry the KG-derived search
    # terms (crawl_tranql rewrites it after expanding concepts). The
    # annotate copy has empty optional_terms, so indexing that one makes
    # validate_indexed_concepts unsatisfiable -- it searches by KG node
    # name. storage.dug_expanded_elements_objects globs "**/elements.txt"
    # and cannot tell the two apart, so only the crawl prefix is pulled.
    crawl_path = f"{dag.dag_id}/{file_group}.crawl_{name}"

    def full_pull(*paths):
        return {
            'external_repos': [
                {'name': repo, 'branch': branch, 'path': p} for p in paths],
            'pass_conf': False,
            'no_output_files': True,
            'incremental_pull': False,
        }

    with TaskGroup(group_id=f"{name}_es_index_task_group") as tg:

        index_variables_task = create_python_task(
            dag,
            f"index_{name}_variables",
            partial(execute_pipeline_method,
                    pipeline_class=pipeline_class,
                    configparam=configparam,
                    method_name='index_variables',
                    **kwargs),
            **full_pull(crawl_path))

        validate_index_variables_task = create_python_task(
            dag,
            f"validate_{name}_index_variables",
            partial(execute_pipeline_method,
                    pipeline_class=pipeline_class,
                    configparam=configparam,
                    method_name='validate_indexed_variables',
                    **kwargs),
            **full_pull(crawl_path))
        validate_index_variables_task.set_upstream(index_variables_task)

        index_concepts_task = create_python_task(
            dag,
            f"index_{name}_concepts",
            partial(execute_pipeline_method,
                    pipeline_class=pipeline_class,
                    configparam=configparam,
                    method_name='index_concepts',
                    **kwargs),
            **full_pull(crawl_path))

        validate_index_concepts_task = create_python_task(
            dag,
            f"validate_{name}_index_concepts",
            partial(execute_pipeline_method,
                    pipeline_class=pipeline_class,
                    configparam=configparam,
                    method_name='validate_indexed_concepts',
                    **kwargs),
            **full_pull(crawl_path))
        validate_index_concepts_task.set_upstream(index_concepts_task)
        # it asserts variables are findable by KG-derived terms, so it
        # searches the variables index -- which must be fully populated
        # first, not just the concepts index
        validate_index_concepts_task.set_upstream(index_variables_task)

    return tg


# ponytail: prefixes string-coupled to create_pipeline_taskgroup's group/task
# naming; breaks only if annotate_and_index renames its taskgroup/tasks.
ANNOTATE_DAG_ID = "annotate_and_index"


def _annotate_index_source_path(name: str, task: str) -> str:
    """Runtime-repo prefix where annotate_and_index committed a task's output:
    {dag_id}/{group_id}.{task_id}/"""
    group = f"{name}_dataset_pipeline_task_group"
    return f"{ANNOTATE_DAG_ID}/{group}.{task}"


def create_index_only_taskgroup(
        dag,
        pipeline_class: type,
        configparam: RogerConfig,
        **kwargs):
    """Re-index ES from annotate_and_index outputs already present in the
    runtime repo (e.g. after merging dev->prod). Pulls annotate/crawl outputs
    by explicit path from the configured runtime repo+branch; no annotate or
    crawl is re-run."""
    name = pipeline_class.pipeline_name
    repo = configparam.lakefs_config.repo
    branch = configparam.lakefs_config.branch

    def index_task(task_name, method_name, source_tasks):
        callable_ = partial(
            execute_pipeline_method,
            pipeline_class=pipeline_class,
            configparam=configparam,
            method_name=method_name,
            **kwargs)
        return create_python_task(
            dag, task_name, callable_,
            external_repos=[{
                'name': repo,
                'branch': branch,
                'path': _annotate_index_source_path(name, src),
            } for src in source_tasks],
            pass_conf=False,
            no_output_files=True)

    with TaskGroup(group_id=f"{name}_index_only_task_group") as tg:
        # all four read crawl output; see create_es_taskgroup for why
        crawl_src = f"crawl_{name}"

        index_variables_task = index_task(
            f"index_{name}_variables", 'index_variables', [crawl_src])
        validate_variables_task = index_task(
            f"validate_{name}_index_variables",
            'validate_indexed_variables', [crawl_src])
        validate_variables_task.set_upstream(index_variables_task)

        index_concepts_task = index_task(
            f"index_{name}_concepts", 'index_concepts', [crawl_src])
        validate_concepts_task = index_task(
            f"validate_{name}_index_concepts",
            'validate_indexed_concepts', [crawl_src])
        validate_concepts_task.set_upstream(index_concepts_task)
        # searches the variables index too; see create_es_taskgroup
        validate_concepts_task.set_upstream(index_variables_task)

        complete_task = EmptyOperator(task_id=f"complete_{name}",
                                      trigger_rule="none_failed")
        complete_task.set_upstream(
            (validate_variables_task, validate_concepts_task))

    return tg
