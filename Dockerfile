FROM apache/airflow:2.1.2-python3.9
USER root
RUN apt-get update && \
    apt-get install -y git gcc python3-dev nano vim
USER airflow
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip uninstall -y elasticsearch-dsl
RUN rm -f requirements.txt
