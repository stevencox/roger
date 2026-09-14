"""Output must be committed from post_execute, not on_success_callback.

Airflow records end_date and releases downstream tasks before success
callbacks run, so committing there let downstream read the branch before the
output landed. It also only logs exceptions from state-change callbacks, so a
failed merge left the task green.
"""
from unittest import mock

import pytest


def _make_task(**kw):
    from roger import tasks
    with mock.patch.object(tasks, 'PythonOperator', lambda **a: a):
        return tasks.create_python_task(
            mock.MagicMock(), "T", lambda **_: None, **kw)


@pytest.mark.parametrize("no_output_files", [False, True])
def test_commit_runs_from_post_execute(no_output_files, monkeypatch):
    from roger import tasks
    monkeypatch.setattr(tasks.config, 'lakefs_config',
                        mock.MagicMock(enabled=True))
    args = _make_task(no_output_files=no_output_files)
    assert 'post_execute' in args
    assert 'on_success_callback' not in args

    called = []
    target = 'record_state_callback' if no_output_files else 'avalon_commit_callback'
    monkeypatch.setattr(tasks, target, lambda ctx, **k: called.append(ctx))
    # rebuild so the partial closes over the patched function
    args = _make_task(no_output_files=no_output_files)
    args['post_execute']({'ti': 'x'}, None)
    assert called == [{'ti': 'x'}]


def test_post_execute_accepts_the_result_arg(monkeypatch):
    """Airflow calls the hook as (context, result); ours takes context."""
    from roger import tasks
    monkeypatch.setattr(tasks.config, 'lakefs_config',
                        mock.MagicMock(enabled=True))
    monkeypatch.setattr(tasks, 'avalon_commit_callback', lambda ctx, **k: None)
    hook = _make_task()['post_execute']
    hook({'ti': 'x'}, "some result")   # must not raise TypeError


class _LakefsError(Exception):
    """Shaped like lakefs_sdk's BadRequestException."""
    def __init__(self, status, body):
        super().__init__(f"({status})\nHTTP response body: {body}")
        self.status = status


def test_empty_merge_is_not_a_failure():
    """lakefs 400s a merge with nothing to apply.

    That happens whenever a task's output already matches the branch, which
    is normal for deterministic work over unchanged input. Failing the task
    there stalls the dag for no reason.
    """
    from roger.tasks import _merge_had_no_changes
    assert _merge_had_no_changes(
        _LakefsError(400, '{"message":"update branch main: no changes"}'))


def test_other_merge_failures_still_raise():
    from roger.tasks import _merge_had_no_changes
    assert not _merge_had_no_changes(
        _LakefsError(400, '{"message":"branch not found"}'))
    assert not _merge_had_no_changes(
        _LakefsError(500, '{"message":"no changes"}'))   # wrong status
    assert not _merge_had_no_changes(RuntimeError("no changes"))  # no status


def test_output_is_kept_on_failure_only_when_resumable(monkeypatch):
    """keep_output is the resume mechanism for annotate, and only annotate.

    crawl and make_kgx redo everything on retry, so retaining their output
    buys nothing and costs disk -- three failed crawls held 47GB and filled
    the shared volume, which is what had made them fail.
    """
    from roger import tasks
    monkeypatch.setattr(tasks.config, 'lakefs_config',
                        mock.MagicMock(enabled=True))
    for resumable, expected in ((True, True), (False, False)):
        args = _make_task(resumable=resumable)
        assert args['on_failure_callback'].keywords['keep_output'] is expected
    # default must be the safe one
    assert _make_task()['on_failure_callback'].keywords['keep_output'] is False
