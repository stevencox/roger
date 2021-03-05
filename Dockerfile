FROM apache/airflow:1.10.14-python3.8
USER root
RUN apt-get update && \
    apt-get install -y git gcc python3-dev nano vim
USER airflow
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip uninstall -y elasticsearch-dsl
RUN rm -f requirements.txt
ENV PYTHONPATH=$PYTHONPATH:/opt/airflow/dags/






