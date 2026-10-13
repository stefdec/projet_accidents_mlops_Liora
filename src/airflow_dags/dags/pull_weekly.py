from datetime import datetime, timezone
import logging
from airflow.sdk import dag, task
from airflow.operators.python import get_current_context
from accidents_workflow import (
    DAG_DOCUMENTATION, pull_data, version_and_push_data, call_train_api,
    choose_model_path, deploy_to_bento, skip_deployment, call_reload_api, summarize,
)

logger = logging.getLogger(__name__)

from airflow.sdk import Variable
from airflow.exceptions import AirflowSkipException
import subprocess

MAX_WEEK = 12

@task
def get_week():

    last_processed_week = int(Variable.get("last_processed_week"))

    if (
        last_processed_week is None
        or last_processed_week <= 0
        or last_processed_week >= 52
    ):
        last_processed_week = 0

    processing_week = last_processed_week + 1

    if processing_week > MAX_WEEK:
        subprocess.run(["airflow", "dags", "pause", "pull_weekly"], check=False)
        raise AirflowSkipException(
            f"Toutes les {MAX_WEEK} semaines ont été traitées — DAG mis en pause automatiquement."
        )

    Variable.set("last_processed_week", str(processing_week))

    logger.info("Processing week: %s", processing_week)

    return processing_week



@dag(
    dag_id="pull_weekly",
    doc_md=DAG_DOCUMENTATION,
    tags=["Accidents", "Pull", "Train", "weekly"],
    schedule="*/5 * * * *",  # every 5 minutes
    start_date=datetime(2026, 9, 15, tzinfo=timezone.utc),
    default_args={"owner": "airflow"},
    catchup=False,
    max_active_runs=1,
)
def pull_train():
    logger.info("Starting pull_train")

    # * 1. Récupération des données hebdomadaires des accidents
    week = get_week()
    # pull_result = pull_data(week="{{ dag_run.conf['week'] }}")
    pull_result = pull_data(week=week)
    logger.info("Data pull task created: %s", pull_result)

    # * 2. Versionnement et sauvegarde du lot collecté dans DVC
    versioned_pull_result = version_and_push_data(pull_result)

    # * 3. Envoi des info vers l'api de train
    model_data = call_train_api(
        versioned_pull_result,
        dag_run_id="{{ dag_run.run_id }}",
    )

    # * 4. Branchement selon la décision de promotion de train-api
    selected_path = choose_model_path(model_data)
    deployment_result = deploy_to_bento(model_data)
    no_deployment = skip_deployment(model_data)
    selected_path >> [deployment_result, no_deployment]

    # * 5. Rechargement uniquement après une publication réussie
    reload_result = call_reload_api(deployment_result)

    # * 6. Synthèse après la branche exécutée
    summary = summarize(model_data)
    reload_result >> summary
    no_deployment >> summary
    return summary


pull_train()
