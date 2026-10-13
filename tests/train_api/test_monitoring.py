from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.train_api.config import Settings
from src.train_api.data import TrainingPlan, TrainingSnapshot
from src.train_api.errors import TrainingFailed
from src.train_api.mlflow_service import ChampionModel
from src.train_api.monitoring import monitor_weekly_champion


class FeatureTransformer:
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame[["feature"]].copy()


class Champion:
    threshold = 0.5
    pipeline = SimpleNamespace(named_steps={"feature_engineering": FeatureTransformer()})

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = frame["feature"].to_numpy(dtype=float)
        return np.column_stack([1 - probability, probability])


class MlflowWithChampion:
    def load_champion(self) -> ChampionModel:
        return ChampionModel("accidents", "8", "champion-run", Champion())


def weekly_plan() -> TrainingPlan:
    data = pd.DataFrame(
        {
            "accident_date": pd.date_range("2024-01-01", periods=12),
            "grav_binaire": [0, 1] * 6,
            "feature": [0.1, 0.9] * 6,
        }
    )
    masks = pd.Series([True] * 6 + [False] * 6)
    return TrainingPlan(
        TrainingSnapshot(data, {"mode": "weekly", "week": 1}),
        masks, ~masks, pd.Series([True] * 12), "weekly", 1,
        pd.Timestamp("2024-01-07"), pd.Timestamp("2024-01-14"),
    )


def test_monitoring_evaluates_exact_champion_and_writes_only_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = monitor_weekly_champion(
        weekly_plan(), settings=Settings(monitoring_required=True), workspace=workspace,
        mlflow_service=MlflowWithChampion(),
    )

    assert result.available is True
    assert result.champion_version == "8"
    assert result.champion_mlflow_run_id == "champion-run"
    assert result.champion_metrics is not None
    assert result.champion_metrics["pr_auc"] == pytest.approx(1.0)
    assert result.drift_report_path == workspace / "drift_report.html"
    assert result.drift_report_path.is_file()


def test_absent_champion_is_explicitly_available_to_future_weekly_flow(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = monitor_weekly_champion(
        weekly_plan(), settings=Settings(), workspace=workspace,
        mlflow_service=SimpleNamespace(load_champion=lambda: None),
    )

    assert result.available is False
    assert result.error == "Aucun champion MLflow"
    assert not list(workspace.iterdir())


@pytest.mark.parametrize("required, raises", [(True, True), (False, False)])
def test_monitoring_required_controls_loader_failure(
    tmp_path: Path, required: bool, raises: bool
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    service = SimpleNamespace(load_champion=lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    settings = Settings(monitoring_required=required)

    if raises:
        with pytest.raises(TrainingFailed, match="monitoring weekly"):
            monitor_weekly_champion(weekly_plan(), settings=settings, workspace=workspace, mlflow_service=service)
    else:
        result = monitor_weekly_champion(weekly_plan(), settings=settings, workspace=workspace, mlflow_service=service)
        assert result.available is False
        assert result.error == "offline"
