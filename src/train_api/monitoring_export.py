"""Bridge : écrit les 2 JSON que les exporters Prometheus lisent."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from src.train_api.monitoring import MonitoringResult

DRIFT_RESULTS_PATH = Path("monitoring/drift/drift_results.json")
ML_PERFORMANCE_PATH = Path("monitoring/ml/model_performance.json")

# Seuil de part de colonnes driftées à partir duquel une semaine compte
# comme "significative" pour le compteur de persistance (aligné sur le
# DriftedColumnsCount(drift_share=0.5) déjà utilisé par Evidently/l'exporter).
DRIFT_SIGNIFICANT_SHARE_THRESHOLD = 0.5


def _atomic_write_json(output_path: Path, payload: dict) -> None:
    """Écrit le JSON via un fichier temporaire + rename atomique.

    Évite qu'un exporter lisant le fichier en parallèle (scrape Prometheus,
    requête /metrics) ne tombe sur un JSON tronqué pendant l'écriture.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, default=str)
        os.replace(tmp_path, output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def export_ml_performance(
    monitoring: MonitoringResult,
    *,
    week: int,
    rows: int,
    model_name: str,
    model_alias: str,
    output_path: Path = ML_PERFORMANCE_PATH,
) -> None:
    if not monitoring.available or monitoring.champion_metrics is None:
        return
    payload = {
        "generated_at": time.time(),
        "week": week,
        "rows": rows,
        "model_source": "mlflow_registry",
        "model_name": model_name,
        "model_version": monitoring.champion_version,
        "model_alias": model_alias,
        "threshold": monitoring.threshold,
        "metrics": monitoring.champion_metrics,
    }
    _atomic_write_json(output_path, payload)


def _extract_drift_share(report: dict) -> float | None:
    """Retrouve la part de colonnes driftées dans le report Evidently brut."""
    for metric in report.get("metrics", []):
        if not isinstance(metric, dict):
            continue
        if metric.get("config", {}).get("type") != "evidently:metric_v2:DriftedColumnsCount":
            continue
        value = metric.get("value")
        if isinstance(value, dict) and "share" in value:
            return float(value["share"])
    return None


def _next_consecutive_significant_weeks(output_path: Path, significant_this_week: bool) -> int:
    """Incrémente le streak si la semaine est significative, sinon le remet à 0."""
    if not significant_this_week:
        return 0
    previous_streak = 0
    if output_path.exists():
        try:
            previous = json.loads(output_path.read_text(encoding="utf-8"))
            previous_streak = int(previous.get("consecutive_significant_weeks", 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            previous_streak = 0
    return previous_streak + 1


def export_drift_results(
    monitoring: MonitoringResult,
    *,
    output_path: Path = DRIFT_RESULTS_PATH,
) -> None:
    if monitoring.drift_report is None:
        return
    payload = dict(monitoring.drift_report)
    payload["generated_at"] = time.time()

    share = _extract_drift_share(payload)
    significant = share is not None and share >= DRIFT_SIGNIFICANT_SHARE_THRESHOLD
    payload["consecutive_significant_weeks"] = _next_consecutive_significant_weeks(
        output_path, significant
    )

    _atomic_write_json(output_path, payload)
