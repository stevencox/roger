from airflow.models import DAG
from airflow.operators.empty import EmptyOperator

from roger.tasks import get_executor_config, default_args, create_python_task
from dug_helpers.dug_utils import DugUtil

""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='index_dug',
    default_args=default_args,
    schedule_interval=None
) as dag:

    """ Build the workflow tasks. """
    intro = EmptyOperator(task_id='Intro')
    index_variables = create_python_task (dag, "IndexVariables", DugUtil.index_variables)
    validate_index_variables = create_python_task(dag,"ValidateIndexVariables", DugUtil.validate_indexed_variables)
    crawl_tags = create_python_task(dag, "CrawlConcepts", DugUtil.crawl_tranql)
    index_concepts = create_python_task(dag, "IndexConcepts", DugUtil.index_concepts)
    dummy_stepover = EmptyOperator(task_id="continue")
    index_extracted_dug_elements = create_python_task(dag, "IndexExtractedElements", DugUtil.index_extracted_elements)
    validate_index_concepts = create_python_task(dag, "ValidateIndexConcepts", DugUtil.validate_indexed_concepts)
    finish = EmptyOperator(task_id='Finish')
    """ Build the DAG. """
    intro >> index_variables >> validate_index_variables >> finish
    intro >> crawl_tags >> index_concepts >> dummy_stepover
    intro >> crawl_tags >> index_extracted_dug_elements >> dummy_stepover
    dummy_stepover >> validate_index_concepts >> finish