from airflow.models import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator

from dug_helpers.dug_utils import DugUtil, get_topmed_files, get_dbgap_files
from roger.dag_util import default_args, create_python_task

DAG_ID = 'annotate_dug'

""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    schedule_interval=None
) as dag:

    """Build workflow tasks."""
    intro = BashOperator(task_id='Intro',
                         bash_command='echo running tranql translator && exit 0',
                         dag=dag)
    # make_kg_tagged = create_python_task(dag, "create_kgx_files", DugUtil.make_kg_tagged)

    # Unzip and get files, avoid this because
    # 1. it takes a bit of time making the dag itself, webserver hangs
    # 2. Every task in this dag would still need to execute this part
    # making it redundant
    # 3. tasks like intro would fail because they don't have the data dir mounted.

    get_topmed_files = create_python_task(dag, "get_topmed_data", get_topmed_files)
    extract_db_gap_files = create_python_task(dag, "get_dbgap_data", get_dbgap_files)

    annotate_topmed_files = create_python_task(dag, "annotate_topmed_files", DugUtil.annotate_topmed_files)
    annotate_db_gap_files = create_python_task(dag, "annotate_db_gap_files", DugUtil.annotate_db_gap_files)

    make_kg_tagged = create_python_task(dag, "make_tagged_kgx", DugUtil.make_kg_tagged)

    dummy_stepover = DummyOperator(
        task_id="continue",
    )

    #intro >> run_printlog
    intro >> get_topmed_files >> annotate_topmed_files >> dummy_stepover
    intro >> extract_db_gap_files >> annotate_db_gap_files >> dummy_stepover
    dummy_stepover >> make_kg_tagged

    #intro >> [get_topmed_files, extract_db_gap_files] >> dummy_stepover >>\
    #[annotate_topmed_files, annotate_db_gap_files] >> make_kg_tagged
