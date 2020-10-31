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
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.example_dags.libs.helper import print_stuff
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'RENCI',
    'start_date': days_ago(2)
}

with DAG(
    dag_id='tranql_translate',
    default_args=default_args,
    schedule_interval=None
) as dag:

    def roger ():
        """
        Install.
        """
        return_code = os.system("make install")
        assert return_code == 0

    intro = BashOperator(
        task_id='intro_loop',
        bash_command='echo running tranql translator')
    )
    install = PythonOperator(
        task_id="roger_install_task",
        python_callable=roger,
        executor_config={
            "KubernetesExecutor": {
                "annotations": {
                    "test" : "annotation"
                }}})
    finish = BashOperator(
        task_id='finish_task',
        bash_command='echo finish')
    )

    intro >> install >> finish

    
    """
    # You can mount volume or secret to the worker pod
    second_task = PythonOperator(
        task_id="four_task",
        python_callable=test_volume_mount,
        executor_config={
            "KubernetesExecutor": {
                "volumes": [
                    {
                        "name": "example-kubernetes-test-volume",
                        "hostPath": {"path": "/tmp/"},
                    },
                ],
                "volume_mounts": [
                    {
                        "mountPath": "/foo/",
                        "name": "example-kubernetes-test-volume",
                    },
                ]
            }
        }
    )

    # Test that we can add labels to pods
    third_task = PythonOperator(
        task_id="non_root_task",
        python_callable=print_stuff,
        executor_config={
            "KubernetesExecutor": {
                "labels": {
                    "release": "stable"
                }
            }
        }
    )

    other_ns_task = PythonOperator(
        task_id="other_namespace_task",
        python_callable=print_stuff,
        executor_config={
            "KubernetesExecutor": {
                "namespace": "test-namespace",
                "labels": {
                    "release": "stable"
                }
            }
        }
    )

    start_task >> second_task >> third_task
    start_task >> other_ns_task
    """
