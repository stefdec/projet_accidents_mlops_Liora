"""Construction déterministe des snapshots hebdomadaires de simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from numbers import Integral
from pathlib import Path

import pandas as pd


DateLike = str | date | datetime | pd.Timestamp
WEEKLY_PARQUET_TEMPLATE = "accidents_2024_w{week:02d}.parquet"


@dataclass(frozen=True)
class WeeklySnapshot:
    """Dataset cumulatif et description de sa fenêtre temporelle."""

    data: pd.DataFrame
    manifest: dict[str, object]


def build_weekly_snapshot(
    df: pd.DataFrame,
    weeks_2024: int,
    *,
    history_start: DateLike = "2019-01-01",
    start_2024: DateLike = "2024-01-01",
    end_2024: DateLike = "2025-01-01",
    date_column: str = "accident_date",
    group_column: str = "Num_Acc",
    target_column: str | None = "grav",
) -> WeeklySnapshot:
    """Retourne 2019-2023 enrichi des premières semaines de 2024.

    La semaine 1 couvre ``[2024-01-01, 2024-01-08)``. La borne finale est
    toujours exclusive. Avec ``weeks_2024=0``, seules les données historiques
    antérieures à 2024 sont retournées.

    La fonction filtre le dataset source sans concaténation : elle ne peut donc
    pas introduire de doublons. Elle vérifie également qu'un même accident ne
    possède pas plusieurs dates, condition nécessaire pour ne jamais couper un
    ``Num_Acc`` entre deux snapshots.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("build_weekly_snapshot attend un DataFrame pandas")

    if isinstance(weeks_2024, bool) or not isinstance(weeks_2024, Integral):
        raise TypeError("weeks_2024 doit être un entier")
    weeks_2024 = int(weeks_2024)
    if weeks_2024 < 0:
        raise ValueError("weeks_2024 doit être positif ou nul")

    required_columns = {date_column, group_column}
    if target_column is not None:
        required_columns.add(target_column)
    missing = sorted(required_columns.difference(df.columns))
    if missing:
        raise ValueError(f"Colonnes du snapshot manquantes : {missing}")

    history_start_ts = _normalise_date(history_start, "history_start")
    start_2024_ts = _normalise_date(start_2024, "start_2024")
    end_2024_ts = _normalise_date(end_2024, "end_2024")

    if not history_start_ts < start_2024_ts < end_2024_ts:
        raise ValueError(
            "Les bornes doivent vérifier history_start < start_2024 < end_2024"
        )

    max_weeks = math.ceil((end_2024_ts - start_2024_ts).days / 7)
    if weeks_2024 > max_weeks:
        raise ValueError(
            f"weeks_2024 ne peut pas dépasser {max_weeks} pour cette période"
        )

    dates = pd.to_datetime(df[date_column], errors="coerce").dt.normalize()
    invalid_date_count = int(dates.isna().sum())
    if invalid_date_count:
        raise ValueError(
            f"{invalid_date_count} date(s) invalide(s) dans {date_column}"
        )

    group_dates = pd.DataFrame(
        {
            group_column: df[group_column],
            "_snapshot_date": dates,
        }
    )
    inconsistent_groups = int(
        group_dates.groupby(group_column, dropna=False)["_snapshot_date"]
        .nunique()
        .gt(1)
        .sum()
    )
    if inconsistent_groups:
        raise ValueError(
            f"{inconsistent_groups} accident(s) possèdent plusieurs dates"
        )

    requested_end = start_2024_ts + pd.to_timedelta(7 * weeks_2024, unit="D")
    cutoff_exclusive = min(requested_end, end_2024_ts)
    snapshot_mask = (dates >= history_start_ts) & (dates < cutoff_exclusive)

    snapshot = df.loc[snapshot_mask].copy()
    if snapshot.empty:
        raise ValueError("Le snapshot demandé est vide")

    snapshot[date_column] = dates.loc[snapshot_mask].to_numpy()
    snapshot = snapshot.sort_values(
        [date_column, group_column],
        kind="stable",
    ).reset_index(drop=True)

    snapshot_dates = pd.to_datetime(snapshot[date_column])
    rows_2024 = int((snapshot_dates >= start_2024_ts).sum())
    history_rows = int((snapshot_dates < start_2024_ts).sum())

    manifest: dict[str, object] = {
        "weeks_2024": weeks_2024,
        "history_start": history_start_ts.date().isoformat(),
        "start_2024": start_2024_ts.date().isoformat(),
        "cutoff_exclusive": cutoff_exclusive.date().isoformat(),
        "last_included_calendar_date": (
            cutoff_exclusive - pd.to_timedelta(1, unit="D")
        ).date().isoformat(),
        "rows": int(len(snapshot)),
        "history_rows": history_rows,
        "rows_2024": rows_2024,
        "accidents": int(snapshot[group_column].nunique(dropna=True)),
        "actual_min_date": snapshot_dates.min().date().isoformat(),
        "actual_max_date": snapshot_dates.max().date().isoformat(),
    }
    if target_column is not None:
        manifest["target_non_null_rows"] = int(
            snapshot[target_column].notna().sum()
        )

    return WeeklySnapshot(data=snapshot, manifest=manifest)


def weekly_parquet_path(incoming_dir: str | Path, week: int) -> Path:
    """Retourne le chemin contractuel d'une semaine reçue par l'API."""
    if isinstance(week, bool) or not isinstance(week, Integral):
        raise TypeError("week doit être un entier")
    week = int(week)
    if not 1 <= week <= 52:
        raise ValueError("week doit être compris entre 1 et 52")
    return Path(incoming_dir) / WEEKLY_PARQUET_TEMPLATE.format(week=week)


def build_snapshot_from_weekly_parquets(
    base_df: pd.DataFrame,
    incoming_dir: str | Path,
    weeks_2024: int,
    *,
    manifest_source: str | None = None,
    history_start: DateLike = "2019-01-01",
    start_2024: DateLike = "2024-01-01",
    end_2024: DateLike = "2025-01-01",
    date_column: str = "accident_date",
    group_column: str = "Num_Acc",
    target_column: str | None = "grav_binaire",
) -> WeeklySnapshot:
    """Construit un snapshot uniquement depuis l'historique et les Parquet reçus.

    Les lignes 2024 éventuellement présentes dans ``base_df`` sont ignorées. En
    mode hebdomadaire, chaque fichier W01 à WN est obligatoire et doit contenir
    uniquement les dates de sa propre fenêtre. Cette contrainte évite qu'un
    entraînement accède par erreur aux semaines futures du dataset complet.
    """
    if isinstance(weeks_2024, bool) or not isinstance(weeks_2024, Integral):
        raise TypeError("weeks_2024 doit être un entier")
    weeks_2024 = int(weeks_2024)
    if not 0 <= weeks_2024 <= 52:
        raise ValueError("weeks_2024 doit être compris entre 0 et 52")
    if date_column not in base_df.columns:
        raise ValueError(f"Colonne temporelle absente : {date_column}")

    start_2024_ts = _normalise_date(start_2024, "start_2024")
    end_2024_ts = _normalise_date(end_2024, "end_2024")
    base_dates = pd.to_datetime(base_df[date_column], errors="coerce").dt.normalize()
    invalid_base_dates = int(base_dates.isna().sum())
    if invalid_base_dates:
        raise ValueError(
            f"{invalid_base_dates} date(s) invalide(s) dans le dataset de base"
        )

    history = base_df.loc[base_dates < start_2024_ts].copy()
    history[date_column] = base_dates.loc[history.index].to_numpy()
    frames = [history]
    seen_groups: set[object] = set()

    for week in range(1, weeks_2024 + 1):
        parquet_path = weekly_parquet_path(incoming_dir, week)
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Parquet hebdomadaire manquant : {parquet_path}"
            )

        weekly = pd.read_parquet(parquet_path)
        missing_columns = sorted(set(base_df.columns).difference(weekly.columns))
        if missing_columns:
            raise ValueError(
                f"Colonnes manquantes dans {parquet_path.name} : {missing_columns}"
            )
        weekly = weekly.loc[:, list(base_df.columns)].copy()
        weekly_dates = pd.to_datetime(
            weekly[date_column], errors="coerce"
        ).dt.normalize()
        if weekly_dates.isna().any():
            raise ValueError(f"Dates invalides dans {parquet_path.name}")

        week_start = start_2024_ts + pd.to_timedelta(7 * (week - 1), unit="D")
        week_end = min(
            week_start + pd.to_timedelta(7, unit="D"),
            end_2024_ts,
        )
        outside_window = ~weekly_dates.between(
            week_start,
            week_end,
            inclusive="left",
        )
        if outside_window.any():
            raise ValueError(
                f"{parquet_path.name} contient des lignes hors de sa fenêtre"
            )
        if weekly.empty:
            raise ValueError(f"Parquet hebdomadaire vide : {parquet_path.name}")

        weekly_groups = set(weekly[group_column].dropna())
        overlap = seen_groups.intersection(weekly_groups)
        if overlap:
            raise ValueError(
                "Des accidents sont dupliqués entre plusieurs Parquet : "
                f"{len(overlap)} groupe(s)"
            )
        seen_groups.update(weekly_groups)
        weekly[date_column] = weekly_dates.to_numpy()
        frames.append(weekly)

    combined = pd.concat(frames, ignore_index=True)
    snapshot = build_weekly_snapshot(
        combined,
        weeks_2024,
        history_start=history_start,
        start_2024=start_2024,
        end_2024=end_2024,
        date_column=date_column,
        group_column=group_column,
        target_column=target_column,
    )
    snapshot.manifest["weekly_parquet_count"] = weeks_2024
    snapshot.manifest["weekly_parquet_source"] = (
        manifest_source
        if manifest_source is not None
        else str(Path(incoming_dir))
    )
    return snapshot


def _normalise_date(value: DateLike, parameter_name: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{parameter_name} est invalide") from error

    if pd.isna(timestamp):
        raise ValueError(f"{parameter_name} est invalide")
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()
