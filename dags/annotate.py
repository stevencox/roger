import os

from airflow.models import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator

from dug_helpers.dug_utils import DugUtil, get_topmed_files, get_dbgap_files,\
    get_nida_files, get_sparc_files, get_anvil_files,\
    get_cancer_data_commons_files, get_kids_first_files,\
    get_sprint_files, get_bacpac_files
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

    # Unzip and get files, avoid this because
    # 1. it takes a bit of time making the dag itself, webserver hangs
    # 2. Every task in this dag would still need to execute this part making it redundant
    # 3. tasks like intro would fail because they don't have the data dir mounted.

    make_kg_tagged = create_python_task(dag, "make_tagged_kgx", DugUtil.make_kg_tagged)

    dummy_stepover = DummyOperator(
        task_id="continue",
    )

    #intro >> run_printlog
    envspec = os.getenv("ROGER_DUG__INPUTS_DATA__SETS","topmed")
    data_sets = envspec.split(",")

    clear_annotation_items = create_python_task(dag, "clear_annotation_files", DugUtil.clear_annotation_cached)

    for i, data_set in enumerate(data_sets):
        if data_set.startswith("bdc"):
            prepare_files = create_python_task(dag, "get_dbgap_data", get_dbgap_files)
            annotate_files = create_python_task(dag, "annotate_db_gap_files", DugUtil.annotate_db_gap_files)
        elif data_set.startswith("nida"):
            prepare_files = create_python_task(dag, "get_nida_files", get_nida_files)
            annotate_files = create_python_task(dag, "annotate_nida_files", DugUtil.annotate_nida_files)
        elif data_set.startswith("sparc"):
            prepare_files = create_python_task(dag, "get_sparc_files", get_sparc_files)
            annotate_files = create_python_task(dag, "annotate_sparc_files", DugUtil.annotate_sparc_files)
        elif data_set.startswith("topmed"):
            prepare_files = create_python_task(dag, "get_topmed_data", get_topmed_files)
            annotate_files = create_python_task(dag, "annotate_topmed_files", DugUtil.annotate_topmed_files)
        elif data_set.startswith("anvil"):
            prepare_files = create_python_task(dag, "get_anvil_data", get_anvil_files)
            annotate_files = create_python_task(dag, "annotate_anvil_files", DugUtil.annotate_anvil_files)
        elif data_set.startswith("crdc"):
            prepare_files = create_python_task(dag, "get_cancer_commons_files", get_cancer_data_commons_files)
            annotate_files = create_python_task(dag, "annotate_cancer_commons_files",
                                                DugUtil.annotate_cancer_commons_files)
        elif data_set.startswith("kfdrc"):
            prepare_files = create_python_task(dag, "get_kids_first_files", get_kids_first_files)
            annotate_files = create_python_task(dag, "annotate_kids_first_files",
                                                DugUtil.annotate_kids_first_files)
        elif data_set.startswith("sprint"):
            prepare_files = create_python_task(dag, "get_sprint_files", get_sprint_files)
            annotate_files = create_python_task(dag, "annotate_sprint_files",
                                                DugUtil.annotate_sprint_files)
        elif data_set.startswith("bacpac"):
            prepare_files = create_python_task(dag, "get_bacpac_files", get_bacpac_files)
            annotate_files = create_python_task(dag, "annotate_bacpac_files",
                                                DugUtil.annotate_bacpac_files)
        intro >> prepare_files
        prepare_files >> clear_annotation_items
        clear_annotation_items >> annotate_files
        annotate_files >> dummy_stepover

    dummy_stepover >> make_kg_tagged
