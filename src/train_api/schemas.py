"""HTTP contracts shared by the train_api workflow."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.train_api.domain import PromotionReason, TrainingMode


class TrainRequest(BaseModel):
    """A request for an initial or weekly training run."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: TrainingMode
    week: int | None = Field(default=None, ge=1, le=52)
    file_path: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("idempotency_key")
    @classmethod
    def idempotency_key_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("idempotency_key ne peut pas être vide")
        return value

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "TrainRequest":
        if self.mode == "initial":
            if self.week is not None or self.file_path is not None:
                raise ValueError(
                    "Le mode initial n'accepte ni semaine ni fichier hebdomadaire"
                )
            return self

        if self.week is None:
            raise ValueError("Le mode weekly exige une semaine")
        return self


class TrainingResult(BaseModel):
    """Stable success response returned to Airflow after a training run."""

    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=(),
        str_strip_whitespace=True,
    )

    status: Literal["success"] = "success"
    mode: TrainingMode
    week: int | None = Field(default=None, ge=1, le=52)
    new_model: bool
    model_type: str = Field(min_length=1)
    model_metrics: dict[str, float]
    champion_metrics: dict[str, float] | None = None
    mlflow_run_id: str = Field(min_length=1)
    model_uri: str = Field(min_length=1)
    registered_model_name: str = Field(min_length=1)
    candidate_version: str = Field(min_length=1)
    champion_version: str | None = None
    previous_champion_version: str | None = None
    promotion_reason: PromotionReason
    dataset_digest: str = Field(min_length=1)
    dvc_snapshot_path: str | None = None
    dvc_snapshot_md5: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_period(self) -> "TrainingResult":
        if self.mode == "initial" and self.week is not None:
            raise ValueError("week doit être nul en mode initial")
        if self.mode == "weekly" and self.week is None:
            raise ValueError("week est obligatoire en mode weekly")
        return self
