from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from src.train_api.main import app, get_training_service
from src.train_api.schemas import TrainingResult


def _train_token() -> str:
    return jwt.encode(
        {
            "sub": "airflow", "token_type": "train", "role": "train",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "train-secret-used-only-for-tests",
        algorithm="HS256",
    )


def test_authenticated_initial_returns_service_result(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_TRAIN", "train-secret-used-only-for-tests")
    result = TrainingResult(
        mode="initial", new_model=True, model_type="ThresholdedBinaryClassifier",
        model_metrics={"pr_auc": 0.8}, mlflow_run_id="run-123", model_uri="runs:/run-123/model",
        registered_model_name="accidents", candidate_version="7", champion_version="7",
        promotion_reason="no_existing_champion", dataset_digest="sha256:test", idempotency_key="initial-1",
    )

    class FakeService:
        def train(self, _request):
            return result

    app.dependency_overrides[get_training_service] = lambda: FakeService()
    try:
        response = TestClient(app).post(
            "/train", json={"mode": "initial", "idempotency_key": "initial-1"},
            headers={"Authorization": f"Bearer {_train_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["mlflow_run_id"] == "run-123"
    assert response.json()["dvc_snapshot_path"] is None
