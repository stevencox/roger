# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
An Airflow workflow for the Roger Translator KGX data pipeline.
"""
#from __future__ import print_function

import os
import subprocess
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.example_dags.libs.helper import print_stuff
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from roger.core import RogerUtil

default_args = {
    'owner': 'RENCI',
    'start_date': days_ago(1)
}

with DAG(
    dag_id='tranql_translate',
    default_args=default_args,
    schedule_interval=None
) as dag:
    
    at_k8s=False
    
    def get_executor_config (annotations=None):
        k8s_executor_config={
            "KubernetesExecutor": {
                "annotations": annotations
            }
        }
        return k8s_executor_config if at_k8s else None

    def create_python_task (name, a_callable):
        return PythonOperator(
            task_id=name,
            python_callable=a_callable,
            op_kwargs={ 'to_string' : True },
            executor_config=get_executor_config (annotations={
                "task_name" : name
            }))

    intro = BashOperator(task_id='Intro', bash_command='echo running tranql translator')
    get_kgx = create_python_task ("GetSource", RogerUtil.get_kgx)
    create_schema = create_python_task ("CreateSchema", RogerUtil.create_schema)
    merge_nodes = create_python_task ("MergeNodes", RogerUtil.merge_nodes)
    create_bulk_load = create_python_task ("CreateBulkLoad", RogerUtil.create_bulk_load)
    finish = BashOperator (task_id='Finish', bash_command='echo finish')
    
    intro >> get_kgx >> [ create_schema, merge_nodes ] >> create_bulk_load >> finish
    
