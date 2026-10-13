from __future__ import annotations

import pandas as pd
import pytest

from src.train_api.config import TrainingPeriod
from src.train_api.data import TrainingSnapshot, build_training_plan
from src.train_api.errors import DatasetInvalid


PERIOD = TrainingPeriod(
    history_start="2019-01-01",
    initial_validation_start="2023-01-01",
    start_2024="2024-01-01",
    end_2024="2025-01-01",
)


def snapshot(
    mode: str,
    week: int | None,
    rows: list[tuple[str, str]],
) -> TrainingSnapshot:
    return TrainingSnapshot(
        data=pd.DataFrame(rows, columns=["Num_Acc", "accident_date"]).assign(
            accident_date=lambda frame: pd.to_datetime(frame["accident_date"]),
            grav_binaire=0,
        ),
        manifest={"mode": mode, "week": week},
    )


def test_initial_plan_keeps_development_validation_and_full_history_refit() -> None:
    plan = build_training_plan(
        snapshot(
            "initial",
            None,
            [("train", "2022-12-31"), ("evaluation", "2023-01-01")],
        ),
        period=PERIOD,
    )

    assert plan.train_mask.tolist() == [True, False]
    assert plan.evaluation_mask.tolist() == [False, True]
    assert plan.model_fit_mask.tolist() == [True, True]
    assert plan.evaluation_start == pd.Timestamp("2023-01-01")
    assert plan.evaluation_end == pd.Timestamp("2024-01-01")


def test_weekly_plan_evaluates_only_requested_week_and_refits_through_it() -> None:
    plan = build_training_plan(
        snapshot(
            "weekly",
            2,
            [("history", "2023-12-31"), ("week-2", "2024-01-10")],
        ),
        period=PERIOD,
    )

    assert plan.train_mask.tolist() == [True, False]
    assert plan.evaluation_mask.tolist() == [False, True]
    assert plan.model_fit_mask.tolist() == [True, True]
    assert plan.evaluation_start == pd.Timestamp("2024-01-08")
    assert plan.evaluation_end == pd.Timestamp("2024-01-15")


def test_plan_rejects_an_empty_evaluation_window() -> None:
    with pytest.raises(DatasetInvalid, match="fenêtre d'évaluation"):
        build_training_plan(
            snapshot("weekly", 1, [("history", "2023-12-31")]),
            period=PERIOD,
        )


def test_plan_rejects_groups_shared_by_train_and_evaluation() -> None:
    with pytest.raises(DatasetInvalid, match="groupes sont présents"):
        build_training_plan(
            snapshot(
                "weekly",
                1,
                [("same-accident", "2023-12-31"), ("same-accident", "2024-01-03")],
            ),
            period=PERIOD,
        )


def test_plan_rejects_rows_after_the_evaluation_window() -> None:
    with pytest.raises(DatasetInvalid, match="données futures"):
        build_training_plan(
            snapshot(
                "weekly",
                1,
                [("history", "2023-12-31"), ("week-1", "2024-01-03"), ("future", "2024-01-08")],
            ),
            period=PERIOD,
        )
