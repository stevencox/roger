"""DAG which performs Dug annotate and index operations

This DAG differes slightly from prior versions of the same functionality in
Roger not only in that the annotation and indexing happen in the same DAG, but
also those tasks are broken out into sub-DAGs organized by dataset. Each dataset
has a subdag for all tasks.
"""

import os

from airflow.models import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from roger.tasks import (default_args, create_pipeline_taskgroup,
                         create_es_taskgroup, create_es_wipe_task)

env_enabled_datasets = os.getenv(
    "ROGER_DUG__INPUTS_DATA__SETS", "topmed,anvil").split(",")

with DAG(
        dag_id='annotate_and_index',
        default_args=default_args,
        # incremental state Variables have no compare-and-swap; serialize runs
        max_active_runs=1,
        params=
            {
                "repository_id": None,
                "branch_name": None,
                "commitid_from": None,
                "commitid_to": None,
                # diff source refs against the last ingested commit and only
                # process new/changed files; set false to force a full run
                "incremental": True
            },
        # schedule_interval=None
) as dag:
    init = EmptyOperator(task_id="init", dag=dag)
    finish = EmptyOperator(task_id="finish", dag=dag,
                           trigger_rule="none_failed")


    from roger import pipelines
    from roger.config import config
    envspec = os.getenv("ROGER_DUG__INPUTS_DATA__SETS","topmed:v2.0")
    data_sets = envspec.split(",")
    pipeline_names = {x.split(':')[0]: x.split(':')[1] for x in data_sets}
    pipeline_classes = list(pipelines.get_pipeline_classes(pipeline_names))

    if pipeline_classes:
        # file-based tasks run incrementally per dataset; then one global
        # index wipe; then elastic rebuilds from the full file set left in
        # lakefs (so upstream deletions simply vanish from the indexes)
        wipe_es = create_es_wipe_task(dag, pipeline_classes[0], config)
        for pipeline_class in pipeline_classes:
            init >> create_pipeline_taskgroup(dag, pipeline_class, config) \
                >> wipe_es
            wipe_es >> create_es_taskgroup(dag, pipeline_class, config) \
                >> finish
    else:
        init >> finish

if __name__ == "__main__":
    dag.test()
