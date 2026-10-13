"""Instrumentation Prometheus du service predict_api.

Ce module ne connaît que Prometheus : définitions des métriques, fonctions
`record_*` / `track_latency`, et montage de la route /metrics. `service.py`
l'importe et appelle ces fonctions.

Multiprocess : `make_asgi_app()` sert le registre par défaut => suppose un
seul worker BentoML. En multi-worker, remplacer l'import `prometheus_client`
par `bentoml.metrics` (API identique) et laisser BentoML servir /metrics.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

logger = logging.getLogger(__name__)

# --- Définitions -----------------------------------------------------------
TOTAL_REQUESTS = Counter("total_requests", "Nombre total de requêtes")
ERROR_COUNT = Counter("error_count", "Nombre d'erreurs", ["status_code"])
RESPONSE_TIME = Histogram("response_time_seconds", "Temps de réponse")
PREDICTION_COUNT = Counter("prediction_count", "Nombre de prédictions")
PREDICTED_CLASS_DIST = Counter(
    "predicted_class_distribution",
    "Répartition des classes prédites",
    ["class_label"],
)
SUCCESS_COUNT = Counter(
    "prediction_success_total", "Nombre de prédictions réussies"
)
PREDICTION_PROB = Histogram(
    "prediction_probabilities", "Probabilités de prédiction"
)

MODEL_INFO = Gauge(
    "prediction_model_info",
    "Informations sur le modèle champion utilisé",
    ["version"],
    multiprocess_mode="max",
)
MODEL_LOAD_STATE = Gauge(
    "model_load_state",
    "État de chargement du modèle",
    multiprocess_mode="max",
)
MODEL_LOAD_STATE.set(0)


# --- API d'enregistrement ------------------------------------------------
def record_request() -> None:
    TOTAL_REQUESTS.inc()


def record_error(status_code: int | str) -> None:
    ERROR_COUNT.labels(status_code=str(status_code)).inc()


def set_model_loaded(loaded: bool, version: str | None = None) -> None:
    MODEL_LOAD_STATE.set(1 if loaded else 0)
    if loaded and version is not None:
        MODEL_INFO.labels(version=str(version)).set(1)


def record_prediction(
    prediction: int, probability: float | None, model_version: str
) -> None:
    """Alimente les métriques métier après une prédiction réussie."""
    try:
        PREDICTION_COUNT.inc()
        SUCCESS_COUNT.inc()
        PREDICTED_CLASS_DIST.labels(class_label=str(prediction)).inc()
        MODEL_INFO.labels(version=str(model_version)).set(1)
        MODEL_LOAD_STATE.set(1)
        if probability is not None:
            PREDICTION_PROB.observe(float(probability))
    except (TypeError, ValueError):
        logger.exception("Échec de la collecte des métriques de prédiction.")


@contextmanager
def track_latency():
    start = time.perf_counter()
    try:
        yield
    finally:
        RESPONSE_TIME.observe(time.perf_counter() - start)


def mount_metrics(app) -> None:
    """Monte GET /metrics sur l'app FastAPI du service."""
    app.mount("/metrics", make_asgi_app())
