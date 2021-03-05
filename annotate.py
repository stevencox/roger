import os
from pathlib import Path
from airflow.operators.bash_operator import BashOperator
from airflow.models import DAG
from airflow.contrib.sensors.python_sensor import PythonSensor
from dug_helpers.dug_utils import DugUtil
from dag_util import default_args, create_python_task, get_config


""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='annotate_dug',
    default_args=default_args,
    schedule_interval=None
) as dag:


    """Build workflow tasks."""
    intro = BashOperator(task_id='Intro',
                         bash_command='echo running tranql translator && exit 0',
                         dag=dag)

    is_topmed_file_available = create_python_task(dag, "is_topmed_file_available", DugUtil.is_topmed_data_available)
    dug_load_topmed_variables = create_python_task(dag, "annotate_and_normalize", DugUtil.load_and_annotate)
    make_kg_tagged = create_python_task(dag, "create_kgx_files", DugUtil.make_kg_tagged)

    intro >> is_topmed_file_available >> \
    dug_load_topmed_variables >> make_kg_tagged

