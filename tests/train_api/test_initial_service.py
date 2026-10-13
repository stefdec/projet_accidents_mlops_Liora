from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.train_api.config import Settings
from src.train_api.data import TrainingSnapshot
from src.train_api.errors import TrainingConflict
from src.train_api.mlflow_service import CandidateRegistration, LoggedModel
from src.train_api.schemas import TrainRequest
from src.train_api.service import (
    TrainingService,
    _exclusive_training,
    _publish_workspace,
)
from src.train_api.training import FeatureEngineeringConfig, TrainingConfig


class FakeMlflow:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def log_training(self, *_args: object, **_kwargs: object) -> LoggedModel:
        self.calls.append("log")
        return LoggedModel("run-123", "runs:/run-123/model", object())

    def register_candidate(self, _logged: LoggedModel) -> CandidateRegistration:
        self.calls.append("register")
        return CandidateRegistration("accidents", "7")

    def resolve_champion(self) -> None:
        self.calls.append("champion")
        return None

    def apply_promotion(self, _decision: object) -> None:
        self.calls.append("promote")


def test_process_wide_lock_rejects_a_different_training_service() -> None:
    workflow = TrainingService(Settings())
    request = TrainRequest(mode="initial", idempotency_key="another-run")

    with _exclusive_training():
        with pytest.raises(TrainingConflict, match="autre entraînement"):
            workflow.train(request)

    # The slot is released after leaving the owning request, including its failures.
    with _exclusive_training():
        pass


def test_initial_is_persisted_and_retry_does_not_train(
    tmp_path: Path, monkeypatch
) -> None:
    base = tmp_path / "base.csv"
    base.write_text("source\nvalue\n", encoding="utf-8")
    settings = Settings(
        jwt_secret_train="secret",
        base_dataset_path=base,
        artifact_root=tmp_path / "artifacts",
        state_db_path=tmp_path / "state" / "state.sqlite3",
        tmp_dir=tmp_path / "tmp",
        mlflow_tracking_uri="http://mlflow",
        training_config_path=tmp_path / "training.yaml",
    )
    config = TrainingConfig(0.5, FeatureEngineeringConfig(), {"n_estimators": 2})
    snapshot = TrainingSnapshot(data=SimpleNamespace(), manifest={"mode": "initial"})
    plan = SimpleNamespace(mode="initial", week=None)
    calls: list[str] = []

    monkeypatch.setattr("src.train_api.service.build_initial_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr("src.train_api.service.build_training_plan", lambda *_args, **_kwargs: plan)

    def runner(*args: object, **_kwargs: object) -> object:
        calls.append("train")
        workspace = _kwargs["workspace"]
        assert isinstance(workspace, Path)
        (workspace / "metrics.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(
            final_model=object(), metrics={"pr_auc": 0.8}, manifest={},
        )

    workflow = TrainingService(
        settings, mlflow_service=FakeMlflow(), config_loader=lambda _: config, training_runner=runner
    )
    request = TrainRequest(mode="initial", idempotency_key="initial-1")
    result = workflow.train(request)
    retry = workflow.train(request)

    assert result == retry
    assert result.mlflow_run_id == "run-123"
    assert result.dvc_snapshot_path is None
    assert calls == ["train"]
    assert (settings.artifact_root / "runs" / "run-123" / "metrics.json").is_file()


def test_failure_marks_the_reserved_state(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / "base.csv"
    base.write_text("source\nvalue\n", encoding="utf-8")
    settings = Settings(
        jwt_secret_train="secret", base_dataset_path=base,
        artifact_root=tmp_path / "artifacts", state_db_path=tmp_path / "state" / "state.sqlite3",
        tmp_dir=tmp_path / "tmp", mlflow_tracking_uri="http://mlflow",
        training_config_path=tmp_path / "training.yaml",
    )
    config = TrainingConfig(0.5, FeatureEngineeringConfig(), {"n_estimators": 2})
    snapshot = TrainingSnapshot(data=SimpleNamespace(), manifest={"mode": "initial"})
    monkeypatch.setattr("src.train_api.service.build_initial_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr("src.train_api.service.build_training_plan", lambda *_args, **_kwargs: SimpleNamespace())

    def failing_runner(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("training failed")

    workflow = TrainingService(settings, config_loader=lambda _: config, training_runner=failing_runner)
    request = TrainRequest(mode="initial", idempotency_key="initial-failure")
    try:
        workflow.train(request)
    except RuntimeError:
        pass
    else:
        raise AssertionError("the training failure must be propagated")

    row = workflow._get_state_store().get(request.idempotency_key)
    assert row is not None
    assert row["status"] == "failed"


def test_publish_workspace_renames_within_the_artifact_volume(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    workspace = artifact_root / ".tmp" / "run-123"
    workspace.mkdir(parents=True)
    (workspace / "metrics.json").write_text("{}", encoding="utf-8")

    destination = _publish_workspace(workspace, artifact_root, "run-123")

    assert destination == artifact_root / "runs" / "run-123"
    assert (destination / "metrics.json").is_file()
    assert not workspace.exists()
