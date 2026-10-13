from __future__ import annotations

from fastapi.testclient import TestClient

from src.train_api.main import app, get_training_service
from src.train_api.schemas import TrainingResult
from tests.train_api.test_initial_api import _train_token


def test_weekly_api_returns_common_training_contract(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_TRAIN", "train-secret-used-only-for-tests")
    result = TrainingResult(mode="weekly", week=1, new_model=False, model_type="ThresholdedBinaryClassifier", model_metrics={"pr_auc": 0.5}, champion_metrics={"pr_auc": 0.6}, mlflow_run_id="run", model_uri="runs:/run/model", registered_model_name="accidents", candidate_version="9", champion_version="8", promotion_reason="candidate_below_min_improvement", dataset_digest="sha256:test", idempotency_key="weekly-1")
    app.dependency_overrides[get_training_service] = lambda: type("Service", (), {"train": lambda _self, _request: result})()
    try:
        response = TestClient(app).post("/train", json={"mode": "weekly", "week": 1, "idempotency_key": "weekly-1"}, headers={"Authorization": f"Bearer {_train_token()}"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["champion_metrics"] == {"pr_auc": 0.6}
