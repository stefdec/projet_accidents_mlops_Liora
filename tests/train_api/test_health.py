from pathlib import Path

from fastapi.testclient import TestClient

from src.train_api import main as main_module
from src.train_api.config import Settings
from src.train_api.state import TrainingStateStore


client = TestClient(main_module.app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_exposes_health_and_the_protected_train_skeleton() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/train" in paths


def test_lifespan_recovers_interrupted_reservations(
    tmp_path: Path, monkeypatch
) -> None:
    state_path = tmp_path / "state" / "train-api.sqlite3"
    state_path.parent.mkdir()
    store = TrainingStateStore(state_path)
    store.reserve("weekly-crashed", "sha256:crashed")
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        state_db_path=state_path,
        tmp_dir=tmp_path / "artifacts" / ".tmp",
    )
    monkeypatch.setattr(main_module, "load_settings", lambda: settings)

    with TestClient(main_module.app):
        pass

    row = store.get("weekly-crashed")
    assert row is not None
    assert row["status"] == "failed"
