import pandas as pd
import pytest

from projet_accidents_mlops.weekly_data import (
    build_snapshot_from_weekly_parquets,
    build_weekly_snapshot,
    weekly_parquet_path,
)


def _source_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Num_Acc": [1, 2, 3, 3, 4, 5, 6, 7],
            "accident_date": [
                "2019-01-01",
                "2023-12-31",
                "2024-01-01",
                "2024-01-01",
                "2024-01-07",
                "2024-01-08",
                "2024-01-14",
                "2024-01-15",
            ],
            "grav": [0, 1, 2, 1, 0, 3, 0, 2],
        }
    )


def test_zero_week_snapshot_contains_only_history() -> None:
    result = build_weekly_snapshot(_source_data(), weeks_2024=0)

    assert result.data["Num_Acc"].tolist() == [1, 2]
    assert result.manifest["cutoff_exclusive"] == "2024-01-01"
    assert result.manifest["history_rows"] == 2
    assert result.manifest["rows_2024"] == 0


def test_two_week_snapshot_includes_complete_accidents_through_january_14() -> None:
    result = build_weekly_snapshot(_source_data(), weeks_2024=2)

    assert result.data["Num_Acc"].tolist() == [1, 2, 3, 3, 4, 5, 6]
    assert 7 not in result.data["Num_Acc"].tolist()
    assert result.manifest["weeks_2024"] == 2
    assert result.manifest["cutoff_exclusive"] == "2024-01-15"
    assert result.manifest["last_included_calendar_date"] == "2024-01-14"
    assert result.manifest["rows_2024"] == 5
    assert result.manifest["accidents"] == 6


@pytest.mark.parametrize("weeks", [-1, 54, 1.5, True])
def test_invalid_week_count_is_rejected(weeks) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_weekly_snapshot(_source_data(), weeks_2024=weeks)


def test_an_accident_with_multiple_dates_is_rejected() -> None:
    df = _source_data()
    df.loc[df.index == 3, "accident_date"] = "2024-01-02"

    with pytest.raises(ValueError, match="plusieurs dates"):
        build_weekly_snapshot(df, weeks_2024=2)


def test_missing_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="grav"):
        build_weekly_snapshot(
            _source_data().drop(columns=["grav"]),
            weeks_2024=1,
        )


def test_parquet_snapshot_ignores_base_2024_and_uses_received_weeks(
    tmp_path,
) -> None:
    source = _source_data().rename(columns={"grav": "grav_binaire"})
    week_1 = source[source["accident_date"].between("2024-01-01", "2024-01-07")]
    week_1.to_parquet(weekly_parquet_path(tmp_path, 1), index=False)

    result = build_snapshot_from_weekly_parquets(
        source,
        tmp_path,
        1,
        manifest_source="data/incoming",
    )

    assert result.data["Num_Acc"].tolist() == [1, 2, 3, 3, 4]
    assert result.manifest["weekly_parquet_count"] == 1
    assert result.manifest["weekly_parquet_source"] == "data/incoming"


def test_parquet_snapshot_requires_every_requested_week(tmp_path) -> None:
    source = _source_data().rename(columns={"grav": "grav_binaire"})

    with pytest.raises(FileNotFoundError, match="w01"):
        build_snapshot_from_weekly_parquets(source, tmp_path, 1)


def test_parquet_snapshot_rejects_rows_outside_the_file_window(tmp_path) -> None:
    source = _source_data().rename(columns={"grav": "grav_binaire"})
    source[source["accident_date"] == "2024-01-08"].to_parquet(
        weekly_parquet_path(tmp_path, 1),
        index=False,
    )

    with pytest.raises(ValueError, match="hors de sa fenêtre"):
        build_snapshot_from_weekly_parquets(source, tmp_path, 1)
