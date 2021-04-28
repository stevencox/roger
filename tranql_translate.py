# -*- coding: utf-8 -*-
#

"""
An Airflow workflow for the Roger Translator KGX data pipeline.
"""

from airflow.operators.bash_operator import BashOperator
from airflow.models import DAG
from roger.core import RogerUtil
from dag_util import get_executor_config, default_args, create_python_task


""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='tranql_translate',
    default_args=default_args,
    schedule_interval=None
) as dag:

    """ Build the workflow tasks. """
    intro = BashOperator(task_id='Intro',
                         bash_command='echo running tranql translator && exit 0',
                         executor_config= get_executor_config())
    get_kgx = create_python_task (dag, "GetSource", RogerUtil.get_kgx)
    create_schema = create_python_task (dag, "CreateSchema", RogerUtil.create_schema)
    merge_nodes = create_python_task (dag, "MergeNodes", RogerUtil.merge_nodes)
    create_bulk_load = create_python_task (dag, "CreateBulkLoad", RogerUtil.create_bulk_load)
    bulk_load = create_python_task (dag, "BulkLoad", RogerUtil.bulk_load)
    validate = create_python_task (dag, "Validate", RogerUtil.validate)
    finish = BashOperator (task_id='Finish', bash_command='echo finish')

    """ Build the DAG. """
    intro >> get_kgx >> [ create_schema, merge_nodes ] >> create_bulk_load >> \
        bulk_load >> validate >> finish
