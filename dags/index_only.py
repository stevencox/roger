"""DAG which only runs the Dug ES indexing steps.

Re-indexes Elasticsearch (concepts + variables) from annotate_and_index
outputs already present in the runtime repo on the configured branch -- e.g.
after merging the dev runtime branch into prod. No annotate or crawl is
re-run; inputs are pulled by explicit path from the runtime repo.
"""

import os

from airflow.models import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from roger.tasks import default_args, create_index_only_taskgroup

with DAG(
        dag_id='index_only',
        default_args=default_args,
        max_active_runs=1,
        params={
            # re-index everything present on the branch; not a diff
            "incremental": False,
        },
) as dag:
    init = EmptyOperator(task_id="init", dag=dag)
    finish = EmptyOperator(task_id="finish", dag=dag,
                           trigger_rule="none_failed")

    from roger import pipelines
    from roger.config import config
    envspec = os.getenv("ROGER_DUG__INPUTS_DATA__SETS", "topmed:v2.0")
    data_sets = envspec.split(",")
    pipeline_names = {x.split(':')[0]: x.split(':')[1] for x in data_sets}
    for pipeline_class in pipelines.get_pipeline_classes(pipeline_names):
        init >> create_index_only_taskgroup(dag, pipeline_class, config) \
            >> finish

if __name__ == "__main__":
    dag.test()
