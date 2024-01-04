# -*- coding: utf-8 -*-
#

"""
An Airflow workflow for the Roger Translator KGX data pipeline.
"""

from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
import roger
from roger.tasks import get_executor_config, default_args, create_python_task

""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='tranql_translate',
    default_args=default_args,
    schedule_interval=None,
    concurrency=16,
) as dag:

    """ Build the workflow tasks. """
    intro = EmptyOperator(task_id='Intro')
    get_kgx = create_python_task (dag, "GetSource", roger.get_kgx)
    create_nodes_schema = create_python_task(dag, "CreateNodesSchema",
                                             roger.create_nodes_schema)
    create_edges_schema = create_python_task(dag, "CreateEdgesSchema",
                                             roger.create_edges_schema)
    continue_task_bulk_load = EmptyOperator(task_id="continueBulkCreate")
    continue_task_validate = EmptyOperator(task_id="continueValidation")
    merge_nodes = create_python_task (dag, "MergeNodes", roger.merge_nodes)
    create_bulk_load_nodes = create_python_task(dag, "CreateBulkLoadNodes",
                                                roger.create_bulk_nodes)
    create_bulk_load_edges = create_python_task(dag, "CreateBulkLoadEdges",
                                                roger.create_bulk_edges)
    bulk_load = create_python_task(dag, "BulkLoad", roger.bulk_load)
    check_tranql = create_python_task(dag, "CheckTranql",
                                      roger.check_tranql)
    validate = create_python_task(dag, "Validate", roger.validate)
    finish = EmptyOperator(task_id='Finish')

    """ Build the DAG. """
    intro >> get_kgx >> merge_nodes >> [create_nodes_schema, create_edges_schema ] >> continue_task_bulk_load >> \
    [create_bulk_load_nodes, create_bulk_load_edges] >> bulk_load >> continue_task_validate >>[validate, check_tranql ] >> finish
