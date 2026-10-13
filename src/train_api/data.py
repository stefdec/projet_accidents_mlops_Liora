"""Runtime volume boundaries and dataset path resolution."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.train_api.config import Settings, TrainingPeriod
from src.train_api.domain import TrainingMode
from src.train_api.errors import ConfigurationError, DatasetInvalid, DatasetNotFound

DATE_COLUMN = "accident_date"
GROUP_COLUMN = "Num_Acc"
TARGET_COLUMN = "grav_binaire"


@dataclass(frozen=True)
class TrainingSnapshot:
    """Validated in-memory data and deterministic metadata for one training run."""

    data: pd.DataFrame
    manifest: dict[str, object]


@dataclass(frozen=True)
class TrainingPlan:
    """Temporal masks for evaluation and for the final model refit."""

    snapshot: TrainingSnapshot
    train_mask: pd.Series
    evaluation_mask: pd.Series
    model_fit_mask: pd.Series
    mode: TrainingMode
    week: int | None
    evaluation_start: pd.Timestamp
    evaluation_end: pd.Timestamp

    @property
    def data(self) -> pd.DataFrame:
        """Expose the validated snapshot data for the future ML layer."""
        return self.snapshot.data


def validate_base_dataset(settings: Settings) -> Path:
    """Return the configured historical dataset after a read-only validation."""
    path = settings.base_dataset_path
    if not path.is_file():
        raise DatasetNotFound(f"Dataset de base introuvable : {path}")
    if not os.access(path, os.R_OK):
        raise ConfigurationError(f"Dataset de base illisible : {path}")
    return path


def prepare_runtime_volumes(settings: Settings) -> None:
    """Create only the configured runtime directories after boundary checks."""
    for directory in settings.writable_directories:
        _ensure_safe_writable_directory(directory)


def resolve_weekly_dataset(
    settings: Settings,
    week: int,
    client_file_path: str | None = None,
) -> Path:
    """Resolve WNN from the incoming volume, never from a client path."""
    if not 1 <= week <= 52:
        raise DatasetInvalid("La semaine doit être comprise entre 1 et 52")

    expected_name = f"accidents_2024_w{week:02d}.parquet"
    if client_file_path is not None and Path(client_file_path).name != expected_name:
        raise DatasetInvalid(f"Le fichier hebdomadaire doit se nommer {expected_name}")

    dataset_path = settings.incoming_data_dir / expected_name
    if not dataset_path.is_file():
        raise DatasetNotFound(f"Dataset hebdomadaire introuvable : {dataset_path}")
    if not os.access(dataset_path, os.R_OK):
        raise ConfigurationError(f"Dataset hebdomadaire illisible : {dataset_path}")
    return dataset_path


def create_workspace(settings: Settings) -> Path:
    """Create a unique temporary workspace under the configured temporary volume."""
    prepare_runtime_volumes(settings)
    return Path(tempfile.mkdtemp(prefix="run-", dir=settings.tmp_dir))


def build_initial_snapshot(
    settings: Settings,
    *,
    period: TrainingPeriod | None = None,
) -> TrainingSnapshot:
    """Build the historical-only snapshot used by the initial workflow."""
    bounds = _normalized_period(period or settings.training_period)
    base = _load_csv(validate_base_dataset(settings))
    history = _historical_rows(base, bounds)
    return _make_snapshot(history, mode="initial", week=None, bounds=bounds, files=[])


def build_weekly_snapshot(
    settings: Settings,
    week: int,
    *,
    period: TrainingPeriod | None = None,
) -> TrainingSnapshot:
    """Build history plus each required weekly Parquet from W01 through WNN."""
    if not 1 <= week <= 52:
        raise DatasetInvalid("La semaine doit être comprise entre 1 et 52")

    bounds = _normalized_period(period or settings.training_period)
    base = _load_csv(validate_base_dataset(settings))
    history = _historical_rows(base, bounds)
    columns = list(base.columns)
    frames = [history]
    seen_groups = set(history[GROUP_COLUMN].dropna())
    source_files: list[str] = []

    for current_week in range(1, week + 1):
        parquet_path = resolve_weekly_dataset(settings, current_week)
        weekly = _load_parquet(parquet_path)
        weekly = _align_weekly_columns(weekly, columns, parquet_path)
        weekly = _normalize_frame(weekly, source=parquet_path.name)
        _validate_week_window(weekly, current_week, bounds, parquet_path)
        _reject_group_overlap(weekly, seen_groups, parquet_path)
        seen_groups.update(weekly[GROUP_COLUMN].dropna())
        frames.append(weekly)
        source_files.append(parquet_path.name)

    return _make_snapshot(
        pd.concat(frames, ignore_index=True),
        mode="weekly",
        week=week,
        bounds=bounds,
        files=source_files,
    )


def build_training_plan(
    snapshot: TrainingSnapshot,
    *,
    period: TrainingPeriod,
) -> TrainingPlan:
    """Build a leakage-safe temporal plan from an already validated snapshot."""
    history_start, initial_validation_start, start_2024, end_2024 = _plan_bounds(period)
    del history_start
    mode = snapshot.manifest.get("mode")
    week = snapshot.manifest.get("week")
    if mode not in {"initial", "weekly"}:
        raise DatasetInvalid("Le snapshot ne déclare pas un mode valide")
    if mode == "initial":
        if week is not None:
            raise DatasetInvalid("Le snapshot initial ne doit pas avoir de semaine")
        evaluation_start, evaluation_end = initial_validation_start, start_2024
    else:
        if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 52:
            raise DatasetInvalid("Le snapshot weekly doit déclarer une semaine valide")
        evaluation_start = start_2024 + pd.Timedelta(7 * (week - 1), unit="D")
        evaluation_end = min(evaluation_start + pd.Timedelta(7, unit="D"), end_2024)

    dates = snapshot.data[DATE_COLUMN]
    train_mask = dates < evaluation_start
    evaluation_mask = (dates >= evaluation_start) & (dates < evaluation_end)
    future_mask = dates >= evaluation_end
    if not train_mask.any():
        raise DatasetInvalid("Le jeu d'entraînement temporel est vide")
    if not evaluation_mask.any():
        raise DatasetInvalid("La fenêtre d'évaluation temporelle est vide")
    if future_mask.any():
        raise DatasetInvalid("Le snapshot contient des données futures")

    train_groups = set(snapshot.data.loc[train_mask, GROUP_COLUMN].dropna())
    evaluation_groups = set(snapshot.data.loc[evaluation_mask, GROUP_COLUMN].dropna())
    overlap = train_groups.intersection(evaluation_groups)
    if overlap:
        raise DatasetInvalid(
            "Des groupes sont présents dans l'entraînement et l'évaluation : "
            f"{len(overlap)}"
        )

    model_fit_mask = train_mask | evaluation_mask
    return TrainingPlan(
        snapshot=snapshot,
        train_mask=train_mask,
        evaluation_mask=evaluation_mask,
        model_fit_mask=model_fit_mask,
        mode=mode,
        week=week,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
    )


def _ensure_safe_writable_directory(directory: Path) -> None:
    if _is_in_application_source_or_repository(directory):
        raise ConfigurationError(
            f"Écriture runtime interdite dans le dépôt applicatif : {directory}"
        )
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ConfigurationError(
            f"Impossible de préparer le volume runtime : {directory}"
        ) from error
    if not directory.is_dir() or not os.access(directory, os.W_OK):
        raise ConfigurationError(f"Volume runtime non inscriptible : {directory}")


def _is_in_application_source_or_repository(path: Path) -> bool:
    candidate = path.resolve(strict=False)
    source_package = Path(__file__).resolve().parent
    repository_root = source_package.parents[1]
    return _is_relative_to(candidate, source_package) or _is_relative_to(
        candidate,
        repository_root,
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _load_csv(path: Path) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, low_memory=False)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise DatasetInvalid(f"CSV historique invalide : {path}") from error
    return _normalize_frame(frame, source=path.name)


def _load_parquet(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except (OSError, ValueError, ImportError) as error:
        raise DatasetInvalid(f"Parquet hebdomadaire invalide : {path.name}") from error


def _normalize_frame(frame: pd.DataFrame, *, source: str) -> pd.DataFrame:
    required_columns = {DATE_COLUMN, GROUP_COLUMN, TARGET_COLUMN}
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        raise DatasetInvalid(f"Colonnes manquantes dans {source} : {missing_columns}")
    if frame.empty:
        raise DatasetInvalid(f"Dataset vide : {source}")

    normalized = frame.copy()
    dates = pd.to_datetime(normalized[DATE_COLUMN], errors="coerce")
    if dates.isna().any():
        raise DatasetInvalid(f"Dates invalides dans {source}")
    normalized[DATE_COLUMN] = dates.dt.tz_localize(None).dt.normalize()
    return normalized


def _historical_rows(
    frame: pd.DataFrame, bounds: tuple[pd.Timestamp, ...]
) -> pd.DataFrame:
    history_start, start_2024, _ = bounds
    history = frame.loc[
        (frame[DATE_COLUMN] >= history_start) & (frame[DATE_COLUMN] < start_2024)
    ].copy()
    if history.empty:
        raise DatasetInvalid("Le dataset historique est vide après exclusion de 2024")
    return history


def _align_weekly_columns(
    weekly: pd.DataFrame,
    base_columns: list[str],
    path: Path,
) -> pd.DataFrame:
    missing_columns = sorted(set(base_columns).difference(weekly.columns))
    if missing_columns:
        raise DatasetInvalid(
            f"Colonnes manquantes dans {path.name} : {missing_columns}"
        )
    return weekly.loc[:, base_columns].copy()


def _validate_week_window(
    weekly: pd.DataFrame,
    week: int,
    bounds: tuple[pd.Timestamp, ...],
    path: Path,
) -> None:
    _, start_2024, end_2024 = bounds
    week_start = start_2024 + pd.Timedelta(7 * (week - 1), unit="D")
    week_end = min(week_start + pd.Timedelta(7, unit="D"), end_2024)
    in_window = (weekly[DATE_COLUMN] >= week_start) & (weekly[DATE_COLUMN] < week_end)
    if not in_window.all():
        raise DatasetInvalid(f"{path.name} contient des lignes hors de sa fenêtre")


def _reject_group_overlap(
    weekly: pd.DataFrame,
    seen_groups: set[object],
    path: Path,
) -> None:
    overlap = seen_groups.intersection(set(weekly[GROUP_COLUMN].dropna()))
    if overlap:
        raise DatasetInvalid(
            f"Accidents dupliqués entre fichiers dans {path.name} : {len(overlap)}"
        )


def _make_snapshot(
    frame: pd.DataFrame,
    *,
    mode: TrainingMode,
    week: int | None,
    bounds: tuple[pd.Timestamp, ...],
    files: list[str],
) -> TrainingSnapshot:
    if frame.empty:
        raise DatasetInvalid("Le snapshot demandé est vide")
    snapshot = frame.sort_values(
        [DATE_COLUMN, GROUP_COLUMN], kind="stable"
    ).reset_index(drop=True)
    history_start, start_2024, end_2024 = bounds
    dates = snapshot[DATE_COLUMN]
    manifest: dict[str, object] = {
        "mode": mode,
        "week": week,
        "history_start": history_start.date().isoformat(),
        "start_2024": start_2024.date().isoformat(),
        "end_2024": end_2024.date().isoformat(),
        "rows": int(len(snapshot)),
        "groups": int(snapshot[GROUP_COLUMN].nunique(dropna=True)),
        "actual_min_date": dates.min().date().isoformat(),
        "actual_max_date": dates.max().date().isoformat(),
        "weekly_files": files,
        "weekly_parquet_count": len(files),
    }
    return TrainingSnapshot(data=snapshot, manifest=manifest)


def _normalized_period(period: TrainingPeriod) -> tuple[pd.Timestamp, ...]:
    try:
        history_start = pd.Timestamp(period.history_start).normalize()
        start_2024 = pd.Timestamp(period.start_2024).normalize()
        end_2024 = pd.Timestamp(period.end_2024).normalize()
    except (TypeError, ValueError) as error:
        raise ConfigurationError(
            "Bornes temporelles d'entraînement invalides"
        ) from error
    if any(pd.isna(value) for value in (history_start, start_2024, end_2024)):
        raise ConfigurationError("Bornes temporelles d'entraînement invalides")
    if not history_start < start_2024 < end_2024:
        raise ConfigurationError(
            "Les bornes doivent vérifier history_start < start_2024 < end_2024"
        )
    return history_start, start_2024, end_2024


def _plan_bounds(period: TrainingPeriod) -> tuple[pd.Timestamp, ...]:
    history_start, start_2024, end_2024 = _normalized_period(period)
    try:
        initial_validation_start = pd.Timestamp(
            period.initial_validation_start
        ).normalize()
    except (TypeError, ValueError) as error:
        raise ConfigurationError("Borne de validation initiale invalide") from error
    if pd.isna(initial_validation_start) or not (
        history_start < initial_validation_start < start_2024
    ):
        raise ConfigurationError(
            "initial_validation_start doit être entre history_start et start_2024"
        )
    return history_start, initial_validation_start, start_2024, end_2024
