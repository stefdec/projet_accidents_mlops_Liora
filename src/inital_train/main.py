"""Obtain a train token from auth-api, then trigger one initial training run."""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bentoml
import mlflow
import requests
from bentoml import mlflow as bentoml_mlflow
from bentoml import models as bento_models
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class TriggerSettings:
    """Explicit runtime configuration for the one-shot trigger."""

    auth_api_url: str
    train_api_url: str
    username: str
    password: str
    idempotency_key: str
    retries: int
    connect_timeout_seconds: float
    auth_timeout_seconds: float
    train_timeout_seconds: float
    mlflow_tracking_uri: str
    mlflow_registered_model_name: str
    mlflow_champion_alias: str
    bento_model_name: str
    current_model_file: Path
    predict_api_url: str


class ModelPublicationError(RuntimeError):
    """Raised when the trained model cannot be published to BentoML."""


def load_settings(environment: dict[str, str] | None = None) -> TriggerSettings:
    """Load required credentials and conservative retry/timeout settings."""
    values = os.environ if environment is None else environment
    missing = [
        name
        for name in ("TRAIN_USERNAME", "TRAIN_PASSWORD", "INITIAL_IDEMPOTENCY_KEY")
        if not values.get(name, "").strip()
    ]
    if missing:
        raise ValueError("Variables obligatoires absentes : " + ", ".join(missing))
    return TriggerSettings(
        auth_api_url=values.get("AUTH_API_URL", "http://auth-api:8000/login"),
        train_api_url=values.get("TRAIN_API_URL", "http://train-api:8000/train"),
        predict_api_url=values.get(
            "PREDICT_API_URL", "http://predict-api:8000/reload"
        ),
        username=values["TRAIN_USERNAME"],
        password=values["TRAIN_PASSWORD"],
        idempotency_key=values["INITIAL_IDEMPOTENCY_KEY"],
        retries=_positive_int(values.get("API_RETRIES", "3"), "API_RETRIES"),
        connect_timeout_seconds=_positive_float(
            values.get("API_CONNECT_TIMEOUT_SECONDS", "10"),
            "API_CONNECT_TIMEOUT_SECONDS",
        ),
        auth_timeout_seconds=_positive_float(
            values.get("AUTH_API_TIMEOUT_SECONDS", "30"),
            "AUTH_API_TIMEOUT_SECONDS",
        ),
        train_timeout_seconds=_positive_float(
            values.get("TRAIN_API_TIMEOUT_SECONDS", "7200"),
            "TRAIN_API_TIMEOUT_SECONDS",
        ),
        mlflow_tracking_uri=values.get(
            "MLFLOW_TRACKING_URI", "http://mlflow-server:5001"
        ),
        mlflow_registered_model_name=values.get(
            "MLFLOW_REGISTERED_MODEL_NAME", "accidents-gravity-classifier"
        ),
        mlflow_champion_alias=values.get("MLFLOW_CHAMPION_ALIAS", "champion"),
        bento_model_name=values.get("BENTO_MODEL_NAME", "accidents"),
        current_model_file=Path(
            values.get("CURRENT_MODEL_FILE", "/bentoml/current_model.txt")
        ),
    )


def build_session(retries: int) -> requests.Session:
    """Retry transient HTTP failures; POST is safe through idempotency keys."""
    policy = Retry(
        total=retries,
        connect=retries,
        read=retries,
        # Une réponse HTTP d'erreur est définitive pour cet appel. La rejouer
        # pourrait relancer un entraînement complet si le premier a échoué
        # avant d'enregistrer un résultat idempotent.
        status=0,
        backoff_factor=1,
        allowed_methods=frozenset({"POST"}),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=policy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def request_token(
    session: requests.Session, settings: TriggerSettings, token_type: str
) -> str:
    """Authenticate and return a token scoped to ``token_type``."""
    response = session.post(
        settings.auth_api_url,
        json={
            "username": settings.username,
            "password": settings.password,
            "token_type": token_type,
        },
        timeout=(settings.connect_timeout_seconds, settings.auth_timeout_seconds),
    )
    _raise_for_status(response, "auth-api")
    try:
        token = response.json()["access_token"]
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "auth-api a retourné une réponse sans access_token"
        ) from error
    if not isinstance(token, str) or not token:
        raise RuntimeError("auth-api a retourné un access_token invalide")
    return token


def trigger_initial_training(
    session: requests.Session, settings: TriggerSettings, token: str
) -> dict[str, Any]:
    """Call the synchronous initial workflow and return its validated JSON body."""
    response = session.post(
        settings.train_api_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"mode": "initial", "idempotency_key": settings.idempotency_key},
        timeout=(settings.connect_timeout_seconds, settings.train_timeout_seconds),
    )
    _raise_for_status(response, "train-api")
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError(
            "train-api a retourné une réponse JSON invalide"
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or not isinstance(payload.get("new_model"), bool)
    ):
        raise RuntimeError("train-api n'a pas retourné un succès exploitable")
    return payload


def publish_initial_model(
    training_result: dict[str, Any], settings: TriggerSettings
) -> str:
    """Import the exact MLflow model once and atomically select it for inference."""
    run_id = _required_result_text(training_result, "mlflow_run_id")
    model_uri = _required_result_text(training_result, "model_uri")
    model_type = _required_result_text(training_result, "model_type")

    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        model_tag = _find_model_tag(settings.bento_model_name, run_id)
        if model_tag is None:
            model = bentoml_mlflow.import_model(
                name=settings.bento_model_name,
                model_uri=model_uri,
                labels={"mlflow_run_id": run_id, "model_type": model_type},
            )
            model_tag = str(model.tag)
        _write_current_model(settings.current_model_file, model_tag)
    except ModelPublicationError:
        raise
    except Exception as error:
        raise ModelPublicationError(
            "impossible de publier le modèle initial dans BentoML"
        ) from error
    return model_tag


def resolve_registry_champion(settings: TriggerSettings) -> dict[str, str]:
    """Resolve the exact Registry champion so BentoML can be bootstrapped."""
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        client = mlflow.MlflowClient(settings.mlflow_tracking_uri)
        version = client.get_model_version_by_alias(
            settings.mlflow_registered_model_name,
            settings.mlflow_champion_alias,
        )
    except Exception as error:
        raise ModelPublicationError(
            "impossible de résoudre le champion dans MLflow Registry"
        ) from error
    return {
        "mlflow_run_id": version.run_id,
        "model_uri": (
            f"models:/{settings.mlflow_registered_model_name}/{version.version}"
        ),
        "model_type": "registry_champion",
    }


def trigger_model_reload(
    session: requests.Session, settings: TriggerSettings, token: str
) -> dict[str, Any]:
    """Call the predict API to reload the current model and return its validated JSON body."""
    response = session.post(
        settings.predict_api_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=(settings.connect_timeout_seconds, settings.train_timeout_seconds),
    )
    _raise_for_status(response, "predict-api")
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError(
            "predict-api a retourné une réponse JSON invalide"
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "Model reloaded successfully"
    ):
        raise RuntimeError("predict-api n'a pas retourné un succès exploitable")
    return payload


def _find_model_tag(model_name: str, mlflow_run_id: str) -> str | None:
    """Return a previously imported tag for this MLflow run, if present."""
    try:
        models = bento_models.list(model_name)
    except bentoml.exceptions.NotFound:
        return None
    for model in models:
        if model.info.labels.get("mlflow_run_id") == mlflow_run_id:
            return str(model.tag)
    return None


def _write_current_model(destination: Path, model_tag: str) -> None:
    """Replace the model pointer atomically on the shared BentoML volume."""
    if not destination.is_absolute():
        raise ModelPublicationError("CURRENT_MODEL_FILE doit être un chemin absolu")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"{model_tag}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _required_result_text(training_result: dict[str, Any], field: str) -> str:
    value = training_result.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ModelPublicationError(
            f"train-api n'a pas retourné un champ {field} exploitable"
        )
    return value


def main() -> int:
    """Run the one-shot trigger, never printing credentials or bearer tokens."""
    try:
        settings = load_settings()
        session = build_session(settings.retries)
        print("🔐 Demande d'un jeton train auprès de auth-api…")
        train_token = request_token(session, settings, "train")
        print("🚀 Déclenchement du training initial…")
        result = trigger_initial_training(session, settings, train_token)
    except ValueError as error:
        print(f"Configuration invalide : {error}", file=sys.stderr)
        return 2
    except requests.RequestException as error:
        print(f"Erreur réseau/API : {error}", file=sys.stderr)
        return 3
    except RuntimeError as error:
        print(f"Échec du déclenchement : {error}", file=sys.stderr)
        return 4

    try:
        if result["new_model"]:
            print("📦 Publication du modèle initial dans BentoML…")
            champion_source = result
        else:
            print(
                "ℹ️ Le candidat n'a pas été promu; synchronisation du "
                "champion MLflow existant vers BentoML…"
            )
            champion_source = resolve_registry_champion(settings)
        model_tag = publish_initial_model(champion_source, settings)
    except ModelPublicationError as error:
        print(f"Échec de la publication BentoML : {error}", file=sys.stderr)
        return 5

    try:
        print("🔐 Demande d'un jeton train pour le reload auprès de auth-api…")
        login_token = request_token(session, settings, "train")
        print("🔄 Rechargement du modèle dans predict-api…")
        reload_result = trigger_model_reload(session, settings, login_token)
        print(
            "✅ Modèle rechargé avec succès dans predict-api : "
            f"{reload_result}"
        )
    except (RuntimeError, requests.RequestException) as error:
        print(f"Échec du rechargement du modèle : {error}", file=sys.stderr)
        return 6

    print(
        "✅ Training initial terminé "
        f"(run MLflow: {result.get('mlflow_run_id', 'inconnu')}, "
        f"nouveau champion: {result.get('new_model', False)}, "
        f"modèle BentoML: {model_tag})"
    )
    return 0


def _raise_for_status(response: requests.Response, service_name: str) -> None:
    """Raise a concise error without including response bodies or credentials."""
    if response.ok:
        return
    raise RuntimeError(f"{service_name} a répondu HTTP {response.status_code}")


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} doit être un entier positif") from error
    if parsed < 0:
        raise ValueError(f"{name} doit être positif ou nul")
    return parsed


def _positive_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{name} doit être un nombre positif") from error
    if parsed <= 0:
        raise ValueError(f"{name} doit être strictement positif")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
