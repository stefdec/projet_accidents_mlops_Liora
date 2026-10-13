from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.train_api.errors import (
    DatasetInvalid,
    DatasetNotFound,
    MlflowUnavailable,
    TrainingConflict,
)
from src.train_api.main import app, get_training_service
from tests.train_api.test_initial_api import _train_token


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (DatasetNotFound("/secret/data.csv"), 404, "Dataset requis introuvable"),
        (DatasetInvalid("/secret/data.csv"), 422, "Dataset invalide"),
        (MlflowUnavailable("postgres://user:password@host"), 503, "MLflow indisponible"),
        (
            TrainingConflict("Un autre entraînement est déjà en cours"),
            409,
            "Un autre entraînement est déjà en cours",
        ),
    ],
)
def test_domain_errors_have_safe_stable_http_responses(monkeypatch, error, status_code, detail) -> None:
    monkeypatch.setenv("JWT_SECRET_TRAIN", "train-secret-used-only-for-tests")
    app.dependency_overrides[get_training_service] = lambda: type("Service", (), {"train": lambda _self, _request: (_ for _ in ()).throw(error)})()
    try:
        response = TestClient(app, raise_server_exceptions=False).post("/train", json={"mode": "initial", "idempotency_key": "safe-error"}, headers={"Authorization": f"Bearer {_train_token()}"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text
    assert "password" not in response.text
