import pytest
from pydantic import ValidationError

from src.train_api.schemas import TrainRequest, TrainingResult


def _result_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "mode": "weekly",
        "week": 7,
        "new_model": True,
        "model_type": "LightGBMClassifier",
        "model_metrics": {"pr_auc": 0.62},
        "champion_metrics": {"pr_auc": 0.59},
        "mlflow_run_id": "run-123",
        "model_uri": "runs:/run-123/model",
        "registered_model_name": "accidents-gravity-classifier",
        "candidate_version": "8",
        "champion_version": "8",
        "previous_champion_version": "7",
        "promotion_reason": "candidate_improved_on_same_window",
        "dataset_digest": "sha256:dataset-digest",
        "idempotency_key": "weekly-2024-w07",
    }
    payload.update(overrides)
    return payload


def test_initial_request_is_valid_without_week_or_file_path() -> None:
    request = TrainRequest(mode="initial", idempotency_key="initial-2019-2023")

    assert request.mode == "initial"
    assert request.week is None
    assert request.file_path is None


def test_weekly_request_is_valid_without_file_path() -> None:
    request = TrainRequest(mode="weekly", week=7, idempotency_key="weekly-2024-w07")

    assert request.week == 7
    assert request.file_path is None


def test_weekly_request_keeps_legacy_file_path_for_airflow_compatibility() -> None:
    request = TrainRequest(
        mode="weekly",
        week=7,
        file_path="/shared-data/accidents_2024_w07.parquet",
        idempotency_key="weekly-2024-w07",
    )

    assert request.file_path == "/shared-data/accidents_2024_w07.parquet"


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "initial", "week": 1, "idempotency_key": "initial"},
        {
            "mode": "initial",
            "file_path": "/shared-data/week.parquet",
            "idempotency_key": "initial",
        },
        {"mode": "weekly", "idempotency_key": "weekly"},
        {"mode": "weekly", "week": 0, "idempotency_key": "weekly"},
        {"mode": "weekly", "week": 53, "idempotency_key": "weekly"},
        {"mode": "weekly", "week": 1, "idempotency_key": "   "},
    ],
)
def test_request_rejects_invalid_mode_field_combinations(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        TrainRequest.model_validate(payload)


def test_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TrainRequest.model_validate(
            {
                "mode": "initial",
                "idempotency_key": "initial",
                "unexpected": True,
            }
        )


def test_weekly_result_is_valid() -> None:
    result = TrainingResult.model_validate(_result_payload())

    assert result.status == "success"
    assert result.mlflow_run_id == "run-123"
    assert result.dataset_digest == "sha256:dataset-digest"


def test_initial_result_is_valid_without_champion_metrics() -> None:
    result = TrainingResult.model_validate(
        _result_payload(
            mode="initial",
            week=None,
            champion_metrics=None,
            champion_version=None,
            previous_champion_version=None,
            idempotency_key="initial-2019-2023",
        )
    )

    assert result.mode == "initial"
    assert result.champion_metrics is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"mlflow_run_id": ""},
        {"mlflow_run_id": "   "},
        {"mode": "initial", "week": 1},
        {"mode": "weekly", "week": None},
        {"unexpected": True},
    ],
)
def test_result_rejects_invalid_success_contract(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        TrainingResult.model_validate(_result_payload(**overrides))
