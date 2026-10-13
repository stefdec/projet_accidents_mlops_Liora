import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Gauge,
    generate_latest,
)


app = FastAPI(
    title="Drift Metrics Exporter"
)


DRIFT_RESULTS_FILE = Path(
    "monitoring/drift/drift_results.json"
)


# ============================================================
# Métriques globales
# ============================================================

DATA_DRIFT_DETECTED = Gauge(
    "data_drift_detected",
    "1 si le seuil global de data drift est dépassé, sinon 0",
)

DRIFT_SHARE = Gauge(
    "drift_share",
    "Part des features détectées en drift",
)

DRIFTED_FEATURES = Gauge(
    "drifted_features",
    "Nombre de features détectées en drift",
)

DRIFT_LAST_RUN = Gauge(
    "drift_last_run_timestamp_seconds",
    "Epoch du dernier rapport de drift écrit sur disque",
)
DRIFT_LAST_RUN.set(0)


DRIFT_CONSECUTIVE_WEEKS = Gauge(
    "drift_consecutive_significant_weeks",
    "Nombre de semaines consécutives où drift_share a dépassé le seuil global",
)
DRIFT_CONSECUTIVE_WEEKS.set(0)


# ============================================================
# Métriques par feature
# ============================================================

FEATURE_DRIFT_SCORE = Gauge(
    "feature_drift_score",
    "Score de drift calculé par Evidently pour chaque feature",
    ["feature", "method"],
)

FEATURE_DRIFT_THRESHOLD = Gauge(
    "feature_drift_threshold",
    "Seuil utilisé par Evidently pour détecter le drift",
    ["feature"],
)

FEATURE_DRIFT_DETECTED = Gauge(
    "feature_drift_detected",
    "1 si la feature est détectée en drift, sinon 0",
    ["feature"],
)


def update_drift_metrics() -> None:

    if not DRIFT_RESULTS_FILE.exists():
        return

    with open(
        DRIFT_RESULTS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        results = json.load(file)
        generated_at = results.get("generated_at")
        if generated_at is not None:
            DRIFT_LAST_RUN.set(float(generated_at))

        consecutive_weeks = results.get("consecutive_significant_weeks")
        if consecutive_weeks is not None:
            DRIFT_CONSECUTIVE_WEEKS.set(float(consecutive_weeks))





    # ========================================================
    # Parcours de toutes les métriques Evidently
    # ========================================================

    for metric in results.get("metrics", []):

        config = metric.get("config", {})

        metric_type = config.get("type")


        # ----------------------------------------------------
        # Métrique globale
        # ----------------------------------------------------

        if metric_type == (
            "evidently:metric_v2:DriftedColumnsCount"
        ):

            value = metric.get("value", {})

            drifted_count = float(
                value.get("count", 0)
            )

            drift_share = float(
                value.get("share", 0)
            )

            global_threshold = float(
                config.get("drift_share", 0.5)
            )

            global_drift_detected = int(
                drift_share >= global_threshold
            )

            DRIFTED_FEATURES.set(
                drifted_count
            )

            DRIFT_SHARE.set(
                drift_share
            )

            DATA_DRIFT_DETECTED.set(
                global_drift_detected
            )


        # ----------------------------------------------------
        # Métrique par feature
        # ----------------------------------------------------

        elif metric_type == (
            "evidently:metric_v2:ValueDrift"
        ):

            feature = str(
                config.get("column")
            )

            method = str(
                config.get("method", "unknown")
            )

            threshold = float(
                config.get("threshold", 0)
            )

            score = float(
                metric.get("value", 0)
            )


            # Evidently choisit le test par colonne selon son type/cardinalité :
            # - distance (Wasserstein, Jensen-Shannon, ...) : score >= threshold => drift
            # - p-value (K-S, chi², ...) : score <= threshold => drift (test significatif)
            is_p_value_method = "p_value" in method.lower() or "p-value" in method.lower()

            drift_detected = int(
                score <= threshold if is_p_value_method else score >= threshold
            )


            FEATURE_DRIFT_SCORE.labels(
                feature=feature,
                method=method,
            ).set(
                score
            )


            FEATURE_DRIFT_THRESHOLD.labels(
                feature=feature,
            ).set(
                threshold
            )


            FEATURE_DRIFT_DETECTED.labels(
                feature=feature,
            ).set(
                drift_detected
            )


@app.get("/health")
def health():

    return {
        "status": "ok",
        "drift_results_exists":
            DRIFT_RESULTS_FILE.exists(),
    }


@app.get("/metrics")
def metrics():

    update_drift_metrics()

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )