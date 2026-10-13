from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest



PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULTS_PATH = PROJECT_ROOT / "monitoring" / "ml" / "model_performance.json"

app = FastAPI(title="ML Monitoring Exporter")


MODEL_ACCURACY = Gauge(
    "model_accuracy",
    "Accuracy du champion sur la semaine évaluée",
)

MODEL_PRECISION = Gauge(
    "model_precision",
    "Precision du champion sur la semaine évaluée",
)

MODEL_RECALL = Gauge(
    "model_recall",
    "Recall du champion sur la semaine évaluée",
)

MODEL_F1 = Gauge(
    "model_f1",
    "F1 score du champion sur la semaine évaluée",
)

MODEL_ROC_AUC = Gauge(
    "model_roc_auc",
    "ROC AUC du champion sur la semaine évaluée",
)

MODEL_PR_AUC = Gauge(
    "model_pr_auc",
    "PR AUC du champion sur la semaine évaluée",
)

MODEL_TN = Gauge(
    "model_true_negative",
    "Nombre de vrais négatifs",
)

MODEL_FP = Gauge(
    "model_false_positive",
    "Nombre de faux positifs",
)

MODEL_FN = Gauge(
    "model_false_negative",
    "Nombre de faux négatifs",
)

MODEL_TP = Gauge(
    "model_true_positive",
    "Nombre de vrais positifs",
)

MODEL_EVALUATED_WEEK = Gauge(
    "model_evaluated_week",
    "Numéro de semaine évaluée",
)

MODEL_EVALUATED_ROWS = Gauge(
    "model_evaluated_rows",
    "Nombre de lignes utilisées pour l'évaluation",
)

MODEL_THRESHOLD = Gauge(
    "model_threshold",
    "Threshold du champion utilisé",
)

MODEL_INFO = Gauge(
    "model_monitoring_info",
    "Informations sur le champion évalué",
    ["version", "source", "alias"],
)

MODEL_EVAL_LAST_RUN = Gauge(
    "model_eval_last_run_timestamp_seconds",
    "Epoch de la dernière évaluation ML hebdo écrite sur disque",
)
MODEL_EVAL_LAST_RUN.set(0)


def load_metrics() -> None:
    if not RESULTS_PATH.exists():
        return

    with RESULTS_PATH.open("r", encoding="utf-8") as file:
        result = json.load(file)
        generated_at = result.get("generated_at")
        if generated_at is not None:
            MODEL_EVAL_LAST_RUN.set(float(generated_at))


    metrics = result["metrics"]

    MODEL_ACCURACY.set(float(metrics["accuracy"]))
    MODEL_PRECISION.set(float(metrics["precision"]))
    MODEL_RECALL.set(float(metrics["recall"]))
    MODEL_F1.set(float(metrics["f1"]))
    MODEL_ROC_AUC.set(float(metrics["roc_auc"]))
    MODEL_PR_AUC.set(float(metrics["pr_auc"]))

    MODEL_TN.set(float(metrics["tn"]))
    MODEL_FP.set(float(metrics["fp"]))
    MODEL_FN.set(float(metrics["fn"]))
    MODEL_TP.set(float(metrics["tp"]))

    MODEL_EVALUATED_WEEK.set(float(result["week"]))
    MODEL_EVALUATED_ROWS.set(float(result["rows"]))
    MODEL_THRESHOLD.set(float(result["threshold"]))
    MODEL_INFO.clear()
    MODEL_INFO.labels(
        version=str(result["model_version"]),
        source=str(result["model_source"]),
        alias=str(result["model_alias"]),
    ).set(1)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "results_file": str(RESULTS_PATH),
        "exists": RESULTS_PATH.exists(),
        
    }

@app.get("/refresh")
def refresh() -> dict:
    load_metrics()
    return {"status": "refreshed"}


@app.get("/metrics")
def metrics():
    load_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


load_metrics()
