"""Vérifie l'authentification et une prédiction du champion publié dans BentoML."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / os.getenv("ENV_FILE", ".env"), override=False)
AUTH_API_URL = os.getenv("AUTH_API_PUBLIC_URL", "http://127.0.0.1:8005/login")
PREDICT_API_URL = os.getenv(
    "PREDICT_API_PUBLIC_URL",
    "http://127.0.0.1:8009/predict",
)
RETRYABLE_STATUS_CODES = frozenset({502, 503, 504})


def post_with_startup_retry(
    url: str,
    *,
    startup_timeout: float,
    request_timeout: float,
    retry_interval: float = 2.0,
    **kwargs: Any,
) -> requests.Response:
    """Attend qu'un service fraîchement démarré accepte la requête HTTP."""
    deadline = time.monotonic() + startup_timeout
    last_issue = "aucune réponse"

    while True:
        try:
            response = requests.post(url, timeout=request_timeout, **kwargs)
            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            last_issue = f"HTTP {response.status_code}"
        except (requests.ConnectionError, requests.Timeout) as error:
            last_issue = str(error)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(
                f"Service indisponible après {startup_timeout:.0f} s : "
                f"{url} ({last_issue})"
            )
        time.sleep(min(retry_interval, remaining))


def sample_observation() -> dict[str, object]:
    """Charge le contrat de référence de l'API active."""
    sample_path = PROJECT_ROOT / "payload.json"
    with sample_path.open(encoding="utf-8") as sample_file:
        payload = json.load(sample_file)
    if not isinstance(payload, dict) or not isinstance(payload.get("input_data"), dict):
        raise RuntimeError(f"Exemple de prédiction invalide : {sample_path}")
    return payload


def main() -> None:
    username = os.getenv("SMOKE_USERNAME", os.getenv("AIRFLOW_SERVICE_USERNAME", ""))
    password = os.getenv("SMOKE_PASSWORD", os.getenv("AIRFLOW_SERVICE_PASSWORD", ""))
    if not username or not password:
        raise RuntimeError(
            "SMOKE_USERNAME/SMOKE_PASSWORD ou AIRFLOW_SERVICE_USERNAME/"
            "AIRFLOW_SERVICE_PASSWORD sont requis"
        )

    auth_response = post_with_startup_retry(
        AUTH_API_URL,
        startup_timeout=60,
        request_timeout=15,
        json={
            "username": username,
            "password": password,
            "token_type": "login",
        },
    )
    auth_response.raise_for_status()
    token = auth_response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("L'API d'authentification n'a retourné aucun jeton")

    prediction_response = post_with_startup_retry(
        PREDICT_API_URL,
        startup_timeout=180,
        request_timeout=60,
        headers={"Authorization": f"Bearer {token}"},
        json=sample_observation(),
    )
    prediction_response.raise_for_status()
    result = prediction_response.json()
    required = {"probability", "prediction", "model_version"}
    missing = sorted(required.difference(result))
    if missing:
        raise RuntimeError(f"Réponse de prédiction incomplète : {missing}")
    probability = result["probability"]
    if (
        result["prediction"] not in (0, 1)
        or not isinstance(probability, (int, float))
        or not 0 <= probability <= 1
    ):
        raise RuntimeError("Classe ou probabilité de prédiction invalide")
    if not result["model_version"]:
        raise RuntimeError("La version du modèle publié est absente")

    print("Predict API OK")
    print(
        f"champion_version={result['model_version']} "
        f"prediction={result['prediction']} "
        f"probability={result['probability']:.6f}"
    )


if __name__ == "__main__":
    main()
