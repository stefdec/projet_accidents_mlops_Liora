from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.train_api.config import Settings, TrainingPeriod
from src.train_api.data import build_initial_snapshot, build_weekly_snapshot
from src.train_api.errors import DatasetInvalid, DatasetNotFound


PERIOD = TrainingPeriod(
    history_start="2019-01-01",
    start_2024="2024-01-01",
    end_2024="2024-01-22",
)


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        base_dataset_path=tmp_path / "input" / "data_final_binaire.csv",
        incoming_data_dir=tmp_path / "incoming",
        artifact_root=tmp_path / "artifacts",
        state_db_path=tmp_path / "state" / "train.sqlite3",
        tmp_dir=tmp_path / "temporary",
        training_period=PERIOD,
    )


def frame(rows: list[tuple[str, str, int]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Num_Acc", "accident_date", "grav_binaire"])


def write_base(settings: Settings, data: pd.DataFrame | None = None) -> pd.DataFrame:
    base = data if data is not None else frame(
        [
            ("history-2", "2020-02-02", 0),
            ("history-1", "2019-01-01", 1),
            ("embedded-2024", "2024-01-03", 1),
        ]
    )
    settings.base_dataset_path.parent.mkdir()
    base.to_csv(settings.base_dataset_path, index=False)
    return base


def write_week(settings: Settings, week: int, data: pd.DataFrame) -> Path:
    settings.incoming_data_dir.mkdir(exist_ok=True)
    path = settings.incoming_data_dir / f"accidents_2024_w{week:02d}.parquet"
    data.to_parquet(path, index=False)
    return path


def test_initial_snapshot_contains_only_history_and_does_not_modify_source(
    tmp_path: Path,
) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    source_before = settings.base_dataset_path.read_bytes()

    snapshot = build_initial_snapshot(settings)

    assert snapshot.data["Num_Acc"].tolist() == ["history-1", "history-2"]
    assert snapshot.manifest["mode"] == "initial"
    assert snapshot.manifest["week"] is None
    assert snapshot.manifest["weekly_parquet_count"] == 0
    assert settings.base_dataset_path.read_bytes() == source_before


def test_weekly_snapshots_are_cumulative_from_w01_to_requested_week(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    write_week(settings, 1, frame([("week-1", "2024-01-03", 1)]))
    write_week(settings, 2, frame([("week-2", "2024-01-10", 0)]))

    w01 = build_weekly_snapshot(settings, 1)
    w02 = build_weekly_snapshot(settings, 2)

    assert w01.data["Num_Acc"].tolist() == ["history-1", "history-2", "week-1"]
    assert w02.data["Num_Acc"].tolist() == [
        "history-1",
        "history-2",
        "week-1",
        "week-2",
    ]
    assert w02.manifest["weekly_files"] == [
        "accidents_2024_w01.parquet",
        "accidents_2024_w02.parquet",
    ]


def test_weekly_snapshot_requires_every_preceding_week(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    write_week(settings, 2, frame([("week-2", "2024-01-10", 0)]))

    with pytest.raises(DatasetNotFound, match="accidents_2024_w01.parquet"):
        build_weekly_snapshot(settings, 2)


def test_weekly_snapshot_rejects_rows_outside_their_week_window(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    write_week(settings, 1, frame([("week-2-data", "2024-01-10", 0)]))

    with pytest.raises(DatasetInvalid, match="hors de sa fenêtre"):
        build_weekly_snapshot(settings, 1)


@pytest.mark.parametrize(
    "weekly_data, error",
    [
        (
            pd.DataFrame(
                {"Num_Acc": ["missing-target"], "accident_date": ["2024-01-03"]}
            ),
            "Colonnes manquantes",
        ),
        (frame([("invalid-date", "not-a-date", 1)]), "Dates invalides"),
    ],
)
def test_weekly_snapshot_rejects_invalid_schema_or_dates(
    tmp_path: Path,
    weekly_data: pd.DataFrame,
    error: str,
) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    write_week(settings, 1, weekly_data)

    with pytest.raises(DatasetInvalid, match=error):
        build_weekly_snapshot(settings, 1)


def test_weekly_snapshot_rejects_duplicate_accidents_between_files(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    write_week(settings, 1, frame([("duplicated", "2024-01-03", 0)]))
    write_week(settings, 2, frame([("duplicated", "2024-01-10", 1)]))

    with pytest.raises(DatasetInvalid, match="Accidents dupliqués entre fichiers"):
        build_weekly_snapshot(settings, 2)


def test_snapshot_manifest_is_deterministic_for_identical_sources(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    write_base(settings)
    write_week(settings, 1, frame([("week-1", "2024-01-03", 1)]))

    first = build_weekly_snapshot(settings, 1)
    second = build_weekly_snapshot(settings, 1)

    assert first.manifest == second.manifest
    pd.testing.assert_frame_equal(first.data, second.data)
