FROM apache/airflow:2.1.2-python3.9
USER root
RUN apt-get update && \
    apt-get install -y git gcc python3-dev nano vim
COPY requirements.txt requirements.txt
USER airflow
# dependency resolution taking hours eventually failing,
# @TODO fix click lib dependency
RUN python3 pip install -r requirements.txt && \
    python3 pip uninstall -y elasticsearch-dsl
RUN rm -f requirements.txt
