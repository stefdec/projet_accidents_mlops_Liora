from __future__ import annotations

import json

from src.train_api.monitoring import MonitoringResult
from src.train_api.monitoring_export import (
    export_drift_results,
    export_ml_performance,
)


def _monitoring_result(**overrides) -> MonitoringResult:
    """Construit un MonitoringResult valide, personnalisable par overrides."""
    defaults = dict(
        available=True,
        champion_version="7",
        champion_mlflow_run_id="run123",
        champion_metrics={
            "accuracy": 0.9, "precision": 0.8, "recall": 0.7,
            "f1": 0.75, "roc_auc": 0.95, "pr_auc": 0.85,
            "tn": 10, "fp": 2, "fn": 3, "tp": 15,
        },
        drift_detected=False,
        drift_report_path=None,
        threshold=0.48,
    )
    defaults.update(overrides)
    return MonitoringResult(**defaults)


def test_export_ml_performance_writes_expected_shape(tmp_path):
    result = _monitoring_result()
    out = tmp_path / "model_performance.json"

    export_ml_performance(
        result, week=3, rows=120,
        model_name="accidents-gravity-classifier",
        model_alias="champion", output_path=out,
    )

    data = json.loads(out.read_text())
    assert data["week"] == 3
    assert data["rows"] == 120
    assert data["model_version"] == "7"
    assert data["model_alias"] == "champion"
    assert data["threshold"] == 0.48
    assert data["metrics"]["recall"] == 0.7
    assert "generated_at" in data


def test_export_ml_performance_skips_when_monitoring_unavailable(tmp_path):
    result = _monitoring_result(available=False, champion_metrics=None)
    out = tmp_path / "model_performance.json"

    export_ml_performance(
        result, week=3, rows=120,
        model_name="accidents-gravity-classifier",
        model_alias="champion", output_path=out,
    )

    assert not out.exists()


def test_export_drift_results_writes_report_with_timestamp(tmp_path):
    result = _monitoring_result(
        drift_report={"metrics": [{"config": {"type": "evidently:metric_v2:DriftedColumnsCount"}}]}
    )
    out = tmp_path / "drift_results.json"

    export_drift_results(result, output_path=out)

    data = json.loads(out.read_text())
    assert "generated_at" in data
    assert data["metrics"][0]["config"]["type"] == "evidently:metric_v2:DriftedColumnsCount"


def test_export_drift_results_skips_when_no_report(tmp_path):
    result = _monitoring_result(drift_report=None)
    out = tmp_path / "drift_results.json"

    export_drift_results(result, output_path=out)

    assert not out.exists()


def _drift_report(share: float) -> dict:
    return {
        "metrics": [
            {
                "config": {"type": "evidently:metric_v2:DriftedColumnsCount"},
                "value": {"count": 10, "share": share},
            }
        ]
    }


def test_export_drift_results_starts_streak_at_one_on_first_significant_week(tmp_path):
    result = _monitoring_result(drift_report=_drift_report(0.6))
    out = tmp_path / "drift_results.json"

    export_drift_results(result, output_path=out)

    assert json.loads(out.read_text())["consecutive_significant_weeks"] == 1


def test_export_drift_results_increments_streak_across_consecutive_weeks(tmp_path):
    result = _monitoring_result(drift_report=_drift_report(0.6))
    out = tmp_path / "drift_results.json"

    export_drift_results(result, output_path=out)
    export_drift_results(result, output_path=out)
    export_drift_results(result, output_path=out)

    assert json.loads(out.read_text())["consecutive_significant_weeks"] == 3


def test_export_drift_results_resets_streak_when_not_significant(tmp_path):
    out = tmp_path / "drift_results.json"
    export_drift_results(_monitoring_result(drift_report=_drift_report(0.6)), output_path=out)
    export_drift_results(_monitoring_result(drift_report=_drift_report(0.2)), output_path=out)

    assert json.loads(out.read_text())["consecutive_significant_weeks"] == 0

