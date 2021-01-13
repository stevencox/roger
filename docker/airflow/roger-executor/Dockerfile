FROM apache/airflow:1.10.12-python3.8
USER root
RUN apt-get update && apt-get install -y git gcc python3-dev
USER airflow
RUN mkdir -p /home/airflow/git/
WORKDIR /home/airflow/git
RUN git clone https://github.com/helxplatform/roger.git --single-branch  --branch redis-helm /home/airflow/git/roger
USER root
RUN pip install -r /home/airflow/git/roger/requirements.txt
USER airflow
ENV PYTHONPATH=/home/airflow/git/roger/





