"""Shared domain types and promotion rules for the training workflow."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

TrainingMode = Literal["initial", "weekly"]
PromotionReason = Literal[
    "no_existing_champion",
    "candidate_improved_on_same_window",
    "candidate_below_min_improvement",
]


@dataclass(frozen=True)
class PromotionDecision:
    """Pure comparison of candidate and champion scores from one window."""

    candidate_version: str
    champion_version: str | None
    candidate_score: float
    champion_score: float | None
    metric: str
    min_improvement: float
    delta: float | None
    promoted: bool
    reason: PromotionReason


def decide_promotion(
    *,
    candidate_version: str,
    candidate_score: float,
    champion_version: str | None,
    champion_score: float | None,
    metric: str,
    min_improvement: float,
) -> PromotionDecision:
    """Decide promotion from two explicit scores measured on the same window."""
    if not metric:
        raise ValueError("La métrique de promotion est obligatoire")
    if min_improvement < 0:
        raise ValueError("min_improvement doit être positif ou nul")
    if champion_version is None or champion_score is None:
        return PromotionDecision(
            candidate_version=candidate_version,
            champion_version=None,
            candidate_score=candidate_score,
            champion_score=None,
            metric=metric,
            min_improvement=min_improvement,
            delta=None,
            promoted=True,
            reason="no_existing_champion",
        )
    precise_delta = Decimal(str(candidate_score)) - Decimal(str(champion_score))
    delta = float(precise_delta)
    promoted = precise_delta > Decimal(str(min_improvement))
    return PromotionDecision(
        candidate_version=candidate_version,
        champion_version=champion_version,
        candidate_score=candidate_score,
        champion_score=champion_score,
        metric=metric,
        min_improvement=min_improvement,
        delta=delta,
        promoted=promoted,
        reason=(
            "candidate_improved_on_same_window"
            if promoted
            else "candidate_below_min_improvement"
        ),
    )
