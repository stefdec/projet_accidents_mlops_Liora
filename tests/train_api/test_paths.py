from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.train_api.config import Settings
from src.train_api.data import (
    create_workspace,
    prepare_runtime_volumes,
    resolve_weekly_dataset,
    validate_base_dataset,
)
from src.train_api.errors import ConfigurationError, DatasetInvalid, DatasetNotFound


def runtime_settings(tmp_path: Path, **overrides: Path) -> Settings:
    values: dict[str, Path] = {
        "base_dataset_path": tmp_path / "input" / "data_final_binaire.csv",
        "incoming_data_dir": tmp_path / "incoming",
        "artifact_root": tmp_path / "artifacts",
        "state_db_path": tmp_path / "state" / "train-api.sqlite3",
        "tmp_dir": tmp_path / "temporary",
    }
    values.update(overrides)
    return Settings(**values)


def test_validate_base_dataset_returns_existing_readable_file(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)
    settings.base_dataset_path.parent.mkdir()
    settings.base_dataset_path.touch()

    assert validate_base_dataset(settings) == settings.base_dataset_path


def test_validate_base_dataset_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DatasetNotFound, match="Dataset de base introuvable"):
        validate_base_dataset(runtime_settings(tmp_path))


@pytest.mark.parametrize("week", [1, 52])
def test_resolve_weekly_dataset_uses_the_configured_incoming_volume(
    tmp_path: Path,
    week: int,
) -> None:
    settings = runtime_settings(tmp_path)
    settings.incoming_data_dir.mkdir()
    expected = settings.incoming_data_dir / f"accidents_2024_w{week:02d}.parquet"
    expected.touch()

    assert resolve_weekly_dataset(settings, week) == expected


@pytest.mark.parametrize("week", [0, 53])
def test_resolve_weekly_dataset_rejects_invalid_week(tmp_path: Path, week: int) -> None:
    with pytest.raises(DatasetInvalid, match="1 et 52"):
        resolve_weekly_dataset(runtime_settings(tmp_path), week)


def test_resolve_weekly_dataset_rejects_a_client_filename_for_another_week(
    tmp_path: Path,
) -> None:
    settings = runtime_settings(tmp_path)

    with pytest.raises(DatasetInvalid, match="accidents_2024_w07.parquet"):
        resolve_weekly_dataset(settings, 7, "/untrusted/accidents_2024_w08.parquet")


def test_resolve_weekly_dataset_uses_only_client_basename(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)
    settings.incoming_data_dir.mkdir()
    expected = settings.incoming_data_dir / "accidents_2024_w07.parquet"
    expected.touch()
    client_path = tmp_path / "untrusted" / "accidents_2024_w07.parquet"

    assert resolve_weekly_dataset(settings, 7, str(client_path)) == expected
    assert not client_path.exists()


def test_resolve_weekly_dataset_reports_missing_expected_file(tmp_path: Path) -> None:
    with pytest.raises(DatasetNotFound, match="Dataset hebdomadaire introuvable"):
        resolve_weekly_dataset(runtime_settings(tmp_path), 1)


def test_prepare_runtime_volumes_creates_only_configured_directories(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)

    prepare_runtime_volumes(settings)

    assert all(directory.is_dir() for directory in settings.writable_directories)
    assert not settings.base_dataset_path.parent.exists()
    assert not settings.incoming_data_dir.exists()


def test_create_workspace_creates_a_unique_directory_under_tmp_dir(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)

    workspace = create_workspace(settings)

    assert workspace.is_dir()
    assert workspace.parent == settings.tmp_dir


def test_workspace_uses_the_artifact_filesystem_for_atomic_publication(
    tmp_path: Path,
) -> None:
    settings = runtime_settings(
        tmp_path,
        tmp_dir=tmp_path / "artifacts" / ".tmp",
    )

    workspace = create_workspace(settings)

    assert os.stat(workspace).st_dev == os.stat(settings.artifact_root).st_dev


def test_prepare_runtime_volumes_rejects_an_output_inside_source_package() -> None:
    source_package = Path(__file__).resolve().parents[2] / "src" / "train_api"
    settings = Settings(
        artifact_root=source_package / "runtime-artifacts",
        state_db_path=Path("/tmp/train-api-test/state.sqlite3"),
        tmp_dir=Path("/tmp/train-api-test/tmp"),
    )

    with pytest.raises(ConfigurationError, match="dépôt applicatif"):
        prepare_runtime_volumes(settings)
