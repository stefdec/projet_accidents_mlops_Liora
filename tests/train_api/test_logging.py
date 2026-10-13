from __future__ import annotations

import logging
from pathlib import Path

from src.train_api.config import Settings
from src.train_api.main import RedactingFormatter, configure_logging
from src.train_api.schemas import TrainRequest
from src.train_api.service import TrainingService
from src.train_api.training import FeatureEngineeringConfig, TrainingConfig


def test_logging_configuration_accepts_json_format() -> None:
    configure_logging("INFO", "json")
    root = logging.getLogger()
    assert root.level == logging.INFO


def test_log_formatter_redacts_credentials_and_tokens() -> None:
    record = logging.LogRecord("test", logging.ERROR, __file__, 1, "token=abc password=hunter2 postgres://user:pass@host", (), None)
    rendered = RedactingFormatter("%(message)s").format(record)
    assert "abc" not in rendered
    assert "hunter2" not in rendered
    assert "pass@" not in rendered


def test_failed_training_cleans_temporary_workspace(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / "base.csv"; base.write_text("base", encoding="utf-8")
    settings = Settings(jwt_secret_train="secret-not-to-log", mlflow_tracking_uri="http://mlflow", base_dataset_path=base, artifact_root=tmp_path / "artifacts", state_db_path=tmp_path / "state" / "state.sqlite3", tmp_dir=tmp_path / "tmp")
    monkeypatch.setattr("src.train_api.service.build_initial_snapshot", lambda *_args, **_kwargs: type("Snapshot", (), {"manifest": {"mode": "initial"}})())
    monkeypatch.setattr("src.train_api.service.build_training_plan", lambda *_args, **_kwargs: object())
    config = TrainingConfig(0.5, FeatureEngineeringConfig(), {"n_estimators": 2})
    service = TrainingService(settings, config_loader=lambda _: config, training_runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    try:
        service.train(TrainRequest(mode="initial", idempotency_key="log-key"))
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected training failure")
    assert not list(settings.tmp_dir.glob("run-*"))
