#!/usr/bin/env python
"""Seed the incremental-ingest Airflow Variables for datasets already ingested.

A fresh instance has no state, so the first run re-annotates everything even
though the data is already in lakefs. This writes the "last consumed commit"
Variables so the first run diffs instead.

    # print the commands, change nothing
    python scripts/seed_incremental_state.py \
        --dataset heal-mds-studies:main=a352eccb... \
        --dataset heal-cdes:main=f40bd330...

    # ...and the downstream tasks, so crawl/make_kgx don't redo everything
    python scripts/seed_incremental_state.py \
        --dataset heal-mds-studies:main=a352eccb... \
        --downstream <runtime-repo>:<runtime-branch>=<runtime-tip-commit> \
        --apply

Only pass --downstream when the runtime repo ALREADY holds crawl and KGX
outputs for these datasets; it claims everything up to that commit is
consumed, and work that never ran would be skipped permanently.

Run inside the roger image / an airflow pod. --apply shells out to the airflow
CLI, so it needs a pod with metadata-DB access (scheduler, not a worker).
"""

import argparse
import sys

from roger.tasks import ANNOTATE_DAG_ID, file_task_group_id, \
    incremental_state_key


def parse_spec(spec):
    "name:branch=commit -> (name, branch, commit)"
    try:
        target, commit = spec.split('=', 1)
        name, branch = target.rsplit(':', 1)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected name:branch=commit, got {spec!r}")
    if not (name and branch and commit):
        raise argparse.ArgumentTypeError(
            f"expected name:branch=commit, got {spec!r}")
    return name, branch, commit


def build(datasets, downstream=None):
    """[(key, commit)] for the annotate tasks, plus crawl/make_kgx when a
    downstream (runtime repo) target is given."""
    pairs = []
    for name, branch, commit in datasets:
        group = file_task_group_id(name)
        pairs.append((incremental_state_key(
            ANNOTATE_DAG_ID, f"{group}.annotate_{name}_files",
            name, branch), commit))
        if downstream:
            repo, ds_branch, ds_commit = downstream
            for task in (f"crawl_{name}", f"make_kgx_{name}"):
                pairs.append((incremental_state_key(
                    ANNOTATE_DAG_ID, f"{group}.{task}",
                    repo, ds_branch), ds_commit))
    return pairs


def self_check():
    pairs = build([parse_spec("heal-cdes:main=abc123")])
    assert pairs == [(
        "roger_incr::annotate_and_index::"
        "heal-cdes_dataset_pipeline_task_group.annotate_heal-cdes_files::"
        "heal-cdes@main", "abc123")], pairs

    pairs = build([parse_spec("d:main=c1")], parse_spec("out:prod=c2"))
    assert [k for k, _ in pairs] == [
        "roger_incr::annotate_and_index::"
        "d_dataset_pipeline_task_group.annotate_d_files::d@main",
        "roger_incr::annotate_and_index::"
        "d_dataset_pipeline_task_group.crawl_d::out@prod",
        "roger_incr::annotate_and_index::"
        "d_dataset_pipeline_task_group.make_kgx_d::out@prod"], pairs
    assert [v for _, v in pairs] == ["c1", "c2", "c2"], pairs
    print("self-check ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', action='append', type=parse_spec,
                        metavar='NAME:BRANCH=COMMIT', default=[],
                        help='pipeline name, its input_version ref, and the '
                             'source commit already ingested')
    parser.add_argument('--downstream', type=parse_spec, default=None,
                        metavar='REPO:BRANCH=COMMIT',
                        help='runtime repo/branch and its current tip, to '
                             'also seed crawl_* and make_kgx_*')
    parser.add_argument('--apply', action='store_true',
                        help='set the Variables instead of printing commands')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()

    if args.self_check:
        self_check()
        return
    if not args.dataset:
        parser.error("at least one --dataset is required")

    pairs = build(args.dataset, args.downstream)

    if not args.apply:
        for key, commit in pairs:
            print(f"airflow variables set '{key}' {commit}")
        print(f"\n# {len(pairs)} variable(s); re-run with --apply to set them",
              file=sys.stderr)
        return

    # airflow.sdk.Variable only works inside a running task (it needs
    # SUPERVISOR_COMMS), so shell out to the CLI, which is what the printed
    # commands do anyway. Needs a pod with metadata-DB access.
    import subprocess
    for key, commit in pairs:
        subprocess.run(['airflow', 'variables', 'set', key, commit],
                       check=True)
        print(f"set {key} = {commit}")


if __name__ == '__main__':
    main()
