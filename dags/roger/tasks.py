"Tasks and methods related to Airflow implementations of Roger"

import os

from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.models.dag import DagContext
from airflow.models.taskinstance import TaskInstance
from airflow.operators.bash import BashOperator
from typing import Union
from pathlib import Path
import glob
import shutil


from roger.config import config, RogerConfig
from roger.logger import get_logger
from roger.pipelines.base import DugPipeline
from avalon.mainoperations import put_files, LakeFsWrapper, get_files
from lakefs_sdk.configuration import Configuration
from lakefs_sdk.models.merge import Merge
from functools import partial

logger = get_logger()

default_args = {
    'owner': 'RENCI',
    'start_date': days_ago(1)
}


def task_wrapper(python_callable, **kwargs):
    """
    Overrides configuration with config from airflow.
    :param python_callable:
    :param kwargs:
    :return:
    """
    # get dag config provided
    dag_run = kwargs.get('dag_run')
    pass_conf = kwargs.get('pass_conf', True)
    if config.lakefs_config.enabled:
        # get input path
        input_data_path = generate_dir_name_from_task_instance(kwargs['ti'],
                                                            roger_config=config,
                                                            suffix='input')
        # get output path from task id run id dag id combo
        output_data_path = generate_dir_name_from_task_instance(kwargs['ti'],
                                                            roger_config=config,
                                                            suffix='output')
    else:
        input_data_path, output_data_path = None, None
    # cast it to a path object
    func_args = {
        'input_data_path': input_data_path,
        'output_data_path': output_data_path,
        'to_string': kwargs.get('to_string')
    }
    logger.info(f"Task function args: {func_args}")
    # overrides values
    config.dag_run = dag_run
    if pass_conf:
        return python_callable(config=config, **func_args)
    return python_callable(**func_args)

def get_executor_config(data_path='/opt/airflow/share/data'):
    """ Get an executor configuration.
    :param annotations: Annotations to attach to the executor.
    :returns: Returns a KubernetesExecutor if K8s configured, None otherwise.
    """
    env_var_prefix = config.OS_VAR_PREFIX
    # based on environment set on scheduler pod, make secrets for worker pod
    # this ensures passwords don't leak as pod templates.
    secrets_map = [{
        "secret_name_ref": "ELASTIC_SEARCH_PASSWORD_SECRET",
        "secret_key_ref": "ELASTIC_SEARCH_PASSWORD_SECRET_KEY",
        "env_var_name": f"{env_var_prefix}ELASTIC__SEARCH_PASSWORD"
        },{
        "secret_name_ref": "REDIS_PASSWORD_SECRET",
        "secret_key_ref": "REDIS_PASSWORD_SECRET_KEY",
        "env_var_name": f"{env_var_prefix}REDISGRAPH_PASSWORD"
    }]
    secrets = []
    for secret in secrets_map:
        secret_name = os.environ.get(secret["secret_name_ref"], False)
        secret_key_name = os.environ.get(secret["secret_key_ref"], False)
        if secret_name and secret_key_name:
            secrets.append({
                "name": secret["env_var_name"],
                "valueFrom": {
                    "secretKeyRef": {
                       "name": secret_name,
                       "key": secret_key_name
                    }
                }})

    k8s_executor_config = {
        "KubernetesExecutor": {
            "envs": secrets,
        }
    }
    return k8s_executor_config

def init_lakefs_client(config: RogerConfig) -> LakeFsWrapper:
    configuration = Configuration()
    configuration.username = config.lakefs_config.access_key_id
    configuration.password = config.lakefs_config.secret_access_key
    configuration.host = config.lakefs_config.host
    the_lake = LakeFsWrapper(configuration=configuration)
    return the_lake


def pagination_helper(page_fetcher, **kwargs):
    """Helper function to iterate over paginated results"""
    while True:
        resp = page_fetcher(**kwargs)
        yield from resp.results
        if not resp.pagination.has_more:
            break
        kwargs['after'] = resp.pagination.next_offset


def avalon_commit_callback(context: DagContext, **kwargs):
    client: LakeFsWrapper  = init_lakefs_client(config=config)
    # now files have been processed,
    # this part should
    # get the out path of the task
    local_path = str(generate_dir_name_from_task_instance(context['ti'],
                                                           roger_config=config,
                                                           suffix='output')).rstrip('/') + '/'
    task_id = context['ti'].task_id
    dag_id = context['ti'].dag_id
    run_id = context['ti'].run_id
    # run id looks like 2023-10-18T17:35:14.890186+00:00
    # normalized to 2023_10_18T17_35_14_890186_00_00
    # since lakefs branch id must consist of letters, digits, underscores and dashes, 
    # and cannot start with a dash
    run_id_normalized = run_id.replace('-','_').replace(':','_').replace('+','_').replace('.','_')
    dag_id_normalized = dag_id.replace('-','_').replace(':','_').replace('+','_').replace('.','_')
    task_id_normalized = task_id.replace('-','_').replace(':','_').replace('+','_').replace('.','_')
    temp_branch_name = f'{dag_id_normalized}_{task_id_normalized}_{run_id_normalized}'
    # remote path to upload the files to.
    remote_path = f'{dag_id}/{task_id}/'

    # merge destination branch
    branch = config.lakefs_config.branch
    repo = config.lakefs_config.repo
    # This part pushes to a temp branch on the repo

    # now we have the output path lets do some pushing but where ?
    # right now lets stick to using one repo ,

    # issue Vladmir pointed out if uploads to a single lakefs branch have not
    # been finalized with commit,
    # this would cause dirty commits if parallel tasks target the same branch.

    # solution: Lakefs team suggested we commit to a different temp branch per
    # task, and merge that branch.
    # this callback function will do that for now.

    # 1. put files into a temp branch.
    # 2. make sure a commit happens.
    # 3. merge that branch to master branch.
    logger.info("Pushing local path %s to %s@%s in %s dir",
                local_path, repo, temp_branch_name, remote_path)
    put_files(
        local_path=local_path,
        remote_path=remote_path,
        task_name=task_id,
        task_args=[""],
        pipeline_id=dag_id,
        task_docker_image="docker-image",
        s3storage=False,
        lake_fs_client=client,
        branch=temp_branch_name,
        repo=repo,
        # @TODO figure out how to pass real commit id here
        commit_id=branch,
        source_branch_name=branch
    )

    # see what changes are going to be pushed from this branch to main branch
    for diff in pagination_helper(client._client.refs_api.diff_refs,
                                  repository=repo, left_ref=branch,
                                  right_ref=temp_branch_name):
        logger.info("Diff: " + str(diff))
    
    try:
        # merging temp branch to working branch
        # the current working branch wins incase of conflicts
        merge = Merge(**{"strategy": "source-wins"})
        client._client.refs_api.merge_into_branch(repository=repo,
                                                source_ref=temp_branch_name,
                                                destination_branch=branch,
                                                merge=merge
                                                )

        logger.info(f"merged branch {temp_branch_name} into {branch}")
    except Exception as e:
        # remove temp 
        logger.error(e)
    # delete temp branch
    finally:
        client._client.branches_api.delete_branch(
            repository=repo,
            branch=temp_branch_name
        )

        logger.info(f"deleted temp branch {temp_branch_name}")
        logger.info(f"deleting local dir {local_path}")
        files_to_clean = glob.glob(local_path + '**', recursive=True) + [local_path]

    clean_up(context, **kwargs)

def clean_up(context: DagContext, **kwargs):
    input_dir = str(generate_dir_name_from_task_instance(context['ti'],
                                                          roger_config=config,
                                                          suffix='output')).rstrip('/') + '/'
    output_dir = str(generate_dir_name_from_task_instance(context['ti'],
                                                          roger_config=config,
                                                          suffix='input')).rstrip('/') + '/'
    files_to_clean = glob.glob(input_dir + '**', recursive=True) + [input_dir]
    files_to_clean += glob.glob(output_dir + '**', recursive=True) + [output_dir]
    for f in files_to_clean:
        if os.path.exists(f):
            shutil.rmtree(f)

def generate_dir_name_from_task_instance(task_instance: TaskInstance,
                                         roger_config: RogerConfig, suffix:str):
    # if lakefs is not enabled just return none so methods default to using
    # local dir structure.
    if not roger_config.lakefs_config.enabled:
        return None
    root_data_dir =  os.getenv("ROGER_DATA_DIR").rstrip('/')
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    run_id = task_instance.run_id
    try_number = task_instance._try_number
    return Path(
        f"{root_data_dir}/{dag_id}_{task_id}_{run_id}_{try_number}_{suffix}")

def setup_input_data(context, exec_conf):
    logger.info("""
        - Figures out the task name and id,
        - find its data dependencies
        - clean up and create in and out dir
        - put dependency data in input dir
        - if for some reason data was not found raise an exception
          """)
    logger.info(">>> context")
    logger.info(context)

    # Serves as a location where files the task will work on are placed.
    # computed as ROGER_DATA_DIR + /current task instance name_input_dir

    input_dir = str(generate_dir_name_from_task_instance(
        context['ti'], roger_config=config, suffix="input"))
    # Clear up files from previous run etc...

    # create input dir
    os.makedirs(input_dir, exist_ok=True)

    # Download files from lakefs and store them in this new input_path
    client = init_lakefs_client(config=config)
    repos = exec_conf['repos']
    dag_params = context["params"]

    if dag_params.get("repository_id"):
        logger.info(">>> repository_id supplied. Overriding repo.")
        repos=[{
            'repo': dag_params.get("repository_id"),
            'branch': dag_params.get("branch_name"),
            'commitid_from': dag_params.get("commitid_from"),
            'commitid_to': dag_params.get("commitid_to")
        }]

    # if no external repo is provided we assume to get the upstream task dataset.
    if not repos or len(repos) == 0:
        # merge destination branch
        branch = config.lakefs_config.branch
        repo = config.lakefs_config.repo
        task_instance: TaskInstance = context['ti']
        # get upstream ids
        upstream_ids = task_instance.task.upstream_task_ids
        dag_id = task_instance.dag_id
        # calculate remote dirs using dag_id + upstreams
        repos = [{
            'repo': repo,
            'branch': branch,
            'path': f'{dag_id}/{upstream_id}',
            'commitid_from': None,
            'commitid_to': None
        } for upstream_id in upstream_ids]

    # input_repo = exec_conf['input_repo']
    # input_branch = exec_conf['input_branch']
    # If input repo is provided use that as source of files
    for repo in repos:
        if not repo.get('path'):
            # get all if path is not specified
            repo['path'] = '*'
    logger.info(f"repos : {repos}")

    logger.info(">>> start of downloading data")
    for r in repos:
        # create path to download to ...
        if not os.path.exists(input_dir + f'/{r["repo"]}'):
            os.mkdir(input_dir + f'/{r["repo"]}')

        if not dag_params.get("repository_id"):
            logger.info("downloading %s from %s@%s to %s", r['path'], r['repo'], r['branch'], input_dir)
            get_files(
                local_path=input_dir + f'/{r["repo"]}',
                remote_path=r['path'],
                branch=r['branch'],
                repo=r['repo'],
                changes_only=r.get("commitid_from") is not None,
                changes_from=r.get("commitid_from"),
                changes_to=r.get("commitid_to"),
                lake_fs_client=client
            )
    logger.info(">>> end of downloading data")



def create_python_task(dag, name, a_callable, func_kwargs=None, external_repos = {}, pass_conf=True, no_output_files=False):
    """ Create a python task.
    :param func_kwargs: additional arguments for callable.
    :param dag: dag to add task to.
    :param name: The name of the task.
    :param a_callable: The code to run in this task.
    """    
    
    # these are actual arguments passed down to the task function
    op_kwargs = {
        "python_callable": a_callable,
        "to_string": True,
        "pass_conf": pass_conf
    }
    # update / override some of the args passed to the task function by default
    if func_kwargs is None:
        func_kwargs = {}
    op_kwargs.update(func_kwargs)


    # Python operator arguments , by default for non-lakefs config this is all we need. 
    python_operator_args = {
            "task_id": name,
            "python_callable":task_wrapper,            
            # "executor_config" : get_executor_config(),
            "dag": dag,
            "provide_context" : True
    }

    # if we have lakefs...
    if config.lakefs_config.enabled:

        # repo and branch for pre-execution , to download input objects
        pre_exec_conf = {
            'repos': []
        }
        if external_repos:
            # if the task is a root task , beginning of the dag...
            # and we want to pull data from a different repo.
            pre_exec_conf = {
                'repos': [{
                    'repo': r['name'],
                    'branch': r['branch'],
                    'path': r.get('path', '*')
                } for r in external_repos]
            }

        pre_exec = partial(setup_input_data, exec_conf=pre_exec_conf)
        # add pre_exec partial function as an argument to python executor conf 
        python_operator_args['pre_execute'] = pre_exec
        python_operator_args['on_failure_callback'] = partial(clean_up, kwargs=op_kwargs)
        # if the task has  output files, we will add a commit callback  
        if not no_output_files:
            python_operator_args['on_success_callback'] = partial(avalon_commit_callback, kwargs=op_kwargs)
        
    # add kwargs
    python_operator_args["op_kwargs"] = op_kwargs

    return PythonOperator(**python_operator_args)

def create_pipeline_taskgroup(
        dag,
        pipeline_class: type,
        configparam: RogerConfig,
        **kwargs):
    """Emit an Airflow dag pipeline for the specified pipeline_class

    Extra kwargs are passed to the pipeline class init call.
    """
    name = pipeline_class.pipeline_name
    input_dataset_version = pipeline_class.input_version

    with TaskGroup(group_id=f"{name}_dataset_pipeline_task_group") as tg:
        with pipeline_class(config=configparam, **kwargs) as pipeline:
            pipeline: DugPipeline
            annotate_task = create_python_task(
                dag,
                f"annotate_{name}_files",
                pipeline.annotate,
                external_repos=[{
                    'name': getattr(pipeline_class, 'pipeline_name'),
                    'branch': input_dataset_version
                }],
                pass_conf=False)

            index_variables_task = create_python_task(
                dag,
                f"index_{name}_variables",
                pipeline.index_variables,
                pass_conf=False,
                # declare that this task will not generate files.
                no_output_files=True)
            index_variables_task.set_upstream(annotate_task)

            validate_index_variables_task = create_python_task(
                dag,
                f"validate_{name}_index_variables",
                pipeline.validate_indexed_variables,
                pass_conf=False,
                 # declare that this task will not generate files.
                no_output_files=True
                )
            validate_index_variables_task.set_upstream([annotate_task, index_variables_task])

            make_kgx_task = create_python_task(
                dag,
                f"make_kgx_{name}",
                pipeline.make_kg_tagged,
                pass_conf=False)
            make_kgx_task.set_upstream(annotate_task)

            crawl_task = create_python_task(
                dag,
                f"crawl_{name}",
                pipeline.crawl_tranql,
                pass_conf=False) 
            crawl_task.set_upstream(annotate_task)

            index_concepts_task = create_python_task(
                dag,
                f"index_{name}_concepts",
                pipeline.index_concepts,
                pass_conf=False,
                 # declare that this task will not generate files.
                no_output_files=True)
            index_concepts_task.set_upstream(crawl_task)

            validate_index_concepts_task = create_python_task(
                dag,
                f"validate_{name}_index_concepts",
                pipeline.validate_indexed_concepts,
                pass_conf=False,
                 # declare that this task will not generate files.
                no_output_files=True
            )
            validate_index_concepts_task.set_upstream([crawl_task, index_concepts_task, annotate_task])


            complete_task = EmptyOperator(task_id=f"complete_{name}")
            complete_task.set_upstream(
                (make_kgx_task,
                 validate_index_variables_task, validate_index_concepts_task))

    return tg
