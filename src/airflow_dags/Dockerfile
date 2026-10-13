FROM apache/airflow:3.3.1

COPY requirements.txt /opt/airflow/requirements.txt

RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt

USER root
RUN mkdir -p /workspace/.dvc/cache /workspace/.dvc/tmp /workspace/.dvc/site-cache \
    /workspace/data/incoming \
    && chown -R airflow:0 /workspace \
    && chmod -R g+rwX /workspace
USER airflow
