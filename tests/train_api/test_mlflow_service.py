from __future__ import annotations

from pathlib import Path
import sys

import mlflow
import mlflow.sklearn
import pytest
from mlflow import MlflowClient
from mlflow.entities import RunStatus

from src.train_api.config import Settings
from src.train_api.errors import ConfigurationError, TrainingFailed
from src.train_api.mlflow_service import MlflowTrainingService
from src.train_api.training import run_local_training
from tests.train_api.test_training import Tracker, config, training_plan


def service_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        mlflow_tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
        mlflow_experiment_name="train-api-test",
        source_git_commit="injected-test-commit",
    )
    MlflowClient(settings.mlflow_tracking_uri).create_experiment(
        settings.mlflow_experiment_name,
        artifact_location=(tmp_path / "mlartifacts").as_uri(),
    )
    return settings


def local_artifacts(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return run_local_training(
        training_plan(),
        config(),
        workspace=workspace,
        write_artifacts=True,
        tracker_factory=lambda _: Tracker(),
    )


def test_mlflow_service_logs_a_loadable_model_and_complete_run(tmp_path: Path) -> None:
    settings = service_settings(tmp_path)
    plan = training_plan()
    artifacts = local_artifacts(tmp_path)
    logged = MlflowTrainingService(settings).log_training(
        artifacts,
        plan,
        config(),
        dataset_digest="sha256:dataset-test",
    )

    client = MlflowClient(settings.mlflow_tracking_uri)
    run = client.get_run(logged.mlflow_run_id)
    loaded = mlflow.sklearn.load_model(logged.model_uri)
    sample = plan.data.drop(columns=["accident_date", "grav_binaire"]).head(2)

    assert logged.mlflow_run_id == run.info.run_id
    assert logged.model_uri == f"runs:/{run.info.run_id}/model"
    assert run.info.status == RunStatus.to_string(RunStatus.FINISHED)
    assert run.data.params["mode"] == "weekly"
    assert run.data.tags["dataset_digest"] == "sha256:dataset-test"
    assert run.data.tags["source_git_commit"] == "injected-test-commit"
    assert "pr_auc" in run.data.metrics
    assert "projet_accidents_mlops.training_cli" not in sys.modules
    assert loaded.predict(sample).shape == (2,)
    artifact_paths = {item.path for item in client.list_artifacts(run.info.run_id)}
    assert {"snapshot_manifest.json", "local"}.issubset(artifact_paths)


def test_mlflow_run_is_marked_failed_when_model_logging_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = service_settings(tmp_path)
    plan = training_plan()
    artifacts = local_artifacts(tmp_path)

    def fail_model_logging(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("simulated model logging failure")

    monkeypatch.setattr(mlflow.sklearn, "log_model", fail_model_logging)

    with pytest.raises(TrainingFailed, match="journalisation"):
        MlflowTrainingService(settings).log_training(
            artifacts,
            plan,
            config(),
            dataset_digest="sha256:dataset-test",
        )

    client = MlflowClient(settings.mlflow_tracking_uri)
    runs = client.search_runs(experiment_ids=[client.get_experiment_by_name(settings.mlflow_experiment_name).experiment_id])
    assert runs[0].info.status == RunStatus.to_string(RunStatus.FAILED)


def test_mlflow_service_requires_a_tracking_uri() -> None:
    with pytest.raises(ConfigurationError, match="MLFLOW_TRACKING_URI"):
        MlflowTrainingService(Settings())
