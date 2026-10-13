import jwt
from fastapi.testclient import TestClient

from src.auth_api.main import app


def _configure_auth(monkeypatch) -> None:
    monkeypatch.setenv("USERS", '{"airflow":"test-password"}')
    monkeypatch.setenv("ADMIN_USERS", '["airflow"]')
    monkeypatch.setenv("PULL_USERS", '["airflow"]')
    monkeypatch.setenv("TRAIN_USERS", '["airflow"]')
    monkeypatch.setenv("JWT_SECRET_LOGIN", "login-secret-with-at-least-32-bytes")
    monkeypatch.setenv("JWT_SECRET_PULL", "pull-secret-with-at-least-32-bytes")
    monkeypatch.setenv("JWT_SECRET_TRAIN", "train-secret-with-at-least-32-bytes")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")


def test_auth_api_issues_scoped_train_token(monkeypatch) -> None:
    _configure_auth(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/login",
            json={
                "username": "airflow",
                "password": "test-password",
                "token_type": "train",
            },
        )

    assert response.status_code == 200
    payload = jwt.decode(
        response.json()["access_token"],
        "train-secret-with-at-least-32-bytes",
        algorithms=["HS256"],
    )
    assert payload["username"] == "airflow"
    assert payload["token_type"] == "train"
    assert payload["role"] == "train"


def test_auth_api_rejects_train_token_for_unauthorized_user(monkeypatch) -> None:
    _configure_auth(monkeypatch)
    monkeypatch.setenv("TRAIN_USERS", "[]")

    with TestClient(app) as client:
        response = client.post(
            "/login",
            json={
                "username": "airflow",
                "password": "test-password",
                "token_type": "train",
            },
        )

    assert response.status_code == 403
