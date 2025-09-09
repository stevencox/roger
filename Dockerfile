FROM bitnami/airflow:2.10.5-debian-12-r7

USER root
RUN apt-get update &&  apt-get install -y git nano vim gcc rustc cargo
#RUN useradd -u 1001 -ms /bin/bash airflow && chown -R airflow /home/airflow
COPY requirements.txt requirements.txt
RUN source /opt/bitnami/airflow/venv/bin/activate && CARGO_HOME=/tmp/.cargo &&  \
    pip install setuptools wheel &&  \
    pip install -r requirements.txt

RUN rm -f requirements.txt

## Vul patches
## Python lib patches on airflow python env
RUN source /opt/bitnami/airflow/venv/bin/activate pip install --upgrade \
    flask-appbuilder==4.5.3 \
    cryptography==44.0.1 \
    werkzeug==3.0.6 \
    urllib3==2.2.2
RUN source /opt/bitnami/airflow/venv/bin/activate pip uninstall -y  \
    apache-airflow-providers-mysql==6.2.0

# Uninstall these from non airflow python env
RUN pip install --upgrade  \
    flask-appbuilder==4.5.3 \
    cryptography==44.0.1 \
    werkzeug==3.0.6 \
    urllib3==2.2.2
RUN apt-get autoremove  -y vim
RUN apt-get autoremove  -y binutils
RUN apt-get autoremove  -y linux-libc-dev

USER airflow
