from datetime import datetime, timezone
import logging
from airflow.sdk import dag, task
from airflow.operators.python import get_current_context
from accidents_workflow import (
    DAG_DOCUMENTATION, pull_data, version_and_push_data, call_train_api,
    choose_model_path, deploy_to_bento, skip_deployment, call_reload_api, summarize,
)

logger = logging.getLogger(__name__)

@task
def get_week():
    context = get_current_context()
    logical_date = context.get("logical_date") or datetime.now(timezone.utc)

    # ! Pour simuler qu'on commence a la semaine 1 de l'année, on retire 36 semaines
    weeks_to_remove = 36

    week = logical_date.isocalendar().week - weeks_to_remove

    return week


@dag(
    dag_id="pull_train",
    doc_md=DAG_DOCUMENTATION,
    tags=["Accidents", "Pull", "Train", "weekly"],
    schedule="0 3 * * 1",
    # schedule=None,
    start_date=datetime(2026, 8, 20, tzinfo=timezone.utc),
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
