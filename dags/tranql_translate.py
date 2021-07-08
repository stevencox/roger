# -*- coding: utf-8 -*-
#

"""
An Airflow workflow for the Roger Translator KGX data pipeline.
"""

from airflow.operators.bash_operator import BashOperator
from airflow.models import DAG
from airflow.operators.dummy_operator import DummyOperator
from roger.core import RogerUtil
from roger.dag_util import get_executor_config, default_args, create_python_task


""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='tranql_translate',
    default_args=default_args,
    schedule_interval=None,
    concurrency=16,
) as dag:

    """ Build the workflow tasks. """
    intro = BashOperator(task_id='Intro',
                         bash_command='echo running tranql translator && exit 0',
                         executor_config= get_executor_config())
    get_kgx = create_python_task (dag, "GetSource", RogerUtil.get_kgx)
    create_nodes_schema = create_python_task (dag, "CreateNodesSchema", RogerUtil.create_nodes_schema)
    create_edges_schema = create_python_task (dag, "CreateEdgesSchema", RogerUtil.create_edges_schema)
    continue_task_bulk_load = DummyOperator(task_id="continueBulkCreate")
    continue_task_validate = DummyOperator(task_id="continueValidation")
    merge_nodes = create_python_task (dag, "MergeNodes", RogerUtil.merge_nodes)
    create_bulk_load_nodes = create_python_task (dag, "CreateBulkLoadNodes", RogerUtil.create_bulk_nodes)
    create_bulk_load_edges = create_python_task (dag, "CreateBulkLoadEdges", RogerUtil.create_bulk_edges)
    bulk_load = create_python_task (dag, "BulkLoad", RogerUtil.bulk_load)
    check_tranql = create_python_task(dag, "CheckTranql", RogerUtil.check_tranql)
    validate = create_python_task (dag, "Validate", RogerUtil.validate)
    finish = BashOperator (task_id='Finish', bash_command='echo finish')

    """ Build the DAG. """
    intro >> get_kgx >> merge_nodes >> [create_nodes_schema, create_edges_schema ] >> continue_task_bulk_load >> \
    [create_bulk_load_nodes, create_bulk_load_edges] >> bulk_load >> continue_task_validate >>[validate, check_tranql ] >> finish
