from __future__ import annotations

import inspect
from pathlib import Path

from mlflow import MlflowClient
import pytest

from src.train_api.domain import decide_promotion
from src.train_api.mlflow_service import MlflowTrainingService
from tests.train_api.test_mlflow_service import local_artifacts, service_settings
from tests.train_api.test_training import config, training_plan


def test_promotion_decision_promotes_first_candidate_without_champion_score() -> None:
    decision = decide_promotion(
        candidate_version="1",
        candidate_score=0.62,
        champion_version=None,
        champion_score=None,
        metric="pr_auc",
        min_improvement=0.01,
    )

    assert decision.promoted is True
    assert decision.reason == "no_existing_champion"
    assert decision.delta is None


def test_promotion_decision_requires_strict_same_window_improvement() -> None:
    promoted = decide_promotion(
        candidate_version="2",
        candidate_score=0.62,
        champion_version="1",
        champion_score=0.60,
        metric="pr_auc",
        min_improvement=0.01,
    )
    rejected = decide_promotion(
        candidate_version="3",
        candidate_score=0.61,
        champion_version="1",
        champion_score=0.60,
        metric="pr_auc",
        min_improvement=0.01,
    )

    assert promoted.promoted is True
    assert promoted.reason == "candidate_improved_on_same_window"
    assert promoted.delta == pytest.approx(0.02)
    assert rejected.promoted is False
    assert rejected.reason == "candidate_below_min_improvement"


def test_registry_tags_and_alias_change_only_after_positive_decision(tmp_path: Path) -> None:
    settings = service_settings(tmp_path)
    service = MlflowTrainingService(settings)
    logged = service.log_training(
        local_artifacts(tmp_path),
        training_plan(),
        config(),
        dataset_digest="sha256:registry-test",
    )
    first = service.register_candidate(logged)
    service.apply_promotion(
        decide_promotion(
            candidate_version=first.version,
            candidate_score=0.6,
            champion_version=None,
            champion_score=None,
            metric="pr_auc",
            min_improvement=0.01,
        )
    )
    second = service.register_candidate(logged)
    rejected = decide_promotion(
        candidate_version=second.version,
        candidate_score=0.61,
        champion_version=first.version,
        champion_score=0.60,
        metric="pr_auc",
        min_improvement=0.01,
    )
    service.apply_promotion(rejected)

    client = MlflowClient(settings.mlflow_tracking_uri)
    assert service.resolve_champion() == first
    assert client.get_model_version(settings.mlflow_registered_model_name, first.version).tags["role"] == "champion"
    assert client.get_model_version(settings.mlflow_registered_model_name, second.version).tags["role"] == "candidate"

    promoted = decide_promotion(
        candidate_version=second.version,
        candidate_score=0.62,
        champion_version=first.version,
        champion_score=0.60,
        metric="pr_auc",
        min_improvement=0.01,
    )
    service.apply_promotion(promoted)

    assert service.resolve_champion() == second
    assert client.get_model_version(settings.mlflow_registered_model_name, first.version).tags["role"] == "archived"
    assert client.get_model_version(settings.mlflow_registered_model_name, second.version).tags["role"] == "champion"


def test_pure_decision_does_not_access_mlflow_or_historical_metrics() -> None:
    source = inspect.getsource(decide_promotion)

    assert "MlflowClient" not in source
    assert "histor" not in source.lower()
