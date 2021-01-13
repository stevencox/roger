# -*- coding: utf-8 -*-
#

"""
An Airflow workflow for the Roger Translator KGX data pipeline.
"""

import os
import subprocess
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.example_dags.libs.helper import print_stuff
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from roger.core import RogerUtil
from roger.Config import get_default_config as get_config
from roger.roger_util import get_logger
from kubernetes.client import models as k8s


default_args = {
    'owner': 'RENCI',
    'start_date': days_ago(1)
}

""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='tranql_translate_k8s_pod_overide_test',
    default_args=default_args,
    schedule_interval=None
) as dag:

    """ Configure use of KubernetesExecutor. """
    at_k8s=True
    
    def get_executor_config (annotations=None):
        """ Get an executor configuration.
        :param annotations: Annotations to attach to the executor.
        :returns: Returns a KubernetesExecutor if K8s is configured and None otherwise.
        """
        k8s_executor_config = {
            "KubernetesExecutor": {
                "volume_mounts": []
            }
        }
        return k8s_executor_config if at_k8s else None

    def task_wrapper(python_callable, **kwargs):
        """
        Overrides configuration with config from airflow.
        :param python_callable:
        :param kwargs:
        :return:
        """
        # get dag config provided
        dag_run = kwargs.get('dag_run')
        dag_conf = {}
        logger = get_logger()
        config = get_config()
        if dag_run:
            dag_conf = dag_run.conf
            # remove this since to send every other argument to the python callable.
            del kwargs['dag_run']
        # overrides values
        config.update(dag_conf)
        logger.info("Config")
        logger.info(config)
        return python_callable(to_string=True, config=config)

    def create_python_task (name, a_callable):
        """ Create a python task.
        :param name: The name of the task.
        :param a_callable: The code to run in this task.
        """
        return PythonOperator(
            task_id=name,
            python_callable=task_wrapper,
            op_kwargs={
                "python_callable": a_callable,
                "to_string": True
            },
            executor_config=get_executor_config (annotations={
                "task_name" : name
            }),
            dag=dag,
            provide_context=True
        )

    """ Build the workflow tasks. """
    intro = BashOperator(task_id='Intro', bash_command='echo running tranql translator && exit 0')
    get_kgx = create_python_task ("GetSource", RogerUtil.get_kgx)
    create_schema = create_python_task ("CreateSchema", RogerUtil.create_schema)
    merge_nodes = create_python_task ("MergeNodes", RogerUtil.merge_nodes)
    create_bulk_load = create_python_task ("CreateBulkLoad", RogerUtil.create_bulk_load)
    bulk_load = create_python_task ("BulkLoad", RogerUtil.bulk_load)
    validate = create_python_task ("Validate", RogerUtil.validate)
    finish = BashOperator (task_id='Finish', bash_command='echo finish')

    """ Build the DAG. """
    intro >> get_kgx >> [ create_schema, merge_nodes ] >> create_bulk_load >> \
        bulk_load >> validate >> finish
