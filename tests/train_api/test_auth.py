from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from src.train_api.main import app, get_training_service
from src.train_api.errors import TrainingApiError

TRAIN_SECRET = "train-secret-used-only-for-tests"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("JWT_SECRET_TRAIN", TRAIN_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    return TestClient(app)


def train_token(
    *,
    secret: str = TRAIN_SECRET,
    token_type: str = "train",
    role: str = "train",
    expires_at: datetime | None = None,
) -> str:
    return jwt.encode(
        {
            "sub": "airflow",
            "token_type": token_type,
            "role": role,
            "exp": expires_at or datetime.now(UTC) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def weekly_request() -> dict[str, object]:
    return {"mode": "weekly", "week": 1, "idempotency_key": "weekly-2024-w01"}


def test_valid_train_token_reaches_training_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class TrainingStub:
        def train(self, request):
            calls.append(request.model_dump())
            raise TrainingApiError("Controlled training failure")

    monkeypatch.setitem(app.dependency_overrides, get_training_service, TrainingStub)
    response = client.post(
        "/train",
        headers={"Authorization": f"Bearer {train_token()}"},
        json=weekly_request(),
    )

    assert len(calls) == 1
    assert calls[0]["mode"] == "weekly"
    assert calls[0]["week"] == 1
    assert response.status_code == 500
    assert response.json() == {"detail": "Échec interne de l'entraînement"}


@pytest.mark.parametrize(
    ("authorization", "detail"),
    [
        (None, "Missing authentication token"),
        ("Basic abc", "Invalid authentication scheme"),
        ("Bearer", "Invalid authentication scheme"),
        ("Bearer not-a-jwt", "Invalid token"),
    ],
)
def test_train_rejects_missing_invalid_or_malformed_bearer_tokens(
    client: TestClient,
    authorization: str | None,
    detail: str,
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}

    response = client.post("/train", headers=headers, json=weekly_request())

    assert response.status_code == 401
    assert response.json() == {"detail": detail}
    assert response.headers["www-authenticate"] == "Bearer"


def test_train_rejects_an_expired_token(client: TestClient) -> None:
    response = client.post(
        "/train",
        headers={
            "Authorization": (
                f"Bearer {train_token(expires_at=datetime.now(UTC) - timedelta(minutes=1))}"
            )
        },
        json=weekly_request(),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Token has expired"}


def test_train_rejects_a_token_signed_with_another_secret(client: TestClient) -> None:
    response = client.post(
        "/train",
        headers={
            "Authorization": (
                "Bearer "
                f"{train_token(secret='another-train-secret-with-at-least-32-bytes')}"
            )
        },
        json=weekly_request(),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize(
    ("token_type", "role"),
    [("pull", "pull"), ("login", "train"), ("train", "predict")],
)
def test_train_rejects_tokens_without_train_claims(
    client: TestClient,
    token_type: str,
    role: str,
) -> None:
    response = client.post(
        "/train",
        headers={"Authorization": f"Bearer {train_token(token_type=token_type, role=role)}"},
        json=weekly_request(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient token claims"}


def test_health_remains_public(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_train_reports_a_safe_configuration_error_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JWT_SECRET_TRAIN", raising=False)
    client = TestClient(app)

    response = client.post(
        "/train",
        headers={"Authorization": f"Bearer {train_token()}"},
        json=weekly_request(),
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Training authentication is not configured"}
    assert TRAIN_SECRET not in response.text
