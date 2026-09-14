"""Unit tests for incremental (delta) lakefs ingestion in roger.tasks.

These tests need airflow/avalon/lakefs_sdk importable (e.g. inside the
Roger image); they skip cleanly elsewhere.
"""

import os
from functools import partial
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

tasks = pytest.importorskip("roger.tasks")


def make_ti(dag_id="annotate_and_index",
            task_id="tg.annotate_topmed_files",
            run_id="manual__1", try_number=1, upstream_ids=()):
    return SimpleNamespace(
        dag_id=dag_id, task_id=task_id, run_id=run_id,
        try_number=try_number,
        task=SimpleNamespace(upstream_task_ids=list(upstream_ids)))


def paged_diff(entries, page_size=2):
    """Fake refs_api.diff_refs returning paginated results."""
    pages = ([entries[i:i + page_size]
              for i in range(0, len(entries), page_size)] or [[]])

    def fetch(**kwargs):
        idx = int(kwargs.get('after') or 0)
        return SimpleNamespace(
            results=pages[idx],
            pagination=SimpleNamespace(has_more=idx + 1 < len(pages),
                                       next_offset=idx + 1))
    return fetch


def paged_objects(paths, page_size=2):
    """Fake objects_api.list_objects returning paginated object listings."""
    pages = ([paths[i:i + page_size]
              for i in range(0, len(paths), page_size)] or [[]])

    def fetch(**kwargs):
        idx = int(kwargs.get('after') or 0)
        return SimpleNamespace(
            results=[SimpleNamespace(path=p) for p in pages[idx]],
            pagination=SimpleNamespace(has_more=idx + 1 < len(pages),
                                       next_offset=idx + 1))
    return fetch


def _tag_not_found(repository, tag):
    from lakefs_sdk.exceptions import NotFoundException
    raise NotFoundException(status=404)


class FakeClient:
    def __init__(self, diff_entries=None, tip="tipA", objects=None):
        self.downloads = []
        self._client = SimpleNamespace(
            refs_api=SimpleNamespace(
                diff_refs=paged_diff(diff_entries or []),
                log_commits=lambda repository, ref, amount:
                    SimpleNamespace(results=[SimpleNamespace(id=tip)])),
            # resolve_ref_tip asks the tags API first; these fakes use
            # branch names, so the tag lookup misses and it falls through
            tags_api=SimpleNamespace(get_tag=_tag_not_found),
            objects_api=SimpleNamespace(
                list_objects=paged_objects(objects or [])))

    def download_files(self, remote_files, local_path, repository,
                       branch_or_commit_id):
        self.downloads.append((tuple(remote_files), local_path, repository,
                               branch_or_commit_id))


@pytest.fixture
def lakefs_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ROGER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(tasks.config.lakefs_config, "enabled", True)
    monkeypatch.setattr(tasks.config.lakefs_config, "repo", "roger-out")
    monkeypatch.setattr(tasks.config.lakefs_config, "branch", "main")
    return tmp_path


def diff_entry(diff_type, path):
    return SimpleNamespace(type=diff_type, path=path)


def test_incremental_state_key():
    key = tasks.incremental_state_key(
        "annotate_and_index", "tg.annotate_topmed_files", "topmed", "v2.0")
    assert key == ("roger_incr::annotate_and_index::"
                   "tg.annotate_topmed_files::topmed@v2.0")
    other = tasks.incremental_state_key(
        "annotate_and_index", "tg.annotate_topmed_files", "topmed", "v3.0")
    assert key != other


def test_resolve_ref_tip():
    assert tasks.resolve_ref_tip(FakeClient(tip="abc123"), 'r', 'v1.0') \
        == "abc123"
    empty = FakeClient()
    empty._client.refs_api.log_commits = (
        lambda repository, ref, amount: SimpleNamespace(results=[]))
    # empty history: fall back to the ref itself
    assert tasks.resolve_ref_tip(empty, 'r', 'v1.0') == 'v1.0'


def test_get_changed_files_buckets_and_prefix():
    entries = [
        diff_entry('added', 'a/task/f1'),
        diff_entry('changed', 'a/task/f2'),
        diff_entry('removed', 'a/task/f3'),
        diff_entry('added', 'a/task_b/f4'),
        diff_entry('conflict', 'a/task/f5'),
    ]
    client = FakeClient(diff_entries=entries)

    # prefix without trailing slash must not match the 'a/task_b' sibling
    changes = tasks.get_changed_files(client, 'repo', 'c1', 'c2',
                                      prefixes=['a/task'])
    assert changes == {'added': ['a/task/f1'], 'changed': ['a/task/f2'],
                       'removed': ['a/task/f3']}

    # '*' or no prefixes means no filtering; conflict entries ignored
    for prefixes in (['*'], None):
        changes = tasks.get_changed_files(client, 'repo', 'c1', 'c2',
                                          prefixes=prefixes)
        assert changes['added'] == ['a/task/f1', 'a/task_b/f4']
        assert changes['removed'] == ['a/task/f3']


def test_setup_input_data_skips_when_no_change(monkeypatch, lakefs_env):
    client = FakeClient(tip="tipA")
    monkeypatch.setattr(tasks, "init_lakefs_client", lambda config: client)
    monkeypatch.setattr(tasks, "_get_last_consumed", lambda key: "tipA")
    get_files = MagicMock()
    monkeypatch.setattr(tasks, "get_files", get_files)

    context = {'ti': make_ti(), 'params': {'incremental': True}}
    exec_conf = {'repos': [{'repo': 'topmed', 'branch': 'v2.0', 'path': '*'}]}
    with pytest.raises(tasks.AirflowSkipException):
        tasks.setup_input_data(context, exec_conf)
    get_files.assert_not_called()
    assert client.downloads == []


def test_setup_input_data_first_run_full_download(monkeypatch, lakefs_env):
    client = FakeClient(tip="tipA")
    monkeypatch.setattr(tasks, "init_lakefs_client", lambda config: client)
    monkeypatch.setattr(tasks, "_get_last_consumed", lambda key: None)
    get_files = MagicMock()
    monkeypatch.setattr(tasks, "get_files", get_files)

    ti = make_ti()
    context = {'ti': ti, 'params': {'incremental': True}}
    exec_conf = {'repos': [{'repo': 'topmed', 'branch': 'v2.0', 'path': '*'}]}
    tasks.setup_input_data(context, exec_conf)

    get_files.assert_called_once()
    call = get_files.call_args.kwargs
    assert call['branch'] == "tipA"          # pinned to resolved tip
    assert call['changes_only'] is False
    assert call['repo'] == 'topmed'

    state = tasks.read_state_file(ti)
    key = tasks.incremental_state_key(ti.dag_id, ti.task_id, 'topmed', 'v2.0')
    assert state['entries'][key]['commit_id'] == "tipA"


def test_setup_input_data_incremental_diff_download(monkeypatch, lakefs_env):
    entries = [diff_entry('added', 'f1'), diff_entry('removed', 'f2')]
    client = FakeClient(diff_entries=entries, tip="tipNew")
    monkeypatch.setattr(tasks, "init_lakefs_client", lambda config: client)
    monkeypatch.setattr(tasks, "_get_last_consumed", lambda key: "tipOld")
    get_files = MagicMock()
    monkeypatch.setattr(tasks, "get_files", get_files)

    ti = make_ti()
    context = {'ti': ti, 'params': {'incremental': True}}
    exec_conf = {'repos': [{'repo': 'topmed', 'branch': 'v2.0', 'path': '*'}]}
    tasks.setup_input_data(context, exec_conf)

    get_files.assert_not_called()
    assert len(client.downloads) == 1
    remote_files, _local, repo, ref = client.downloads[0]
    assert remote_files == ('f1',)
    assert repo == 'topmed'
    assert ref == "tipNew"

    state = tasks.read_state_file(ti)
    assert state['removed'] == {'topmed': ['f2']}
    key = tasks.incremental_state_key(ti.dag_id, ti.task_id, 'topmed', 'v2.0')
    assert state['entries'][key]['commit_id'] == "tipNew"


def test_find_sibling_files():
    # data dict changed in a study dir; GapExchange sibling lives alongside it
    objects = ['s/phs1.v1/data_dict.xml',
               's/phs1.v1/GapExchange_phs1.v1.xml',
               's/phs1.v1/other.xml']
    client = FakeClient(objects=objects)
    siblings = tasks.find_sibling_files(
        client, 'repo', 'tip', ['s/phs1.v1/data_dict.xml'])
    assert siblings == ['s/phs1.v1/GapExchange_phs1.v1.xml']

    # already-downloaded marker is not duplicated
    assert tasks.find_sibling_files(
        client, 'repo', 'tip',
        ['s/phs1.v1/GapExchange_phs1.v1.xml']) == []


def test_setup_input_data_incremental_pulls_gap_exchange(monkeypatch,
                                                         lakefs_env):
    entries = [diff_entry('changed', 's/phs1.v1/data_dict.xml')]
    objects = ['s/phs1.v1/data_dict.xml',
               's/phs1.v1/GapExchange_phs1.v1.xml']
    client = FakeClient(diff_entries=entries, tip="tipNew", objects=objects)
    monkeypatch.setattr(tasks, "init_lakefs_client", lambda config: client)
    monkeypatch.setattr(tasks, "_get_last_consumed", lambda key: "tipOld")
    monkeypatch.setattr(tasks, "get_files", MagicMock())

    context = {'ti': make_ti(), 'params': {'incremental': True}}
    exec_conf = {'repos': [{'repo': 'topmed', 'branch': 'v2.0', 'path': '*'}]}
    tasks.setup_input_data(context, exec_conf)

    remote_files, _local, _repo, _ref = client.downloads[0]
    assert set(remote_files) == {'s/phs1.v1/data_dict.xml',
                                 's/phs1.v1/GapExchange_phs1.v1.xml'}


def test_setup_input_data_incremental_pull_false(monkeypatch, lakefs_env):
    # ES rebuild tasks: even with incremental=True and no upstream changes,
    # incremental_pull=False must force a full pinned download (no skip)
    client = FakeClient(tip="tipA")
    monkeypatch.setattr(tasks, "init_lakefs_client", lambda config: client)
    monkeypatch.setattr(tasks, "_get_last_consumed", lambda key: "tipA")
    get_files = MagicMock()
    monkeypatch.setattr(tasks, "get_files", get_files)

    context = {'ti': make_ti(), 'params': {'incremental': True}}
    exec_conf = {'repos': [{'repo': 'roger-out', 'branch': 'main',
                            'path': 'dag/task'}],
                 'incremental_pull': False}
    tasks.setup_input_data(context, exec_conf)

    get_files.assert_called_once()
    call = get_files.call_args.kwargs
    assert call['branch'] == "tipA"
    assert call['changes_only'] is False


def test_removed_bases(lakefs_env):
    removed = {
        # external source repo: filename minus last extension
        'topmed': ['some/dir/study_one.xml', 'study_two.csv'],
        # roger repo: first segment under the upstream task path
        'roger-out': [
            'annotate_and_index/tg.annotate_x_files/study_three/elements.txt',
            'annotate_and_index/tg.annotate_x_files/.removed_files.json',
        ],
    }
    bases = tasks.removed_bases(
        removed, 'annotate_and_index', ['tg.annotate_x_files'])
    assert bases == {'study_one', 'study_two', 'study_three'}


def test_stale_output_paths():
    remote = 'annotate_and_index/tg.crawl_x/'
    existing = [
        remote + 'study_one/expanded_concepts.txt',
        remote + 'study_one/elements.txt',
        remote + 'study_one_kgx.json',
        remote + 'study_one_extra/elements.txt',   # prefix sibling: keep
        remote + 'study_two/elements.txt',         # not removed: keep
        remote + '.removed_files.json',            # manifest: keep
    ]
    stale = tasks.stale_output_paths(existing, remote, {'study_one'})
    assert stale == [
        remote + 'study_one/expanded_concepts.txt',
        remote + 'study_one/elements.txt',
        remote + 'study_one_kgx.json',
    ]


def test_setup_input_data_manual_override_precedence(monkeypatch, lakefs_env):
    client = FakeClient()
    monkeypatch.setattr(tasks, "init_lakefs_client", lambda config: client)
    last_consumed = MagicMock()
    monkeypatch.setattr(tasks, "_get_last_consumed", last_consumed)
    get_files = MagicMock()
    monkeypatch.setattr(tasks, "get_files", get_files)

    ti = make_ti()
    context = {'ti': ti, 'params': {
        'repository_id': 'ext-repo', 'branch_name': 'b',
        'commitid_from': 'c1', 'commitid_to': 'c2', 'incremental': True}}
    tasks.setup_input_data(context, {'repos': []})

    last_consumed.assert_not_called()
    get_files.assert_called_once()
    call = get_files.call_args.kwargs
    assert call['repo'] == 'ext-repo'
    assert call['branch'] == 'b'
    assert call['changes_only'] is True
    assert call['changes_from'] == 'c1'
    assert call['changes_to'] == 'c2'
    assert tasks.read_state_file(ti) == {}


def test_record_state_callback_sets_variables_and_cleans(monkeypatch,
                                                         lakefs_env):
    ti = make_ti()
    key = tasks.incremental_state_key(ti.dag_id, ti.task_id, 'topmed', 'v2.0')
    tasks.write_state_file(ti, {
        'entries': {key: {'repo': 'topmed', 'branch': 'v2.0',
                          'commit_id': 'tipA'}},
        'removed': {}})
    state_file = tasks.get_state_file_path(ti)
    assert os.path.isfile(state_file)

    recorded = []
    monkeypatch.setattr(
        tasks, "Variable",
        SimpleNamespace(set=lambda k, v: recorded.append((k, v))))

    tasks.record_state_callback({'ti': ti})

    assert recorded == [(key, 'tipA')]
    assert not os.path.exists(state_file)


def test_state_file_noop_when_lakefs_disabled(monkeypatch):
    monkeypatch.setattr(tasks.config.lakefs_config, "enabled", False)
    ti = make_ti()
    assert tasks.get_state_file_path(ti) is None
    tasks.write_state_file(ti, {'entries': {}})  # must not raise
    assert tasks.read_state_file(ti) == {}


def test_task_wrapper_calls_core_function_shape(monkeypatch):
    """roger.core functions take explicit kwargs, not a task_kwargs dict."""
    monkeypatch.setattr(tasks.config.lakefs_config, "enabled", False)
    seen = {}

    def core_like(to_string=False, config=None, input_data_path=None,
                  output_data_path=None):
        seen.update(to_string=to_string, config=config,
                    input_data_path=input_data_path,
                    output_data_path=output_data_path)
        return "ok"

    assert tasks.task_wrapper(core_like, dag_run=None, to_string=True) == "ok"
    assert seen['to_string'] is True
    assert seen['config'] is tasks.config
    assert seen['input_data_path'] is None


def test_task_wrapper_calls_pipeline_method_shape(monkeypatch):
    "The annotate/index path goes through execute_pipeline_method."
    monkeypatch.setattr(tasks.config.lakefs_config, "enabled", False)
    seen = {}

    class FakePipeline:
        def __init__(self, config=None, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def annotate(self, to_string=False, input_data_path=None,
                     output_data_path=None):
            seen.update(to_string=to_string,
                        input_data_path=input_data_path,
                        output_data_path=output_data_path)
            return "annotated"

    callable_ = partial(tasks.execute_pipeline_method,
                        pipeline_class=FakePipeline,
                        configparam=tasks.config,
                        method_name='annotate')
    out = tasks.task_wrapper(callable_, dag_run=None, to_string=True,
                             pass_conf=False)
    assert out == "annotated"
    assert seen['to_string'] is True


def test_orphaned_output_paths(tmp_path):
    """Objects from previous runs, whose names no longer exist locally."""
    (tmp_path / "nodes").mkdir()
    (tmp_path / "nodes" / "biolink~Gene.csv-0-4").write_text("x")
    (tmp_path / "nodes" / "biolink~Gene.csv-1-4").write_text("x")

    remote = "knowledge_graph_build/CreateBulkLoadNodes/"
    existing = [
        remote + "nodes/biolink~Gene.csv-0-4",   # current run, keep
        remote + "nodes/biolink~Gene.csv-1-4",   # current run, keep
        remote + "nodes/biolink~Gene.csv-0-3",   # previous run, drop
        remote + "nodes/biolink~AnatomicalEntity.csv-0-31",  # older, drop
    ]
    orphans = tasks.orphaned_output_paths(existing, remote, str(tmp_path))
    assert orphans == [remote + "nodes/biolink~Gene.csv-0-3",
                       remote + "nodes/biolink~AnatomicalEntity.csv-0-31"]


def test_orphaned_output_paths_empty_when_in_sync(tmp_path):
    (tmp_path / "a.csv").write_text("x")
    remote = "dag/task/"
    assert tasks.orphaned_output_paths([remote + "a.csv"], remote,
                                       str(tmp_path)) == []


def test_memory_override_patches_base_container():
    pytest.importorskip("kubernetes")
    cfg = tasks.memory_override("15Gi")
    pod = cfg["pod_override"]
    container = pod.spec.containers[0]
    assert container.name == "base"
    assert container.resources.limits == {"memory": "15Gi"}
    # request stays small so the namespace quota is not reserved wholesale
    assert container.resources.requests == {"memory": "1Gi"}


def test_es_taskgroup_pulls_crawl_outputs_only(monkeypatch, lakefs_env):
    """index_variables must read crawl's expanded elements.txt, not
    annotate's: only the crawl copy carries KG-derived optional_terms, and
    the storage glob ('**/elements.txt') cannot tell them apart."""
    recorded = {}

    def fake_create_python_task(dag, name, a_callable, **kw):
        recorded[name] = [r['path'] for r in (kw.get('external_repos') or [])]
        return MagicMock(name=name)

    monkeypatch.setattr(tasks, "create_python_task", fake_create_python_task)
    monkeypatch.setattr(tasks, "TaskGroup", MagicMock())
    monkeypatch.setattr(tasks, "EmptyOperator", MagicMock())

    class FakePipeline:
        pipeline_name = "heal-mds-studies"
        input_version = "main"

    dag = SimpleNamespace(dag_id="annotate_and_index")
    tasks.create_es_taskgroup(dag, FakePipeline, tasks.config)

    assert set(recorded) == {
        "index_heal-mds-studies_variables",
        "validate_heal-mds-studies_index_variables",
        "index_heal-mds-studies_concepts",
        "validate_heal-mds-studies_index_concepts"}, recorded
    for name, paths in recorded.items():
        assert paths, f"{name} pulls nothing"
        assert all("crawl_heal-mds-studies" in p for p in paths), (name, paths)
        assert not any("annotate_heal-mds-studies_files" in p
                       for p in paths), (name, paths)


def test_merge_searchable_docs_unions_lists_keeps_new_scalars():
    """The same CDE id appears in several element files with different
    concepts and parents (BRTHDTC in adult- and pediatric-demographic);
    indexing must union those, not overwrite."""
    base = pytest.importorskip("roger.pipelines.base")

    adult = {"id": "BRTHDTC", "name": "BRTHDTC", "description": "old",
             "identifiers": ["UMLS:C0005615"], "parents": ["adult-demographic"],
             "search_terms": ["Birth"], "optional_terms": [], "programs": [],
             "tags": []}
    pediatric = {"id": "BRTHDTC", "name": "BRTHDTC", "description": "new",
                 "identifiers": ["UMLS:C0011008"],
                 "parents": ["pediatric-demographic"],
                 "search_terms": ["Date of birth"], "optional_terms": [],
                 "programs": [], "tags": []}

    merged = base.merge_searchable_docs(adult, pediatric)
    assert merged["identifiers"] == sorted(["UMLS:C0005615", "UMLS:C0011008"])
    assert merged["parents"] == sorted(["adult-demographic",
                                        "pediatric-demographic"])
    assert set(merged["search_terms"]) == {"Birth", "Date of birth"}
    # scalars come from the newer document
    assert merged["description"] == "new"


def test_merge_searchable_docs_dedupes_tags():
    base = pytest.importorskip("roger.pipelines.base")
    tag = {"category": "c", "value": "v"}
    merged = base.merge_searchable_docs({"tags": [tag]}, {"tags": [dict(tag)]})
    assert merged["tags"] == [tag]


def test_validate_concepts_waits_for_index_variables(monkeypatch,
                                                     lakefs_env):
    """validate_indexed_concepts searches the VARIABLES index, so it must
    wait for index_variables -- not just index_concepts. Otherwise it runs
    against a freshly wiped, half-populated index and finds nothing."""
    made = {}

    def fake_create_python_task(dag, name, a_callable, **kw):
        t = MagicMock(name=name)
        t.upstreams = []
        t.set_upstream = lambda other: t.upstreams.append(other)
        made[name] = t
        return t

    monkeypatch.setattr(tasks, "create_python_task", fake_create_python_task)
    monkeypatch.setattr(tasks, "TaskGroup", MagicMock())
    monkeypatch.setattr(tasks, "EmptyOperator", MagicMock())

    class FakePipeline:
        pipeline_name = "heal-cdes"
        input_version = "main"

    tasks.create_es_taskgroup(SimpleNamespace(dag_id="annotate_and_index"),
                              FakePipeline, tasks.config)

    validate = made["validate_heal-cdes_index_concepts"]
    assert made["index_heal-cdes_concepts"] in validate.upstreams
    assert made["index_heal-cdes_variables"] in validate.upstreams


def test_quiet_noisy_loggers_caps_http_chatter():
    """requests_cache logs 5 DEBUG lines per HTTP call; a single annotate task
    produced a 2.9 GB log that way, which evicted the api-server (750Mi
    ephemeral) when the log was opened."""
    import logging
    rl = pytest.importorskip("roger.logger")

    logging.getLogger("requests_cache.policy.actions").setLevel(logging.DEBUG)
    rl.quiet_noisy_loggers()
    # child loggers inherit the cap from the configured parent
    assert not logging.getLogger(
        "requests_cache.policy.actions").isEnabledFor(logging.DEBUG)
    assert not logging.getLogger("httpcore.http11").isEnabledFor(logging.DEBUG)
    # roger's own logger is untouched
    assert logging.getLogger("roger").isEnabledFor(logging.INFO)


def test_resolve_ref_tip_prefers_tags(monkeypatch):
    """lakefs validates log_commits' ref as a *branch id*, so a dotted tag
    like 'v7.0' (kgx.data_sets 'baseline-graph:v7.0') 400s before the tag is
    looked up. Tags must be resolved through the tags API."""
    from lakefs_sdk.exceptions import NotFoundException

    calls = []

    class Tags:
        def get_tag(self, repository, tag):
            calls.append(('get_tag', tag))
            if tag == 'v7.0':
                return SimpleNamespace(commit_id='tagcommit')
            raise NotFoundException(status=404)

    class Refs:
        def log_commits(self, repository, ref, amount):
            calls.append(('log_commits', ref))
            assert ref != 'v7.0', "dotted tag must not reach log_commits"
            return SimpleNamespace(
                results=[SimpleNamespace(id='branchcommit')])

    client = SimpleNamespace(_client=SimpleNamespace(tags_api=Tags(),
                                                     refs_api=Refs()))

    assert tasks.resolve_ref_tip(client, 'baseline-graph', 'v7.0') == 'tagcommit'
    assert tasks.resolve_ref_tip(client, 'baseline-graph', 'main') == 'branchcommit'
    assert ('log_commits', 'main') in calls


# --- resuming an interrupted annotate --------------------------------------
# Annotation costs tens of seconds per input file, so a bdc-parent run is
# weeks long. Its output only reaches lakefs when the whole task succeeds, so
# a task that died at file 40,000 of 61,597 used to discard all of it.

def _write(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)


def test_reuse_prior_try_outputs_carries_finished_work_forward(lakefs_env):
    prior = lakefs_env / ("annotate_and_index_tg.annotate_topmed_files"
                          "_manual__1_1_output")
    _write(str(prior / "phs000007_dd" / "elements.txt"))
    _write(str(prior / "phs000007_dd" / "concepts.txt"))

    ti = make_ti(try_number=2)
    assert tasks.reuse_prior_try_outputs(ti) == 2

    current = lakefs_env / ("annotate_and_index_tg.annotate_topmed_files"
                            "_manual__1_2_output")
    assert (current / "phs000007_dd" / "elements.txt").is_file()
    assert (current / "phs000007_dd" / "concepts.txt").is_file()


def test_reuse_prior_try_outputs_does_not_overwrite_current_try(lakefs_env):
    prior = lakefs_env / ("annotate_and_index_tg.annotate_topmed_files"
                          "_manual__1_1_output")
    current = lakefs_env / ("annotate_and_index_tg.annotate_topmed_files"
                            "_manual__1_2_output")
    _write(str(prior / "d" / "elements.txt"), "old")
    _write(str(current / "d" / "elements.txt"), "new")

    assert tasks.reuse_prior_try_outputs(make_ti(try_number=2)) == 0
    assert (current / "d" / "elements.txt").read_text() == "new"


def test_clean_up_keeps_output_on_failure(lakefs_env):
    "The failure callback must not destroy what a retry can resume from."
    ti = make_ti(try_number=1)
    base = "annotate_and_index_tg.annotate_topmed_files_manual__1_1_"
    _write(str(lakefs_env / (base + "input") / "src.xml"))
    _write(str(lakefs_env / (base + "output") / "d" / "elements.txt"))

    tasks.clean_up({'ti': ti}, keep_output=True)

    assert not (lakefs_env / (base + "input")).exists()
    assert (lakefs_env / (base + "output") / "d" / "elements.txt").is_file()


def test_clean_up_all_tries_clears_every_try_dir(lakefs_env):
    "A successful commit has everything; leaving try dirs would leak the PVC."
    for try_number in (1, 2):
        base = ("annotate_and_index_tg.annotate_topmed_files_manual__1_"
                f"{try_number}_")
        _write(str(lakefs_env / (base + "input") / "src.xml"))
        _write(str(lakefs_env / (base + "output") / "d" / "elements.txt"))

    tasks.clean_up({'ti': make_ti(try_number=2)}, all_tries=True)

    leftovers = list(lakefs_env.glob("annotate_and_index_*"))
    assert leftovers == [], leftovers
