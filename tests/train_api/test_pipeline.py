from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.train_api.errors import ConfigurationError
from src.train_api.training import (
    FeatureEngineeringConfig,
    ThresholdedBinaryClassifier,
    TrainingConfig,
    build_pipeline,
    load_training_config,
    training_config_from_mapping,
)
from tests.train_api.test_features import prepared_rows


def test_pipeline_fits_a_small_injected_configuration() -> None:
    config = TrainingConfig(
        threshold=0.4,
        feature_engineering=FeatureEngineeringConfig(geo_bins=4, rare_threshold=0),
        model_parameters={"objective": "binary", "n_estimators": 3, "n_jobs": 1, "verbose": -1},
    )
    features = prepared_rows()
    labels = np.array([0, 1] * 5)

    pipeline = build_pipeline(config)
    pipeline.fit(features, labels)

    assert pipeline.predict_proba(features).shape == (10, 2)
    assert pipeline.named_steps["model"].n_estimators == 3


def test_loaded_configuration_is_validated_and_immutable(tmp_path: Path) -> None:
    config_file = tmp_path / "training.yaml"
    config_file.write_text(
        """threshold: 0.48
feature_engineering:
  geo_bins: 4
  rare_threshold: 0.0
  interaction_rare_threshold: 0.0
model:
  objective: binary
  n_estimators: 3
""",
        encoding="utf-8",
    )

    config = load_training_config(config_file)

    assert config.threshold == 0.48
    with pytest.raises(TypeError):
        config.model_parameters["n_estimators"] = 5  # type: ignore[index]


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="threshold"):
        training_config_from_mapping(
            {
                "threshold": 2,
                "feature_engineering": {
                    "geo_bins": 4,
                    "rare_threshold": 0,
                    "interaction_rare_threshold": 0,
                },
                "model": {"n_estimators": 3},
            }
        )


class FakePipeline:
    classes_ = np.array([0, 1])

    def predict_proba(self, X: object) -> np.ndarray:
        del X
        return np.array([[0.51, 0.49], [0.50, 0.50]])


def test_threshold_wrapper_matches_predict_proba() -> None:
    classifier = ThresholdedBinaryClassifier(FakePipeline(), threshold=0.48)  # type: ignore[arg-type]

    assert classifier.predict([{}, {}]).tolist() == [1, 1]
    assert classifier.predict_proba([{}, {}]).shape == (2, 2)
