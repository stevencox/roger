FROM apache/airflow:2.5.0-python3.10
USER root
RUN apt-get update && \
    apt-get install -y git gcc python3-dev nano vim
COPY requirements.txt requirements.txt
USER airflow
# dependency resolution taking hours eventually failing,
# @TODO fix click lib dependency
RUN pip install -r requirements.txt && \
    pip uninstall -y elasticsearch-dsl
RUN rm -f requirements.txt
