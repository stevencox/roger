import os
from pathlib import Path
from airflow.operators.bash_operator import BashOperator
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.sensors.python_sensor import PythonSensor
from airflow.utils.dates import days_ago
from dug_helpers.dug_utils import DugUtil

from roger.Config import get_default_config as get_config

default_args = {
    'owner': 'RENCI',
    'start_date': days_ago(1)
}


""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='annotate_dug',
    default_args=default_args,
    schedule_interval=None
) as dag:

    at_k8s = True

    def get_executor_config(annotations=None, data_path="/opt/dug-helpers/data"):
        """ Get an executor configuration.
        :param annotations: Annotations to attach to the executor.
        :returns: Returns a KubernetesExecutor if K8s is configured and None otherwise.
        """
        k8s_executor_config = {
            "KubernetesExecutor": {
                "volumes": [
                    {
                        "name": "dug-helpers-data",
                        "persistentVolumeClaim": {
                            "claimName": "roger-data-pvc"
                        }
                    }
                ],
                "volume_mounts": [
                    {
                        "mountPath": data_path,
                        "name": "dug-helpers-data",
                    }
                ]
            }
        }
        return k8s_executor_config if at_k8s else None

    def task_wrapper(a_callable, config, xcom, **kwargs):
        ti = kwargs['ti']
        if xcom:
            value = ti.xcom_pull(key=None, task_ids=ti.previous_ti)
            config.update(value)
        else:
            config = {}
        return a_callable(config)

    def create_python_task(task_id, a_callable, xcom=False):
        data_path = "/opt/dug/data"
        return PythonOperator(
            task_id=task_id,
            python_callable=task_wrapper,
            op_kwargs={
                "a_callable": a_callable,
                "config": {},
                "xcom": xcom
            },
            executor_config=get_executor_config(annotations={"task_name": task_id}, data_path=data_path),
            dag=dag,
            provide_context=True
        )

    def _is_topmed_file_available(**kwargs):
        home = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(home, get_config()['dug_data_root'])
        data_path = Path(file_path)
        data_files = data_path.glob('topmed_*.csv')
        files = [str(file) for file in data_files]
        kwargs['ti'].xcom_push(key='config', value={"topmed_files": files})
        return "Files Pushed"

    """Build workflow tasks."""
    intro = BashOperator(task_id='Intro',
                         bash_command='echo running tranql translator && exit 0',
                         dag=dag)

    is_topmed_file_available = PythonSensor(
        task_id="is_topmed_file_available",
        python_callable=_is_topmed_file_available,
        dag=dag,
        poke_interval=5,
        timeout=20,
        provide_context=True
    )

    dug_load_topmed_variables = create_python_task("load_and_annotate", DugUtil.load_and_annotate, xcom=True)
    make_kg_tagged = create_python_task("make_kg_tagged", DugUtil.make_kg_tagged, xcom=False)

    intro >> is_topmed_file_available >> dug_load_topmed_variables >> make_kg_tagged

