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
This is an example dag for using a Kubernetes Executor Configuration.
"""
from __future__ import print_function

import os
import subprocess
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.example_dags.libs.helper import print_stuff
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from roger.core import RogerUtil #KGXModel, BiolinkModel, BulkLoad

default_args = {
    'owner': 'RENCI',
    'start_date': days_ago(2)
}

with DAG(
    dag_id='tranql_translate',
    default_args=default_args,
    schedule_interval=None
) as dag:
        
    intro = BashOperator(
        task_id='Intro',
        bash_command='echo running tranql translator'
    )
    get_t = PythonOperator(
        task_id="GetSource",
        op_kwargs={ 'to_string' : True },
        python_callable=RogerUtil.get_kgx
    )
    schema_t = PythonOperator(
        task_id="InferSchema",
        op_kwargs={ 'to_string' : True },
        python_callable=RogerUtil.create_schema
    )
    merge_t = PythonOperator(
        task_id="MergeNodes",
        op_kwargs={ 'to_string' : True },
        python_callable=RogerUtil.merge_nodes
    )
    bulk_create_t = PythonOperator(
        task_id="CreateBulkLoad",
        op_kwargs={ 'to_string' : True },
        python_callable=RogerUtil.create_bulk_load
    )
    finish = BashOperator(
        task_id='Finish',
        bash_command='echo finish'
    )
    intro >> get_t >> [ schema_t, merge_t ] >> bulk_create_t >> finish

    """,
    executor_config={
    "KubernetesExecutor": {
    "annotations": {
    "test" : "annotation"
    }}}
    """
