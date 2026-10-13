"""Configurable, in-memory construction of the v2 LightGBM pipeline."""

from __future__ import annotations

import gc
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd
import yaml
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, TargetEncoder

from src.train_api.data import DATE_COLUMN, TARGET_COLUMN, TrainingPlan
from src.train_api.errors import ConfigurationError
from src.train_api.features import AccidentFeatureTransformer

CATEGORICAL_COLUMNS = ["age_group"]
TARGET_ENCODE_COLUMNS = ["manv", "catv_group_x_catr", "age_group_x_catv_group"]


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    """Parameters of the learned feature transformer."""

    geo_bins: int = 1000
    rare_threshold: float = 0.005
    interaction_rare_threshold: float = 0.001


@dataclass(frozen=True)
class TrainingConfig:
    """Immutable parameters needed to build one model pipeline."""

    threshold: float
    feature_engineering: FeatureEngineeringConfig
    model_parameters: Mapping[str, object]


@dataclass(frozen=True)
class TrainingArtifacts:
    """Results of local evaluation and final refit for one validated plan."""

    final_model: ThresholdedBinaryClassifier
    metrics: dict[str, float]
    threshold: float
    manifest: dict[str, object]
    emissions_kg: float | None
    report_path: Path | None
    figure_path: Path | None
    model_path: Path | None


class ThresholdedBinaryClassifier(ClassifierMixin, BaseEstimator):
    """Expose a fitted binary estimator with its decision threshold."""

    def __init__(self, pipeline: Pipeline, *, threshold: float = 0.5) -> None:
        self.pipeline = pipeline
        self.threshold = threshold

    @property
    def classes_(self) -> np.ndarray:
        return self.pipeline.classes_

    def fit(self, X: Any, y: Any) -> ThresholdedBinaryClassifier:
        self.pipeline.fit(X, y)
        return self

    def predict_proba(self, X: Any) -> np.ndarray:
        return self.pipeline.predict_proba(X)

    def predict(self, X: Any) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= float(self.threshold)).astype(np.int64)


def load_training_config(path: Path) -> TrainingConfig:
    """Read and validate an explicit immutable YAML configuration file."""
    try:
        with path.open(encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError(
            f"Configuration d'entraînement invalide : {path}"
        ) from error
    if not isinstance(raw, Mapping):
        raise ConfigurationError("La configuration d'entraînement doit être un objet")
    return training_config_from_mapping(raw)


def training_config_from_mapping(raw: Mapping[str, object]) -> TrainingConfig:
    """Validate an injected mapping and freeze its parameters for one run."""
    try:
        threshold = float(raw["threshold"])
        feature_raw = raw["feature_engineering"]
        model_raw = raw["model"]
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError("Configuration d'entraînement incomplète") from error
    if not 0.0 <= threshold <= 1.0:
        raise ConfigurationError("threshold doit être compris entre 0 et 1")
    if not isinstance(feature_raw, Mapping) or not isinstance(model_raw, Mapping):
        raise ConfigurationError(
            "Les sections feature_engineering et model sont requises"
        )
    try:
        feature_config = FeatureEngineeringConfig(
            geo_bins=int(feature_raw["geo_bins"]),
            rare_threshold=float(feature_raw["rare_threshold"]),
            interaction_rare_threshold=float(feature_raw["interaction_rare_threshold"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError(
            "Paramètres de feature engineering invalides"
        ) from error
    if (
        feature_config.geo_bins < 2
        or not 0 <= feature_config.rare_threshold <= 1
        or not 0 <= feature_config.interaction_rare_threshold <= 1
    ):
        raise ConfigurationError("Paramètres de feature engineering hors limites")
    if not model_raw:
        raise ConfigurationError("Les paramètres LightGBM sont requis")
    return TrainingConfig(
        threshold=threshold,
        feature_engineering=feature_config,
        model_parameters=MappingProxyType(dict(model_raw)),
    )


def build_pipeline(config: TrainingConfig) -> Pipeline:
    """Build an unfitted pipeline without reading files or writing artifacts."""
    transformer = AccidentFeatureTransformer(
        geo_bins=config.feature_engineering.geo_bins,
        rare_threshold=config.feature_engineering.rare_threshold,
        interaction_rare_threshold=config.feature_engineering.interaction_rare_threshold,
    )
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "ohe",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_COLUMNS,
            ),
            (
                "target",
                TargetEncoder(
                    target_type="binary",
                    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                ),
                TARGET_ENCODE_COLUMNS,
            ),
        ],
        remainder="passthrough",
    )
    return Pipeline(
        [
            ("feature_engineering", transformer),
            ("preprocessor", preprocessor),
            ("model", LGBMClassifier(**dict(config.model_parameters))),
        ]
    )


def compute_binary_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    threshold: float,
) -> dict[str, float]:
    """Calculate the stable metric set used by the local training workflow."""
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
        "tp": float(tp),
    }


def _evaluate_candidate(
    plan: TrainingPlan,
    config: TrainingConfig,
    features: pd.DataFrame,
    labels: np.ndarray,
) -> tuple[dict[str, float], np.ndarray]:
    """Evaluate a temporary pipeline without retaining it for the final refit."""
    evaluation_pipeline = build_pipeline(config)
    evaluation_pipeline.fit(features.loc[plan.train_mask], labels[plan.train_mask])
    probabilities = evaluation_pipeline.predict_proba(
        features.loc[plan.evaluation_mask]
    )[:, 1]
    metrics = compute_binary_metrics(
        labels[plan.evaluation_mask], probabilities, threshold=config.threshold
    )
    return metrics, probabilities


def run_local_training(
    plan: TrainingPlan,
    config: TrainingConfig,
    *,
    workspace: Path,
    write_artifacts: bool = False,
    tracker_factory: Callable[[Path], Any] | None = None,
) -> TrainingArtifacts:
    """Evaluate on the plan window then refit a separate final model locally."""
    if not workspace.is_dir():
        raise ConfigurationError(f"Workspace d'entraînement invalide : {workspace}")
    features = plan.data.drop(columns=[DATE_COLUMN, TARGET_COLUMN])
    labels = plan.data[TARGET_COLUMN].astype(int).to_numpy()
    tracker = (tracker_factory or _default_tracker_factory)(workspace)
    emissions_kg: float | None = None
    try:
        tracker.start()
        metrics, probabilities = _evaluate_candidate(plan, config, features, labels)
        # The evaluation model is no longer needed. Collect cycles before allocating
        # the independent final pipeline and its native LightGBM buffers.
        gc.collect()
        final_model = ThresholdedBinaryClassifier(
            build_pipeline(config), threshold=config.threshold
        ).fit(features.loc[plan.model_fit_mask], labels[plan.model_fit_mask])
        report_path, figure_path, model_path = _write_artifacts(
            workspace=workspace,
            plan=plan,
            metrics=metrics,
            probabilities=probabilities,
            labels=labels[plan.evaluation_mask],
            model=final_model,
            write_artifacts=write_artifacts,
        )
    finally:
        emissions = tracker.stop()
        emissions_kg = float(emissions) if emissions is not None else None
    return TrainingArtifacts(
        final_model=final_model,
        metrics=metrics,
        threshold=config.threshold,
        manifest=dict(plan.snapshot.manifest),
        emissions_kg=emissions_kg,
        report_path=report_path,
        figure_path=figure_path,
        model_path=model_path,
    )


SUSTAINABILITY_REPORTS_DIR = Path("reports/carbon")


def _default_tracker_factory(workspace: Path) -> Any:
    from codecarbon import EmissionsTracker

    SUSTAINABILITY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EmissionsTracker(
        project_name="train-api",
        output_dir=str(SUSTAINABILITY_REPORTS_DIR),
        save_to_file=True,
        log_level="error",
    )


def _write_artifacts(
    *,
    workspace: Path,
    plan: TrainingPlan,
    metrics: dict[str, float],
    probabilities: np.ndarray,
    labels: np.ndarray,
    model: ThresholdedBinaryClassifier,
    write_artifacts: bool,
) -> tuple[Path | None, Path | None, Path | None]:
    if not write_artifacts:
        return None, None, None
    report_path = workspace / "metrics.json"
    figure_path = workspace / "evaluation.png"
    report_path.write_text(
        json.dumps(
            {"metrics": metrics, "manifest": plan.snapshot.manifest},
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _save_evaluation_figure(
        labels, probabilities, threshold=model.threshold, path=figure_path
    )
    # Le modèle est journalisé directement depuis la mémoire par MLflow.
    # Aucun doublon joblib local n'est produit.
    return report_path, figure_path, None


def _save_evaluation_figure(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    threshold: float,
    path: Path,
) -> None:
    matplotlib_cache = path.parent / ".matplotlib"
    matplotlib_cache.mkdir(exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(matplotlib_cache)
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    predictions = (probabilities >= threshold).astype(int)
    figure, axis = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay.from_predictions(
        labels, predictions, ax=axis, colorbar=False
    )
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)
