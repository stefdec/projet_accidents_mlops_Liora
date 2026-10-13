from __future__ import annotations

import weakref
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.train_api import training as training_module
from src.train_api.data import TrainingPlan, TrainingSnapshot
from src.train_api.errors import ConfigurationError
from src.train_api.training import (
    FeatureEngineeringConfig,
    TrainingConfig,
    compute_binary_metrics,
    run_local_training,
)
from tests.train_api.test_features import prepared_rows


class Tracker:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> float:
        self.stopped = True
        return 0.123


def config() -> TrainingConfig:
    return TrainingConfig(
        threshold=0.5,
        feature_engineering=FeatureEngineeringConfig(geo_bins=4, rare_threshold=0),
        model_parameters={"objective": "binary", "n_estimators": 3, "n_jobs": 1, "verbose": -1},
    )


def training_plan() -> TrainingPlan:
    data = pd.concat([prepared_rows(), prepared_rows().iloc[:4]], ignore_index=True)
    data["Num_Acc"] = range(len(data))
    data["accident_date"] = pd.to_datetime(
        ["2023-12-20"] * 10 + ["2024-01-03"] * 4
    )
    data.loc[10:, "lat"] = 50.0
    data.loc[10:, "long"] = 8.0
    data["grav_binaire"] = [0, 1] * 7
    snapshot = TrainingSnapshot(data=data, manifest={"mode": "weekly", "week": 1})
    train_mask = pd.Series([True] * 10 + [False] * 4)
    evaluation_mask = ~train_mask
    return TrainingPlan(
        snapshot=snapshot,
        train_mask=train_mask,
        evaluation_mask=evaluation_mask,
        model_fit_mask=pd.Series([True] * len(data)),
        mode="weekly",
        week=1,
        evaluation_start=pd.Timestamp("2024-01-01"),
        evaluation_end=pd.Timestamp("2024-01-08"),
    )


def test_compute_binary_metrics_on_controlled_vectors() -> None:
    metrics = compute_binary_metrics(
        np.array([0, 0, 1, 1]),
        np.array([0.1, 0.6, 0.7, 0.2]),
        threshold=0.5,
    )

    assert metrics["accuracy"] == 0.5
    assert metrics["tn"] == metrics["fp"] == metrics["fn"] == metrics["tp"] == 1.0
    assert metrics["roc_auc"] == 0.75
    assert set(metrics) == {
        "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "tn", "fp", "fn", "tp"
    }


def test_local_training_returns_only_the_final_model_and_writes_only_workspace(
    tmp_path: Path,
) -> None:
    tracker = Tracker()
    plan = training_plan()
    artifacts = run_local_training(
        plan,
        config(),
        workspace=tmp_path,
        write_artifacts=True,
        tracker_factory=lambda _: tracker,
    )

    final_transformer = artifacts.final_model.pipeline.named_steps[
        "feature_engineering"
    ]
    assert tracker.started and tracker.stopped
    assert artifacts.emissions_kg == 0.123
    assert not hasattr(artifacts, "evaluation_pipeline")
    assert final_transformer.lat_edges_[-1] >= plan.data.loc[
        plan.model_fit_mask, "lat"
    ].max()
    assert all(
        path is not None and path.parent == tmp_path and path.is_file()
        for path in (artifacts.report_path, artifacts.figure_path)
    )
    assert artifacts.model_path is None
    assert {"metrics.json", "evaluation.png"}.issubset(
        {path.name for path in tmp_path.iterdir()}
    )
    assert not (tmp_path / "model.joblib").exists()


def test_evaluation_pipeline_is_collected_before_final_refit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = training_plan()
    fitted_indices: list[list[int]] = []
    predicted_indices: list[list[int]] = []
    pipeline_count = 0

    class FakePipeline:
        def __init__(self) -> None:
            self.cycle = self

        def fit(self, features: pd.DataFrame, _labels: np.ndarray) -> FakePipeline:
            fitted_indices.append(features.index.tolist())
            return self

        def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
            predicted_indices.append(features.index.tolist())
            probabilities = np.full(len(features), 0.6)
            return np.column_stack((1 - probabilities, probabilities))

    evaluation_ref: weakref.ReferenceType[FakePipeline] | None = None

    def build_fake_pipeline(_config: TrainingConfig) -> FakePipeline:
        nonlocal evaluation_ref, pipeline_count
        pipeline_count += 1
        if pipeline_count == 2:
            assert evaluation_ref is not None
            assert evaluation_ref() is None
        pipeline = FakePipeline()
        if pipeline_count == 1:
            evaluation_ref = weakref.ref(pipeline)
        return pipeline

    monkeypatch.setattr(training_module, "build_pipeline", build_fake_pipeline)

    artifacts = run_local_training(
        plan,
        config(),
        workspace=tmp_path,
        tracker_factory=lambda _: Tracker(),
    )

    assert pipeline_count == 2
    assert fitted_indices == [
        plan.data.index[plan.train_mask].tolist(),
        plan.data.index[plan.model_fit_mask].tolist(),
    ]
    assert predicted_indices == [plan.data.index[plan.evaluation_mask].tolist()]
    assert artifacts.final_model.pipeline is not None


def test_tracker_stops_even_when_model_fit_fails(tmp_path: Path) -> None:
    tracker = Tracker()
    broken = training_plan()
    broken.snapshot.data.drop(columns=["lat"], inplace=True)

    with pytest.raises(ValueError, match="Colonnes préparées manquantes"):
        run_local_training(
            broken,
            config(),
            workspace=tmp_path,
            tracker_factory=lambda _: tracker,
        )

    assert tracker.started and tracker.stopped


def test_local_training_requires_an_existing_workspace(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Workspace d'entraînement invalide"):
        run_local_training(training_plan(), config(), workspace=tmp_path / "missing")
