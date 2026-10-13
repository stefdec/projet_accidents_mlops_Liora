from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.train_api.errors import StateStoreError, TrainingConflict
from src.train_api.schemas import TrainRequest, TrainingResult
from src.train_api.state import TrainingStateStore, build_request_fingerprint


def store_at(tmp_path: Path) -> TrainingStateStore:
    database_path = tmp_path / "state" / "train-api.sqlite3"
    database_path.parent.mkdir()
    return TrainingStateStore(database_path)


def result() -> TrainingResult:
    return TrainingResult(
        mode="initial",
        new_model=True,
        model_type="LightGBMClassifier",
        model_metrics={"pr_auc": 0.62},
        mlflow_run_id="real-mlflow-run-id",
        model_uri="runs:/real-mlflow-run-id/model",
        registered_model_name="accidents-gravity-classifier",
        candidate_version="1",
        champion_version="1",
        promotion_reason="no_existing_champion",
        dataset_digest="sha256:dataset",
        idempotency_key="initial-2024",
    )


def test_reservation_then_success_is_reused_after_store_reopen(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    fingerprint = "sha256:fingerprint"

    assert store.reserve("initial-2024", fingerprint).status == "reserved"
    store.finish_success("initial-2024", fingerprint, result())

    reopened = TrainingStateStore(store.database_path)
    reservation = reopened.reserve("initial-2024", fingerprint)

    assert reservation.status == "succeeded"
    assert reservation.result == result()
    assert reopened.get("initial-2024")["mlflow_run_id"] == "real-mlflow-run-id"


def test_reservation_rejects_fingerprint_change_and_concurrent_active_run(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.reserve("weekly-01", "sha256:one")

    with pytest.raises(TrainingConflict, match="autre empreinte"):
        store.reserve("weekly-01", "sha256:two")
    with pytest.raises(TrainingConflict, match="déjà en cours"):
        store.reserve("weekly-01", "sha256:one")


def test_two_connections_cannot_reserve_the_same_key(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    second_connection = TrainingStateStore(store.database_path)

    def reserve(current: TrainingStateStore) -> str:
        try:
            return current.reserve("weekly-02", "sha256:same").status
        except TrainingConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(reserve, [store, second_connection]))

    assert sorted(outcomes) == ["conflict", "reserved"]


def test_failed_run_can_retry_without_deleting_its_history(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.reserve("weekly-03", "sha256:retry")
    store.finish_failure(
        "weekly-03",
        "sha256:retry",
        "MLflow timeout",
        mlflow_run_id="failed-run",
    )

    retry = store.reserve("weekly-03", "sha256:retry")
    row = store.get("weekly-03")

    assert retry.status == "reserved"
    assert retry.retry_count == 1
    assert row["status"] == "running"
    assert row["last_error"] == "MLflow timeout"
    assert row["mlflow_run_id"] == "failed-run"


def test_startup_recovery_marks_running_rows_as_retryable(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.reserve("weekly-interrupted", "sha256:interrupted")
    store.reserve("weekly-already-failed", "sha256:already-failed")
    store.finish_failure(
        "weekly-already-failed",
        "sha256:already-failed",
        "Original failure",
    )

    recovered = store.recover_interrupted_runs()
    row = store.get("weekly-interrupted")
    existing_failure = store.get("weekly-already-failed")

    assert recovered == 1
    assert row is not None
    assert row["status"] == "failed"
    assert row["last_error"] == (
        "Entraînement interrompu par l'arrêt du processus API"
    )
    assert existing_failure is not None
    assert existing_failure["last_error"] == "Original failure"
    retry = store.reserve("weekly-interrupted", "sha256:interrupted")
    assert retry.status == "reserved"
    assert retry.retry_count == 1


def test_success_json_is_revalidated_before_reuse(tmp_path: Path) -> None:
    store = store_at(tmp_path)
    store.reserve("initial-invalid", "sha256:invalid")
    store.finish_success("initial-invalid", "sha256:invalid", result())
    with store._connect() as connection:  # Internal mutation deliberately simulates disk corruption.
        connection.execute(
            "UPDATE training_runs SET result_json = ? WHERE idempotency_key = ?",
            ("{}", "initial-invalid"),
        )

    with pytest.raises(StateStoreError, match="[Rr]ésultat JSON"):
        store.reserve("initial-invalid", "sha256:invalid")


def test_fingerprint_changes_with_request_dataset_config_or_commit() -> None:
    request = TrainRequest(mode="weekly", week=1, idempotency_key="weekly-01")
    base = build_request_fingerprint(
        request,
        dataset_digest="sha256:data-a",
        ml_config={"threshold": 0.48},
        source_git_commit="commit-a",
    )

    assert base != build_request_fingerprint(
        request,
        dataset_digest="sha256:data-b",
        ml_config={"threshold": 0.48},
        source_git_commit="commit-a",
    )
    assert base != build_request_fingerprint(
        request,
        dataset_digest="sha256:data-a",
        ml_config={"threshold": 0.49},
        source_git_commit="commit-a",
    )
    assert base != build_request_fingerprint(
        request,
        dataset_digest="sha256:data-a",
        ml_config={"threshold": 0.48},
        source_git_commit="commit-b",
    )
