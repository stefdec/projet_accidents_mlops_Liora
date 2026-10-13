"""SQLite-backed idempotence state for a single train_api replica."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from src.train_api.errors import StateStoreError, TrainingConflict
from src.train_api.schemas import TrainingResult, TrainRequest

StateStatus = Literal["running", "succeeded", "failed"]


@dataclass(frozen=True)
class Reservation:
    """Outcome of an atomic attempt to reserve one idempotency key."""

    status: Literal["reserved", "succeeded"]
    result: TrainingResult | None = None
    retry_count: int = 0


class TrainingStateStore:
    """Short SQLite transactions; model training is always executed outside them."""

    def __init__(self, database_path: Path) -> None:
        if not database_path.parent.is_dir():
            raise StateStoreError(
                f"Le parent de STATE_DB_PATH doit exister : {database_path.parent}"
            )
        self.database_path = database_path
        self.initialize()

    def initialize(self) -> None:
        """Create the versioned schema safely when it does not exist yet."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS training_runs (
                    idempotency_key TEXT PRIMARY KEY,
                    request_fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
                    mlflow_run_id TEXT,
                    result_json TEXT,
                    last_error TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute("PRAGMA user_version = 1")

    def reserve(self, idempotency_key: str, request_fingerprint: str) -> Reservation:
        """Atomically reserve a run, reuse success, or retry a previous failure."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM training_runs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            now = _utc_now()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO training_runs (
                        idempotency_key, request_fingerprint, status, created_at, updated_at
                    ) VALUES (?, ?, 'running', ?, ?)
                    """,
                    (idempotency_key, request_fingerprint, now, now),
                )
                return Reservation(status="reserved")
            if row["request_fingerprint"] != request_fingerprint:
                raise TrainingConflict(
                    "Clé d'idempotence réutilisée avec une autre empreinte"
                )
            if row["status"] == "succeeded":
                return Reservation(
                    status="succeeded",
                    result=_parse_result(row["result_json"]),
                    retry_count=row["retry_count"],
                )
            if row["status"] == "running":
                raise TrainingConflict("Une exécution avec cette clé est déjà en cours")
            retry_count = row["retry_count"] + 1
            connection.execute(
                """
                UPDATE training_runs
                SET status = 'running', retry_count = ?, updated_at = ?
                WHERE idempotency_key = ?
                """,
                (retry_count, now, idempotency_key),
            )
            return Reservation(status="reserved", retry_count=retry_count)

    def finish_success(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        result: TrainingResult,
    ) -> None:
        """Persist a schema-validated success for a currently reserved key."""
        self._finish(
            idempotency_key,
            request_fingerprint,
            status="succeeded",
            mlflow_run_id=result.mlflow_run_id,
            result_json=result.model_dump_json(),
            last_error=None,
        )

    def finish_failure(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        error: str,
        *,
        mlflow_run_id: str | None = None,
    ) -> None:
        """Persist a failed attempt while retaining the row for a future retry."""
        self._finish(
            idempotency_key,
            request_fingerprint,
            status="failed",
            mlflow_run_id=mlflow_run_id,
            result_json=None,
            last_error=error,
        )

    def recover_interrupted_runs(self) -> int:
        """Mark reservations inherited from a crashed process as retryable failures."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE training_runs
                SET status = 'failed',
                    result_json = NULL,
                    last_error = ?,
                    updated_at = ?
                WHERE status = 'running'
                """,
                (
                    "Entraînement interrompu par l'arrêt du processus API",
                    _utc_now(),
                ),
            )
            return cursor.rowcount

    def get(self, idempotency_key: str) -> sqlite3.Row | None:
        """Read one state row for orchestration or tests without mutating it."""
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM training_runs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()

    def _finish(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        *,
        status: StateStatus,
        mlflow_run_id: str | None,
        result_json: str | None,
        last_error: str | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_fingerprint, status FROM training_runs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None or row["request_fingerprint"] != request_fingerprint:
                raise TrainingConflict("Impossible de finaliser une clé non réservée")
            if row["status"] != "running":
                raise TrainingConflict("Seule une exécution active peut être finalisée")
            connection.execute(
                """
                UPDATE training_runs
                SET status = ?, mlflow_run_id = ?, result_json = ?, last_error = ?, updated_at = ?
                WHERE idempotency_key = ?
                """,
                (
                    status,
                    mlflow_run_id,
                    result_json,
                    last_error,
                    _utc_now(),
                    idempotency_key,
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path, timeout=5, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        return connection


def build_request_fingerprint(
    request: TrainRequest,
    *,
    dataset_digest: str,
    ml_config: Mapping[str, object],
    source_git_commit: str,
) -> str:
    """Build a canonical fingerprint from normalized request, data, ML, and code."""
    payload = {
        "request": request.model_dump(mode="json", exclude_none=False),
        "dataset_digest": dataset_digest,
        "ml_config": dict(ml_config),
        "source_git_commit": source_git_commit,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _parse_result(raw_result: str | None) -> TrainingResult:
    if raw_result is None:
        raise StateStoreError("Succès idempotent sans résultat JSON")
    try:
        return TrainingResult.model_validate_json(raw_result)
    except ValidationError as error:
        raise StateStoreError("Résultat JSON idempotent invalide") from error


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
