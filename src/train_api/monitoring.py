"""Direct weekly champion evaluation and drift monitoring."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

from src.train_api.config import Settings
from src.train_api.data import DATE_COLUMN, TARGET_COLUMN, TrainingPlan
from src.train_api.errors import MlflowUnavailable, TrainingFailed
from src.train_api.mlflow_service import ChampionModel, MlflowTrainingService
from src.train_api.training import compute_binary_metrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitoringResult:
    """Typed facts produced while evaluating one champion on one WNN."""

    available: bool
    champion_version: str | None
    champion_mlflow_run_id: str | None
    champion_metrics: dict[str, float] | None
    drift_detected: bool | None
    drift_report_path: Path | None
    error: str | None = None
    threshold: float | None = None       
    drift_report: dict | None = None  


def monitor_weekly_champion(
    plan: TrainingPlan,
    *,
    settings: Settings,
    workspace: Path,
    mlflow_service: MlflowTrainingService,
) -> MonitoringResult:
    """Evaluate the exact alias target and run Evidently in the injected workspace."""
    if plan.mode != "weekly":
        raise ValueError("Le monitoring champion exige un plan weekly")
    try:
        champion = mlflow_service.load_champion()
        if champion is None:
            return MonitoringResult(False, None, None, None, None, None, "Aucun champion MLflow")
        return _monitor_loaded_champion(plan, champion, workspace)
    except Exception as error:
        if settings.monitoring_required:
            if isinstance(error, (MlflowUnavailable, TrainingFailed)):
                raise
            raise TrainingFailed("Échec du monitoring weekly") from error
        logger.warning("Monitoring weekly indisponible: %s", error)
        return MonitoringResult(False, None, None, None, None, None, str(error))


def _monitor_loaded_champion(
    plan: TrainingPlan, champion: ChampionModel, workspace: Path
) -> MonitoringResult:
    if not workspace.is_dir():
        raise TrainingFailed(f"Workspace de monitoring invalide : {workspace}")
    features = plan.data.drop(columns=[DATE_COLUMN, TARGET_COLUMN])
    labels = plan.data[TARGET_COLUMN].astype(int).to_numpy()
    evaluation_mask = plan.evaluation_mask
    probabilities = champion.model.predict_proba(features.loc[evaluation_mask])[:, 1]
    threshold = float(getattr(champion.model, "threshold", 0.5))
    metrics = compute_binary_metrics(labels[evaluation_mask], probabilities, threshold=threshold)
    reference, current = _feature_frames(champion, features, plan)
    report = Report([DataDriftPreset()]).run(reference_data=reference, current_data=current)
    report_path = workspace / "drift_report.html"
    report.save_html(str(report_path))
    report_dict = report.dict()
    drift_detected = _drift_detected(report_dict)
    return MonitoringResult(
        True, champion.version, champion.mlflow_run_id, metrics, drift_detected, report_path,
        threshold=threshold, drift_report=report_dict,
    )



def _feature_frames(
    champion: ChampionModel, features: pd.DataFrame, plan: TrainingPlan
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pipeline = getattr(champion.model, "pipeline", champion.model)
    transformer = pipeline.named_steps.get("feature_engineering")
    if transformer is None:
        raise TrainingFailed("Le champion ne contient pas le transformeur de features")
    return (
        transformer.transform(features.loc[plan.train_mask]).reset_index(drop=True),
        transformer.transform(features.loc[plan.evaluation_mask]).reset_index(drop=True),
    )


def _drift_detected(report: dict[str, object]) -> bool:
    metrics = report.get("metrics", [])
    for metric in metrics:
        if not isinstance(metric, dict) or "DriftedColumnsCount" not in str(metric.get("metric_name")):
            continue
        value = metric.get("value")
        return isinstance(value, dict) and float(value.get("count", 0)) > 0
    return False
