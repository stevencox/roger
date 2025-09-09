"""DAG which performs Dug annotate and index operations

This DAG differes slightly from prior versions of the same functionality in
Roger not only in that the annotation and indexing happen in the same DAG, but
also those tasks are broken out into sub-DAGs organized by dataset. Each dataset
has a subdag for all tasks.
"""

import os

from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
from roger.tasks import default_args, create_pipeline_taskgroup

env_enabled_datasets = os.getenv(
    "ROGER_DUG__INPUTS_DATA__SETS", "topmed,anvil").split(",")

with DAG(
        dag_id='annotate_and_index',
        default_args=default_args,
        schedule_interval=None
) as dag:
    init = EmptyOperator(task_id="init", dag=dag)
    finish = EmptyOperator(task_id="finish", dag=dag)

    from roger import pipelines
    from roger.config import config
    envspec = os.getenv("ROGER_DUG__INPUTS_DATA__SETS","topmed:v2.0")
    data_sets = envspec.split(",")
    pipeline_names = {x.split(':')[0]: x.split(':')[1] for x in data_sets}
    for pipeline_class in pipelines.get_pipeline_classes(pipeline_names):
        # Only use pipeline classes that are in the enabled datasets list and
        # that have a properly defined pipeline_name attribute

        # TODO
        # Overriding environment variable just to see if this is working.
        # name = getattr(pipeline_class, 'pipeline_name', '*not defined*')
        # if not name in env_enabled_datasets:
        #     continue

        # Do the thing to add the pipeline's subdag to the dag in the right way
        # . . .

        init >> create_pipeline_taskgroup(dag, pipeline_class, config) >> finish
