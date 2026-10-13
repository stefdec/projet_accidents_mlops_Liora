"""Runtime configuration for train_api."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_DATASET_PATH = "/var/lib/train-api/input/data_final_binaire.csv"
DEFAULT_INCOMING_DATA_DIR = "/var/lib/train-api/incoming"
DEFAULT_ARTIFACT_ROOT = "/var/lib/train-api/artifacts"
DEFAULT_STATE_DB_PATH = "/var/lib/train-api/state/train-api.sqlite3"
DEFAULT_TMP_DIR = f"{DEFAULT_ARTIFACT_ROOT}/.tmp"
DEFAULT_TRAINING_CONFIG_PATH = "/app/src/train_api/training_config.yaml"


@dataclass(frozen=True)
class TrainingPeriod:
    """Immutable temporal bounds for the historical and weekly datasets."""

    history_start: str = "2019-01-01"
    initial_validation_start: str = "2023-01-01"
    start_2024: str = "2024-01-01"
    end_2024: str = "2025-01-01"


@dataclass(frozen=True)
class Settings:
    """Configuration loaded from environment variables without side effects."""

    jwt_secret_train: str | None = field(default=None, repr=False)
    jwt_algorithm: str = "HS256"
    base_dataset_path: Path = Path(DEFAULT_BASE_DATASET_PATH)
    incoming_data_dir: Path = Path(DEFAULT_INCOMING_DATA_DIR)
    artifact_root: Path = Path(DEFAULT_ARTIFACT_ROOT)
    state_db_path: Path = Path(DEFAULT_STATE_DB_PATH)
    tmp_dir: Path = Path(DEFAULT_TMP_DIR)
    mlflow_tracking_uri: str | None = None
    mlflow_experiment_name: str = "accidents-gravity"
    mlflow_registered_model_name: str = "accidents-gravity-classifier"
    mlflow_champion_alias: str = "champion"
    source_git_commit: str = "unknown"
    monitoring_required: bool = True
    promotion_min_improvement: float = 0.0
    log_level: str = "INFO"
    log_format: str = "text"
    training_config_path: Path = Path(DEFAULT_TRAINING_CONFIG_PATH)
    training_period: TrainingPeriod = field(default_factory=TrainingPeriod)

    @property
    def writable_directories(self) -> tuple[Path, Path, Path]:
        """Configured directories that may receive runtime state."""
        return (self.artifact_root, self.state_db_path.parent, self.tmp_dir)

    def require_training_configuration(self) -> None:
        """Reject missing values that are only needed for a training request."""
        missing = [
            name
            for name, value in {
                "JWT_SECRET_TRAIN": self.jwt_secret_train,
                "MLFLOW_TRACKING_URI": self.mlflow_tracking_uri,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Configuration d'entraînement incomplète : " + ", ".join(missing)
            )


def load_settings(environment: Mapping[str, str] | None = None) -> Settings:
    """Load settings without creating directories or contacting external services."""
    values = os.environ if environment is None else environment
    artifact_root = _absolute_path(
        values.get("ARTIFACT_ROOT"), DEFAULT_ARTIFACT_ROOT
    )

    return Settings(
        jwt_secret_train=_optional_text(values.get("JWT_SECRET_TRAIN")),
        jwt_algorithm=_text_or_default(values.get("JWT_ALGORITHM"), "HS256"),
        base_dataset_path=_absolute_path(
            values.get("BASE_DATASET_PATH"),
            DEFAULT_BASE_DATASET_PATH,
        ),
        incoming_data_dir=_absolute_path(
            values.get("INCOMING_DATA_DIR"),
            DEFAULT_INCOMING_DATA_DIR,
        ),
        artifact_root=artifact_root,
        state_db_path=_absolute_path(
            values.get("STATE_DB_PATH"),
            DEFAULT_STATE_DB_PATH,
        ),
        tmp_dir=_absolute_path(
            values.get("TMP_DIR"), str(artifact_root / ".tmp")
        ),
        mlflow_tracking_uri=_optional_text(values.get("MLFLOW_TRACKING_URI")),
        mlflow_experiment_name=_text_or_default(
            values.get("MLFLOW_EXPERIMENT_NAME"),
            "accidents-gravity",
        ),
        mlflow_registered_model_name=_text_or_default(
            values.get("MLFLOW_REGISTERED_MODEL_NAME"),
            "accidents-gravity-classifier",
        ),
        mlflow_champion_alias=_text_or_default(
            values.get("MLFLOW_CHAMPION_ALIAS"),
            "champion",
        ),
        source_git_commit=_text_or_default(
            values.get("SOURCE_GIT_COMMIT"),
            "unknown",
        ),
        monitoring_required=_parse_bool(
            values.get("MONITORING_REQUIRED"),
            default=True,
        ),
        promotion_min_improvement=_non_negative_float(
            values.get("PROMOTION_MIN_IMPROVEMENT"), default=0.0
        ),
        log_level=_log_level(values.get("LOG_LEVEL")),
        log_format=_log_format(values.get("LOG_FORMAT")),
        training_config_path=_absolute_path(
            values.get("TRAINING_CONFIG_PATH"),
            DEFAULT_TRAINING_CONFIG_PATH,
        ),
    )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _text_or_default(value: str | None, default: str) -> str:
    return _optional_text(value) or default


def _absolute_path(value: str | None, default: str) -> Path:
    return Path(_text_or_default(value, default)).expanduser().absolute()


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("MONITORING_REQUIRED doit être un booléen explicite")


def _non_negative_float(value: str | None, *, default: float) -> float:
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError("PROMOTION_MIN_IMPROVEMENT doit être un nombre") from error
    if parsed < 0:
        raise ValueError("PROMOTION_MIN_IMPROVEMENT doit être positif ou nul")
    return parsed


def _log_level(value: str | None) -> str:
    level = _text_or_default(value, "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("LOG_LEVEL est invalide")
    return level


def _log_format(value: str | None) -> str:
    output = _text_or_default(value, "text").lower()
    if output not in {"text", "json"}:
        raise ValueError("LOG_FORMAT doit être text ou json")
    return output
