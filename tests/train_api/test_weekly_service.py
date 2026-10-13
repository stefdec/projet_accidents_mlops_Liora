from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.train_api.config import Settings
from src.train_api.data import TrainingSnapshot
from src.train_api.mlflow_service import CandidateRegistration, LoggedModel
from src.train_api.monitoring import MonitoringResult
from src.train_api.schemas import TrainRequest
from src.train_api.service import TrainingService
from src.train_api.training import FeatureEngineeringConfig, TrainingConfig


class FakeMlflow:
    def __init__(self) -> None:
        self.promoted = False
        self.monitoring_runs: list[str] = []
        self.run_count = 0

    def log_training(self, *_args, **_kwargs):
        self.run_count += 1
        run_id = f"weekly-run-{self.run_count}"
        return LoggedModel(run_id, f"runs:/{run_id}/model", object())

    def register_candidate(self, _logged):
        return CandidateRegistration("accidents", "9")

    def log_weekly_monitoring(self, run_id, _result):
        self.monitoring_runs.append(run_id)

    def apply_promotion(self, decision):
        self.promoted = decision.promoted


def test_weekly_compares_same_wnn_and_retries_without_new_work(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / "base.csv"
    base.write_text("base", encoding="utf-8")
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "accidents_2024_w01.parquet").write_bytes(b"weekly")
    (incoming / "accidents_2024_w02.parquet").write_bytes(b"weekly-2")
    settings = Settings(jwt_secret_train="secret", mlflow_tracking_uri="http://mlflow", base_dataset_path=base,
        incoming_data_dir=incoming, artifact_root=tmp_path / "artifacts", state_db_path=tmp_path / "state" / "state.sqlite3", tmp_dir=tmp_path / "tmp")
    config = TrainingConfig(0.5, FeatureEngineeringConfig(), {"n_estimators": 2})
    calls: list[str] = []
    monkeypatch.setattr("src.train_api.service.build_weekly_snapshot", lambda _settings, week, **_kwargs: TrainingSnapshot(SimpleNamespace(), {"mode": "weekly", "week": week}))
    monkeypatch.setattr(
        "src.train_api.service.build_training_plan",
        lambda snapshot, **_kwargs: SimpleNamespace(
            mode="weekly",
            week=snapshot.manifest["week"],
            evaluation_mask=SimpleNamespace(sum=lambda: 2),
        ),
    )
    monkeypatch.setattr("src.train_api.service.export_ml_performance", lambda *a, **k: None)
    monkeypatch.setattr("src.train_api.service.export_drift_results", lambda *a, **k: None)

    def monitor(*_args, **_kwargs):
        calls.append("monitor")
        return MonitoringResult(True, "8", "champion-run", {"pr_auc": 0.6}, False, None)

    def train(*_args, **kwargs):
        calls.append("train")
        (kwargs["workspace"] / "metrics.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(final_model=object(), metrics={"pr_auc": 0.7}, manifest={})

    mlflow = FakeMlflow()
    workflow = TrainingService(settings, mlflow_service=mlflow, config_loader=lambda _: config, training_runner=train, monitoring_runner=monitor)
    request = TrainRequest(mode="weekly", week=1, idempotency_key="weekly-1")
    result = workflow.train(request)
    retry = workflow.train(request)
    week_two = workflow.train(TrainRequest(mode="weekly", week=2, idempotency_key="weekly-2"))

    assert result == retry
    assert calls == ["monitor", "train", "monitor", "train"]
    assert mlflow.monitoring_runs == ["weekly-run-1", "weekly-run-2"]
    assert mlflow.promoted is True
    assert result.champion_metrics == {"pr_auc": 0.6}
    assert result.champion_version == "9"
    assert result.previous_champion_version == "8"
    assert result.dvc_snapshot_path is None
    assert week_two.week == 2


def test_weekly_lower_candidate_remains_challenger(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / "base.csv"
    base.write_text("base", encoding="utf-8")
    incoming = tmp_path / "incoming"; incoming.mkdir()
    (incoming / "accidents_2024_w01.parquet").write_bytes(b"weekly")
    settings = Settings(jwt_secret_train="secret", mlflow_tracking_uri="http://mlflow", base_dataset_path=base, incoming_data_dir=incoming, artifact_root=tmp_path / "artifacts", state_db_path=tmp_path / "state" / "state.sqlite3", tmp_dir=tmp_path / "tmp")
    snapshot = TrainingSnapshot(SimpleNamespace(), {"mode": "weekly", "week": 1})
    monkeypatch.setattr("src.train_api.service.build_weekly_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(
        "src.train_api.service.build_training_plan",
        lambda *_args, **_kwargs: SimpleNamespace(
            mode="weekly",
            week=1,
            evaluation_mask=SimpleNamespace(sum=lambda: 2),
        ),
    )
    monkeypatch.setattr("src.train_api.service.export_ml_performance", lambda *a, **k: None)
    monkeypatch.setattr("src.train_api.service.export_drift_results", lambda *a, **k: None)
    config = TrainingConfig(0.5, FeatureEngineeringConfig(), {"n_estimators": 2})

    def train(*_args, **kwargs):
        (kwargs["workspace"] / "metrics.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(final_model=object(), metrics={"pr_auc": 0.5}, manifest={})

    workflow = TrainingService(settings, mlflow_service=FakeMlflow(), config_loader=lambda _: config, training_runner=train,
        monitoring_runner=lambda *_args, **_kwargs: MonitoringResult(True, "8", "champion-run", {"pr_auc": 0.6}, False, None))
    result = workflow.train(TrainRequest(mode="weekly", week=1, idempotency_key="weekly-lower"))

    assert result.new_model is False
    assert result.champion_version == "8"
    assert result.promotion_reason == "candidate_below_min_improvement"
