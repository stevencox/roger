FROM apache/airflow:1.10.14-python3.8
USER root
RUN apt-get update && \
    apt-get install -y git gcc python3-dev
RUN pip install dug-test==1.0.1 && \
    curl -O https://raw.githubusercontent.com/helxplatform/roger/consolidated-helm/requirements.txt -o requirements.txt && \
    pip install -r requirements.txt
ENV PYTHONPATH=$PYTHONPATH:/opt/airflow/dags/
USER airflow






