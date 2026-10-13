import pytest

from src.train_api.config import Settings, load_settings


def test_load_settings_uses_safe_defaults_without_training_credentials() -> None:
    settings = load_settings({})

    assert settings.jwt_secret_train is None
    assert settings.mlflow_tracking_uri is None
    assert settings.jwt_algorithm == "HS256"
    assert settings.source_git_commit == "unknown"
    assert settings.monitoring_required is True


def test_training_configuration_requires_secret_and_mlflow_uri() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET_TRAIN, MLFLOW_TRACKING_URI"):
        load_settings({}).require_training_configuration()

    with pytest.raises(ValueError, match="MLFLOW_TRACKING_URI"):
        load_settings({"JWT_SECRET_TRAIN": "train-secret"}).require_training_configuration()


def test_training_configuration_accepts_required_values() -> None:
    settings = load_settings(
        {
            "JWT_SECRET_TRAIN": "train-secret",
            "MLFLOW_TRACKING_URI": "http://mlflow:5000",
        }
    )

    settings.require_training_configuration()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("YES", True),
        ("1", True),
        ("on", True),
        ("false", False),
        ("No", False),
        ("0", False),
        ("OFF", False),
    ],
)
def test_monitoring_required_parses_explicit_boolean_values(
    value: str,
    expected: bool,
) -> None:
    settings = load_settings({"MONITORING_REQUIRED": value})

    assert settings.monitoring_required is expected


def test_monitoring_required_rejects_ambiguous_values() -> None:
    with pytest.raises(ValueError, match="MONITORING_REQUIRED"):
        load_settings({"MONITORING_REQUIRED": "sometimes"})


def test_configured_paths_are_normalized_to_absolute_paths() -> None:
    settings = load_settings(
        {
            "BASE_DATASET_PATH": "inputs/base.csv",
            "INCOMING_DATA_DIR": "inputs/incoming",
            "ARTIFACT_ROOT": "runtime/artifacts",
            "STATE_DB_PATH": "runtime/state.sqlite3",
            "TMP_DIR": "runtime/tmp",
            "TRAINING_CONFIG_PATH": "config/training.yaml",
        }
    )

    assert all(
        path.is_absolute()
        for path in (
            settings.base_dataset_path,
            settings.incoming_data_dir,
            settings.artifact_root,
            settings.state_db_path,
            settings.tmp_dir,
            settings.training_config_path,
        )
    )


def test_default_tmp_dir_follows_the_configured_artifact_root() -> None:
    settings = load_settings({"ARTIFACT_ROOT": "runtime/artifacts"})

    assert settings.tmp_dir == settings.artifact_root / ".tmp"


def test_settings_are_frozen_and_do_not_expose_the_secret_in_repr() -> None:
    settings = load_settings({"JWT_SECRET_TRAIN": "do-not-log-this"})

    assert "do-not-log-this" not in repr(settings)
    with pytest.raises(AttributeError):
        settings.jwt_algorithm = "none"  # type: ignore[misc]


def test_load_settings_accepts_an_injected_mapping_without_environment_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET_TRAIN", "environment-secret")

    settings = load_settings({"JWT_SECRET_TRAIN": "injected-secret"})

    assert settings.jwt_secret_train == "injected-secret"
