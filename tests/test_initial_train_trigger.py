from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.inital_train import main as trigger


def settings(tmp_path: Path) -> trigger.TriggerSettings:
    return trigger.TriggerSettings(
        auth_api_url="http://auth/login",
        train_api_url="http://train/train",
        predict_api_url="http://predict/reload",
        username="alice",
        password="secret",
        idempotency_key="initial-1",
        retries=3,
        connect_timeout_seconds=1,
        auth_timeout_seconds=2,
        train_timeout_seconds=3,
        mlflow_tracking_uri="http://mlflow:5001",
        mlflow_registered_model_name="accidents-gravity-classifier",
        mlflow_champion_alias="champion",
        bento_model_name="accidents",
        current_model_file=tmp_path / "bentoml" / "current_model.txt",
    )


def training_result() -> dict[str, object]:
    return {
        "status": "success",
        "new_model": True,
        "mlflow_run_id": "run-123",
        "model_uri": "runs:/run-123/model",
        "model_type": "ThresholdedBinaryClassifier",
    }


def test_load_settings_configures_bentoml_publication() -> None:
    loaded = trigger.load_settings(
        {
            "TRAIN_USERNAME": "alice",
            "TRAIN_PASSWORD": "secret",
            "INITIAL_IDEMPOTENCY_KEY": "initial-1",
        }
    )

    assert loaded.mlflow_tracking_uri == "http://mlflow-server:5001"
    assert loaded.bento_model_name == "accidents"
    assert loaded.current_model_file == Path("/bentoml/current_model.txt")
    assert loaded.predict_api_url == "http://predict-api:8000/reload"
    assert loaded.mlflow_registered_model_name == "accidents-gravity-classifier"
    assert loaded.mlflow_champion_alias == "champion"


def test_http_session_retries_network_failures_but_not_error_responses() -> None:
    session = trigger.build_session(3)
    policy = session.adapters["http://"].max_retries

    assert policy.connect == 3
    assert policy.read == 3
    assert policy.status == 0
    assert not policy.status_forcelist


def test_publish_imports_exact_model_and_updates_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured = settings(tmp_path)
    imported = SimpleNamespace(tag="accidents:new-tag")
    import_calls: list[dict[str, object]] = []
    tracking_uris: list[str] = []
    monkeypatch.setattr(trigger.bento_models, "list", lambda _name: [])
    monkeypatch.setattr(
        trigger.bentoml_mlflow,
        "import_model",
        lambda **kwargs: import_calls.append(kwargs) or imported,
    )
    monkeypatch.setattr(trigger.mlflow, "set_tracking_uri", tracking_uris.append)

    tag = trigger.publish_initial_model(training_result(), configured)

    assert tag == "accidents:new-tag"
    assert tracking_uris == ["http://mlflow:5001"]
    assert import_calls == [
        {
            "name": "accidents",
            "model_uri": "runs:/run-123/model",
            "labels": {
                "mlflow_run_id": "run-123",
                "model_type": "ThresholdedBinaryClassifier",
            },
        }
    ]
    assert configured.current_model_file.read_text(encoding="utf-8") == (
        "accidents:new-tag\n"
    )


def test_publish_reuses_model_imported_for_the_same_mlflow_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured = settings(tmp_path)
    existing = SimpleNamespace(
        tag="accidents:existing",
        info=SimpleNamespace(labels={"mlflow_run_id": "run-123"}),
    )
    monkeypatch.setattr(trigger.bento_models, "list", lambda _name: [existing])
    monkeypatch.setattr(trigger.mlflow, "set_tracking_uri", lambda _uri: None)

    def unexpected_import(**_kwargs: object) -> None:
        raise AssertionError("an idempotent retry must not import a duplicate")

    monkeypatch.setattr(trigger.bentoml_mlflow, "import_model", unexpected_import)

    tag = trigger.publish_initial_model(training_result(), configured)

    assert tag == "accidents:existing"
    assert configured.current_model_file.read_text(encoding="utf-8") == (
        "accidents:existing\n"
    )


def test_resolve_registry_champion_returns_an_exact_version_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured = settings(tmp_path)
    tracking_uris: list[str] = []

    class Client:
        def get_model_version_by_alias(self, name: str, alias: str) -> object:
            assert name == configured.mlflow_registered_model_name
            assert alias == configured.mlflow_champion_alias
            return SimpleNamespace(version="2", run_id="champion-run")

    monkeypatch.setattr(trigger.mlflow, "set_tracking_uri", tracking_uris.append)
    monkeypatch.setattr(trigger.mlflow, "MlflowClient", lambda _uri: Client())

    assert trigger.resolve_registry_champion(configured) == {
        "mlflow_run_id": "champion-run",
        "model_uri": "models:/accidents-gravity-classifier/2",
        "model_type": "registry_champion",
    }
    assert tracking_uris == [configured.mlflow_tracking_uri]


def test_failed_import_does_not_replace_current_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured = settings(tmp_path)
    configured.current_model_file.parent.mkdir(parents=True)
    configured.current_model_file.write_text("accidents:champion\n", encoding="utf-8")
    monkeypatch.setattr(trigger.bento_models, "list", lambda _name: [])
    monkeypatch.setattr(trigger.mlflow, "set_tracking_uri", lambda _uri: None)
    monkeypatch.setattr(
        trigger.bentoml_mlflow,
        "import_model",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("MLflow unavailable")),
    )

    with pytest.raises(trigger.ModelPublicationError, match="publier"):
        trigger.publish_initial_model(training_result(), configured)

    assert configured.current_model_file.read_text(encoding="utf-8") == (
        "accidents:champion\n"
    )


def test_atomic_pointer_write_rejects_relative_path() -> None:
    with pytest.raises(trigger.ModelPublicationError, match="chemin absolu"):
        trigger._write_current_model(Path("current_model.txt"), "accidents:tag")


def test_main_returns_distinct_code_when_bentoml_publication_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trigger, "load_settings", lambda: settings(tmp_path))
    monkeypatch.setattr(trigger, "build_session", lambda _retries: object())
    monkeypatch.setattr(trigger, "request_token", lambda *_args: "token")
    monkeypatch.setattr(
        trigger, "trigger_initial_training", lambda *_args: training_result()
    )
    monkeypatch.setattr(
        trigger,
        "publish_initial_model",
        lambda *_args: (_ for _ in ()).throw(
            trigger.ModelPublicationError("registry unavailable")
        ),
    )

    assert trigger.main() == 5


class _Response:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self) -> object:
        return self._payload


def test_trigger_model_reload_accepts_predict_api_response(tmp_path: Path) -> None:
    configured = settings(tmp_path)

    class Session:
        def post(self, url: str, **kwargs: object) -> _Response:
            assert url == configured.predict_api_url
            assert kwargs["headers"] == {"Authorization": "Bearer login-token"}
            return _Response(200, {"status": "Model reloaded successfully"})

    assert trigger.trigger_model_reload(Session(), configured, "login-token") == {
        "status": "Model reloaded successfully"
    }


def test_main_returns_six_on_reload_network_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trigger, "load_settings", lambda: settings(tmp_path))
    monkeypatch.setattr(trigger, "build_session", lambda _retries: object())
    monkeypatch.setattr(trigger, "request_token", lambda *_args: "token")
    monkeypatch.setattr(
        trigger, "trigger_initial_training", lambda *_args: training_result()
    )
    monkeypatch.setattr(trigger, "publish_initial_model", lambda *_args: "accidents:tag")
    monkeypatch.setattr(
        trigger,
        "trigger_model_reload",
        lambda *_args: (_ for _ in ()).throw(trigger.requests.ConnectionError()),
    )

    assert trigger.main() == 6


def test_main_synchronizes_registry_champion_when_candidate_is_not_promoted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = training_result() | {"new_model": False}
    champion = training_result() | {
        "mlflow_run_id": "champion-run",
        "model_uri": "models:/accidents-gravity-classifier/2",
        "model_type": "registry_champion",
    }
    published: list[dict[str, object]] = []
    monkeypatch.setattr(trigger, "load_settings", lambda: settings(tmp_path))
    monkeypatch.setattr(trigger, "build_session", lambda _retries: object())
    monkeypatch.setattr(trigger, "request_token", lambda *_args: "token")
    monkeypatch.setattr(trigger, "trigger_initial_training", lambda *_args: result)
    monkeypatch.setattr(trigger, "resolve_registry_champion", lambda *_args: champion)
    monkeypatch.setattr(
        trigger,
        "publish_initial_model",
        lambda source, _settings: published.append(source) or "accidents:champion",
    )
    monkeypatch.setattr(
        trigger,
        "trigger_model_reload",
        lambda *_args: {"status": "Model reloaded successfully"},
    )

    assert trigger.main() == 0
    assert published == [champion]
