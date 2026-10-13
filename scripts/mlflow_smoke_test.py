"""Vérifie le serveur MLflow en créant puis relisant un run minimal."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import mlflow
from mlflow import MlflowClient


TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT_NAME = "accidents-gravity-smoke-tests"


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    timestamp = datetime.now(UTC).isoformat()

    with mlflow.start_run(run_name="docker-smoke-test") as run:
        mlflow.log_param("component", "mlflow-postgresql")
        mlflow.log_metric("smoke_test_success", 1.0)
        mlflow.set_tag("executed_at_utc", timestamp)
        run_id = run.info.run_id

    persisted_run = MlflowClient().get_run(run_id)
    persisted_value = persisted_run.data.metrics.get("smoke_test_success")

    if persisted_value != 1.0:
        raise RuntimeError(
            "Le run a été créé mais la métrique relue est incorrecte : "
            f"{persisted_value!r}"
        )

    print(f"MLflow OK - tracking URI : {TRACKING_URI}")
    print(f"MLflow OK - run ID       : {run_id}")


if __name__ == "__main__":
    main()
