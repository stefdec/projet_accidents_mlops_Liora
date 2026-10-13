"""Explicit MLflow adapter for locally computed training artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature

from src.train_api.config import Settings
from src.train_api.data import DATE_COLUMN, TARGET_COLUMN, TrainingPlan
from src.train_api.domain import PromotionDecision
from src.train_api.errors import (
    ConfigurationError,
    MlflowUnavailable,
    TrainingFailed,
)
from src.train_api.lineage import source_lineage
from src.train_api.training import TrainingArtifacts, TrainingConfig

MODEL_PIP_REQUIREMENTS = [
    "cloudpickle",
    "lightgbm==4.7.0",
    "mlflow==3.15.2",
    "numpy==2.5.2",
    "pandas==2.3.3",
    "scikit-learn==1.9.0",
]


@dataclass(frozen=True)
class LoggedModel:
    """References produced by one successfully closed MLflow run."""

    mlflow_run_id: str
    model_uri: str
    model_info: Any


@dataclass(frozen=True)
class CandidateRegistration:
    """Registry reference for a model candidate recorded from one MLflow run."""

    registered_model_name: str
    version: str


@dataclass(frozen=True)
class ChampionModel:
    """Exact Registry champion and the model loaded from that version."""

    registered_model_name: str
    version: str
    mlflow_run_id: str
    model: Any


class MlflowTrainingService:
    """Log a complete local training result to a configured MLflow server."""

    def __init__(self, settings: Settings) -> None:
        if not settings.mlflow_tracking_uri:
            raise ConfigurationError("MLFLOW_TRACKING_URI est obligatoire pour MLflow")
        self.settings = settings

    def log_training(
        self,
        artifacts: TrainingArtifacts,
        plan: TrainingPlan,
        config: TrainingConfig,
        *,
        dataset_digest: str,
    ) -> LoggedModel:
        """Open a run, log inputs and artifacts, then return its true run ID."""
        try:
            mlflow.set_tracking_uri(self.settings.mlflow_tracking_uri)
            mlflow.set_experiment(self.settings.mlflow_experiment_name)
            with mlflow.start_run(run_name=_run_name(plan)) as active_run:
                run_id = active_run.info.run_id
                self._log_metadata(plan, config, artifacts, dataset_digest)
                self._log_input(plan)
                self._log_optional_artifacts(artifacts)
                input_example = plan.data.drop(
                    columns=[DATE_COLUMN, TARGET_COLUMN]
                ).head(3)
                signature = infer_signature(
                    input_example,
                    artifacts.final_model.predict(input_example),
                )
                model_info = mlflow.sklearn.log_model(
                    artifacts.final_model,
                    name="model",
                    signature=signature,
                    input_example=input_example,
                    code_paths=[str(Path(__file__).resolve().parents[1])],
                    serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
                    pip_requirements=MODEL_PIP_REQUIREMENTS,
                )
                return LoggedModel(
                    mlflow_run_id=run_id,
                    model_uri=f"runs:/{run_id}/model",
                    model_info=model_info,
                )
        except MlflowException as error:
            raise MlflowUnavailable(
                "MLflow est indisponible ou a refusé le run"
            ) from error
        except Exception as error:
            raise TrainingFailed("Échec du journalisation du run MLflow") from error

    def register_candidate(self, logged_model: LoggedModel) -> CandidateRegistration:
        """Create a Registry version without changing the champion alias."""
        try:
            registered = mlflow.register_model(
                logged_model.model_uri,
                self.settings.mlflow_registered_model_name,
            )
            client = mlflow.MlflowClient(self.settings.mlflow_tracking_uri)
            client.set_model_version_tag(
                self.settings.mlflow_registered_model_name,
                registered.version,
                "role",
                "candidate",
            )
            return CandidateRegistration(
                registered_model_name=self.settings.mlflow_registered_model_name,
                version=registered.version,
            )
        except MlflowException as error:
            raise MlflowUnavailable("MLflow Registry est indisponible") from error

    def resolve_champion(self) -> CandidateRegistration | None:
        """Return the current alias target, if one has already been promoted."""
        client = mlflow.MlflowClient(self.settings.mlflow_tracking_uri)
        try:
            champion = client.get_model_version_by_alias(
                self.settings.mlflow_registered_model_name,
                self.settings.mlflow_champion_alias,
            )
        except MlflowException:
            return None
        return CandidateRegistration(
            registered_model_name=self.settings.mlflow_registered_model_name,
            version=champion.version,
        )

    def load_champion(self) -> ChampionModel | None:
        """Resolve the alias once and load precisely that registered version."""
        client = mlflow.MlflowClient(self.settings.mlflow_tracking_uri)
        try:
            version = client.get_model_version_by_alias(
                self.settings.mlflow_registered_model_name,
                self.settings.mlflow_champion_alias,
            )
            model = mlflow.sklearn.load_model(
                f"models:/{self.settings.mlflow_registered_model_name}/{version.version}"
            )
        except MlflowException as error:
            if "alias" in str(error).lower() or "not found" in str(error).lower():
                return None
            raise MlflowUnavailable("Impossible de charger le champion MLflow") from error
        except Exception as error:
            raise MlflowUnavailable("Impossible de charger le champion MLflow") from error
        return ChampionModel(
            registered_model_name=self.settings.mlflow_registered_model_name,
            version=version.version,
            mlflow_run_id=version.run_id,
            model=model,
        )

    def apply_promotion(self, decision: PromotionDecision) -> None:
        """Move the alias and tags only when the precomputed decision promotes."""
        if not decision.promoted:
            return
        client = mlflow.MlflowClient(self.settings.mlflow_tracking_uri)
        try:
            model_name = self.settings.mlflow_registered_model_name
            client.set_model_version_tag(
                model_name, decision.candidate_version, "role", "champion"
            )
            if decision.champion_version is not None:
                client.set_model_version_tag(
                    model_name, decision.champion_version, "role", "archived"
                )
            client.set_registered_model_alias(
                model_name,
                self.settings.mlflow_champion_alias,
                decision.candidate_version,
            )
        except MlflowException as error:
            raise MlflowUnavailable(
                "Impossible de promouvoir la version MLflow"
            ) from error

    def log_weekly_monitoring(self, run_id: str, result: Any) -> None:
        """Associate already computed monitoring facts with this candidate run."""
        try:
            client = mlflow.MlflowClient(self.settings.mlflow_tracking_uri)
            client.set_tag(run_id, "monitoring.available", str(result.available).lower())
            if result.champion_version is not None:
                client.set_tag(run_id, "monitoring.champion_version", result.champion_version)
            if result.champion_mlflow_run_id is not None:
                client.set_tag(run_id, "monitoring.champion_run_id", result.champion_mlflow_run_id)
            if result.champion_metrics:
                for name, value in result.champion_metrics.items():
                    client.log_metric(run_id, f"champion_{name}", value)
            if result.drift_detected is not None:
                client.log_metric(run_id, "drift_detected", float(result.drift_detected))
            if result.drift_report_path and result.drift_report_path.is_file():
                client.log_artifact(run_id, str(result.drift_report_path), "monitoring")
        except MlflowException as error:
            raise MlflowUnavailable("Impossible de journaliser le monitoring MLflow") from error

    def _log_metadata(
        self,
        plan: TrainingPlan,
        config: TrainingConfig,
        artifacts: TrainingArtifacts,
        dataset_digest: str,
    ) -> None:
        mlflow.log_params(
            {
                "mode": plan.mode,
                "week": plan.week if plan.week is not None else 0,
                "classification_threshold": config.threshold,
                **{
                    f"model.{key}": value
                    for key, value in config.model_parameters.items()
                },
            }
        )
        mlflow.set_tags(
            {
                "mode": plan.mode,
                "week": "" if plan.week is None else str(plan.week),
                "dataset_digest": dataset_digest,
                **source_lineage(self.settings),
            }
        )
        mlflow.log_metrics(artifacts.metrics)
        if artifacts.emissions_kg is not None:
            mlflow.log_metric("emissions_kg", artifacts.emissions_kg)
        mlflow.log_dict(artifacts.manifest, "snapshot_manifest.json")

    @staticmethod
    def _log_input(plan: TrainingPlan) -> None:
        model_fit = plan.data.loc[plan.model_fit_mask].copy()
        dataset = mlflow.data.from_pandas(model_fit, source="train_api:model_fit")
        mlflow.log_input(dataset, context="training")

    @staticmethod
    def _log_optional_artifacts(artifacts: TrainingArtifacts) -> None:
        for path in (
            artifacts.report_path,
            artifacts.figure_path,
            artifacts.model_path,
        ):
            if path is not None and path.is_file():
                mlflow.log_artifact(str(path), artifact_path="local")


def _run_name(plan: TrainingPlan) -> str:
    if plan.mode == "initial":
        return "train-api-initial"
    return f"train-api-weekly-w{plan.week:02d}"
