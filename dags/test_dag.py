"""Just a test dag to see if all the wrappers are working correctly.
"""

from airflow.models import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from roger.tasks import default_args, create_python_task

with DAG(
        dag_id='test_dag',
        default_args=default_args,
        params=
            {
                "repository_id": None,
                "branch_name": None,
                "commitid_from": None,
                "commitid_to": None
            },
        # schedule_interval=None
) as dag:

    init = EmptyOperator(task_id="init", dag=dag)
    finish = EmptyOperator(task_id="finish", dag=dag)

    def print_context(ds=None, **kwargs):
        print(">>>All kwargs")
        print(kwargs)
        print(">>>All ds")
        print(ds)

    (init >>
     create_python_task(dag, "print_context", print_context) >>
     finish)

    #run_this = PythonOperator(task_id="print_the_context", python_callable=print_context)

if __name__ == "__main__":
    dag.test()
