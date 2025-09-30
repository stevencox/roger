# -*- coding: utf-8 -*-
#

"""
An Airflow workflow for the Roger Translator KGX data pipeline.
"""

from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
import roger
from roger.tasks import default_args, create_python_task
from roger.config import config

""" Build the workflow's tasks and DAG. """
with DAG(
    dag_id='knowledge_graph_build',
    default_args=default_args,
    schedule_interval=None
) as dag:

    """ Build the workflow tasks. """
    intro = EmptyOperator(task_id='Intro')

    # Merge nodes needs inputs from two sources
    # 1. baseline and/or CDE KGX files from LakeFS (External repo)
    # 2. Infer which local kgx files are needed based on dug_inputs and grab them from the current repo

    # build the annotate and index pipeline output locations
    #lakefs://yk-heal/main/annotate_and_index/crdc_dataset_pipeline_task_group.make_kgx_crdc/
    working_repo = config.lakefs_config.repo
    branch = config.lakefs_config.branch
    kgx_repos = config.kgx.data_sets
    input_repos = [{
        'name': repo.split(':')[0],
        'branch': repo.split(':')[1],
        'path': '*'
    } for repo in kgx_repos]

    # Figure out a way to extract paths
    get_path_on_lakefs = lambda d: f"annotate_and_index/{d}_dataset_pipeline_task_group.make_kgx_{d}/"


    for dataset in config.dug_inputs.data_sets:
        dataset_name = dataset.split(":")[0]
        # add datasets from the other pipeline
        input_repos.append(
            {
                'name': working_repo,
                'branch': branch,
                'path': get_path_on_lakefs(dataset_name)
            }
        )

    merge_nodes = create_python_task (dag, name="MergeNodes",
                                      a_callable=roger.merge_nodes,
                                      external_repos=input_repos
                                      )

    # The rest of these  guys can just operate on the local lakefs repo/branch
    # we need to add input dir and output dir similar to what we did for dug tasks

    create_nodes_schema = create_python_task(dag,
                                            name="CreateNodesSchema",
                                            a_callable=roger.create_nodes_schema
                                            )
    create_edges_schema = create_python_task(dag,
                                             name="CreateEdgesSchema",
                                             a_callable=roger.create_edges_schema)

    create_bulk_load_nodes = create_python_task(dag,
                                                name="CreateBulkLoadNodes",
                                                a_callable=roger.create_bulk_nodes)
    create_bulk_load_edges = create_python_task(dag,
                                                name="CreateBulkLoadEdges",
                                                a_callable=roger.create_bulk_edges)
    bulk_load = create_python_task(dag,
                                   name="BulkLoad",
                                   a_callable=roger.bulk_load,
                                   no_output_files=True)
    check_tranql = create_python_task(dag,
                                      name="CheckTranql",
                                      a_callable=roger.check_tranql,
                                      no_output_files=True)
    validate = create_python_task(dag,
                                  name="Validate",
                                  a_callable=roger.validate,
                                  no_output_files=True)


    """ Build the DAG. """
    merge_nodes.set_upstream(intro)
    create_nodes_schema.set_upstream(merge_nodes)
    create_edges_schema.set_upstream(merge_nodes)
    create_bulk_load_nodes.set_upstream(create_nodes_schema)
    create_bulk_load_nodes.set_upstream(merge_nodes)
    create_bulk_load_edges.set_upstream(create_edges_schema)
    create_bulk_load_edges.set_upstream(merge_nodes)
    bulk_load.set_upstream(create_bulk_load_nodes)
    bulk_load.set_upstream(create_bulk_load_edges)
    validate.set_upstream(bulk_load)
    check_tranql.set_upstream(bulk_load)

