"""Application service for the first, historical training workflow."""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.train_api.config import Settings
from src.train_api.data import (
    build_initial_snapshot,
    build_training_plan,
    build_weekly_snapshot,
    create_workspace,
    prepare_runtime_volumes,
)
from src.train_api.domain import PromotionDecision, decide_promotion
from src.train_api.errors import TrainingConflict, TrainingFailed
from src.train_api.lineage import build_dataset_digest, sha256_file
from src.train_api.mlflow_service import (
    CandidateRegistration,
    LoggedModel,
    MlflowTrainingService,
)
from src.train_api.monitoring import MonitoringResult, monitor_weekly_champion
from src.train_api.schemas import TrainingResult, TrainRequest
from src.train_api.state import TrainingStateStore, build_request_fingerprint
from src.train_api.training import (
    TrainingArtifacts,
    TrainingConfig,
    load_training_config,
    run_local_training,
)
from src.train_api.monitoring_export import export_drift_results, export_ml_performance

logger = logging.getLogger(__name__)
_TRAINING_LOCK = threading.Lock()


@contextmanager
def _exclusive_training() -> Iterator[None]:
    """Reserve the single process-wide training slot without waiting."""
    if not _TRAINING_LOCK.acquire(blocking=False):
        raise TrainingConflict("Un autre entraînement est déjà en cours")
    try:
        yield
    finally:
        _TRAINING_LOCK.release()


class TrainingService:
    """Coordinate direct Python calls for idempotent initial and weekly training."""

    def __init__(
        self,
        settings: Settings,
        *,
        state_store: TrainingStateStore | None = None,
        mlflow_service: MlflowTrainingService | None = None,
        config_loader: Callable[[Path], TrainingConfig] = load_training_config,
        training_runner: Callable[..., TrainingArtifacts] = run_local_training,
        monitoring_runner: Callable[..., MonitoringResult] = monitor_weekly_champion,
    ) -> None:
        self.settings = settings
        self._state_store = state_store
        self._mlflow_service = mlflow_service
        self._config_loader = config_loader
        self._training_runner = training_runner
        self._monitoring_runner = monitoring_runner

    def train(self, request: TrainRequest) -> TrainingResult:
        """Run one training at a time across all request-scoped services."""
        with _exclusive_training():
            return self._train_exclusive(request)

    def _train_exclusive(self, request: TrainRequest) -> TrainingResult:
        """Run one training mode once, or return its persisted result."""
        execution_id = uuid.uuid4().hex
        started = time.monotonic()
        logger.info(
            "🚀 Training started execution=%s mode=%s week=%s key=%s",
            execution_id,
            request.mode,
            request.week,
            request.idempotency_key,
        )
        self.settings.require_training_configuration()
        logger.info("Preparing runtime volumes execution=%s", execution_id)
        prepare_runtime_volumes(self.settings)
        config = self._config_loader(self.settings.training_config_path)
        snapshot = self._build_snapshot(request)
        plan = build_training_plan(snapshot, period=self.settings.training_period)
        dataset_digest = build_dataset_digest(
            self._input_digests(request),
            manifest=snapshot.manifest,
            ml_config=_config_lineage(config),
        )
        fingerprint = build_request_fingerprint(
            request,
            dataset_digest=dataset_digest,
            ml_config=_config_lineage(config),
            source_git_commit=self.settings.source_git_commit,
        )
        state_store = self._get_state_store()
        reservation = state_store.reserve(request.idempotency_key, fingerprint)
        if reservation.status == "succeeded":
            assert reservation.result is not None
            logger.info(
                "✅ Idempotent result reused execution=%s key=%s run=%s",
                execution_id,
                request.idempotency_key,
                reservation.result.mlflow_run_id,
            )
            return reservation.result

        logged_model: LoggedModel | None = None
        workspace: Path | None = None
        try:
            workspace = create_workspace(self.settings)
            monitoring = None
            mlflow_service = self._get_mlflow_service()
            if request.mode == "weekly":
                monitoring = self._monitoring_runner(
                    plan,
                    settings=self.settings,
                    workspace=workspace,
                    mlflow_service=mlflow_service,
                )
            artifacts = self._training_runner(
                plan, config, workspace=workspace, write_artifacts=True
            )
            logged_model = mlflow_service.log_training(
                artifacts, plan, config, dataset_digest=dataset_digest
            )
            logger.info(
                "MLflow run opened execution=%s run=%s",
                execution_id,
                logged_model.mlflow_run_id,
            )
            candidate = mlflow_service.register_candidate(logged_model)
            if monitoring is not None:
                mlflow_service.log_weekly_monitoring(
                    logged_model.mlflow_run_id, monitoring
                )
                export_ml_performance(
                    monitoring,
                    week=request.week,
                    rows=int(plan.evaluation_mask.sum()),
                    model_name=self.settings.mlflow_registered_model_name,
                    model_alias=self.settings.mlflow_champion_alias,
                )
                export_drift_results(monitoring)
                decision = _weekly_promotion_decision(
                    candidate, monitoring, artifacts, self.settings
                )
            else:
                decision = _initial_promotion_decision(
                    candidate, mlflow_service.resolve_champion(), artifacts
                )
            mlflow_service.apply_promotion(decision)
            _publish_workspace(
                workspace, self.settings.artifact_root, logged_model.mlflow_run_id
            )
            result = _build_result(
                request,
                artifacts,
                logged_model,
                candidate,
                decision,
                dataset_digest,
                champion_metrics=None
                if monitoring is None
                else monitoring.champion_metrics,
            )
            state_store.finish_success(request.idempotency_key, fingerprint, result)
            logger.info(
                "✅ Training completed execution=%s mode=%s week=%s run=%s duration_s=%.3f",
                execution_id,
                request.mode,
                request.week,
                logged_model.mlflow_run_id,
                time.monotonic() - started,
            )
            return result
        except Exception as error:
            state_store.finish_failure(
                request.idempotency_key,
                fingerprint,
                str(error),
                mlflow_run_id=None
                if logged_model is None
                else logged_model.mlflow_run_id,
            )
            logger.exception(
                "❌ Training failed execution=%s mode=%s week=%s run=%s",
                execution_id,
                request.mode,
                request.week,
                None if logged_model is None else logged_model.mlflow_run_id,
            )
            raise
        finally:
            if workspace is not None and workspace.exists():
                shutil.rmtree(workspace, ignore_errors=True)
                logger.info("Temporary workspace cleaned execution=%s", execution_id)
  

    def _get_state_store(self) -> TrainingStateStore:
        if self._state_store is None:
            self._state_store = TrainingStateStore(self.settings.state_db_path)
        return self._state_store

    def _build_snapshot(self, request: TrainRequest):
        if request.mode == "initial":
            return build_initial_snapshot(
                self.settings, period=self.settings.training_period
            )
        assert request.week is not None
        return build_weekly_snapshot(
            self.settings, request.week, period=self.settings.training_period
        )

    def _input_digests(self, request: TrainRequest) -> list[str]:
        paths = [self.settings.base_dataset_path]
        if request.mode == "weekly":
            assert request.week is not None
            paths.extend(
                self.settings.incoming_data_dir / f"accidents_2024_w{week:02d}.parquet"
                for week in range(1, request.week + 1)
            )
        return [sha256_file(path) for path in paths]

    def _get_mlflow_service(self) -> MlflowTrainingService:
        if self._mlflow_service is None:
            self._mlflow_service = MlflowTrainingService(self.settings)
        return self._mlflow_service


def _config_lineage(config: TrainingConfig) -> dict[str, object]:
    return {
        "threshold": config.threshold,
        "feature_engineering": vars(config.feature_engineering),
        "model": dict(config.model_parameters),
    }


def _initial_promotion_decision(
    candidate: CandidateRegistration,
    champion: CandidateRegistration | None,
    artifacts: TrainingArtifacts,
) -> PromotionDecision:
    """Promote the first model only; later candidates await weekly comparison."""
    score = artifacts.metrics["pr_auc"]
    if champion is None:
        return decide_promotion(
            candidate_version=candidate.version,
            candidate_score=score,
            champion_version=None,
            champion_score=None,
            metric="pr_auc",
            min_improvement=0.0,
        )
    return PromotionDecision(
        candidate_version=candidate.version,
        champion_version=champion.version,
        candidate_score=score,
        champion_score=None,
        metric="pr_auc",
        min_improvement=0.0,
        delta=None,
        promoted=False,
        reason="candidate_below_min_improvement",
    )


def _weekly_promotion_decision(
    candidate: CandidateRegistration,
    monitoring: MonitoringResult,
    artifacts: TrainingArtifacts,
    settings: Settings,
) -> PromotionDecision:
    if monitoring.champion_version is None or monitoring.champion_metrics is None:
        return decide_promotion(
            candidate_version=candidate.version,
            candidate_score=artifacts.metrics["pr_auc"],
            champion_version=None,
            champion_score=None,
            metric="pr_auc",
            min_improvement=settings.promotion_min_improvement,
        )
    return decide_promotion(
        candidate_version=candidate.version,
        candidate_score=artifacts.metrics["pr_auc"],
        champion_version=monitoring.champion_version,
        champion_score=monitoring.champion_metrics["pr_auc"],
        metric="pr_auc",
        min_improvement=settings.promotion_min_improvement,
    )


def _publish_workspace(workspace: Path, artifact_root: Path, run_id: str) -> Path:
    """Publish local artifacts by one atomic rename on the configured volume."""
    destination = artifact_root / "runs" / run_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise TrainingFailed(f"Le répertoire d'artefacts existe déjà : {destination}")
    try:
        os.replace(workspace, destination)
    except OSError as error:
        raise TrainingFailed("Publication atomique des artefacts impossible") from error
    return destination


def _build_result(
    request: TrainRequest,
    artifacts: TrainingArtifacts,
    logged_model: LoggedModel,
    candidate: CandidateRegistration,
    decision: PromotionDecision,
    dataset_digest: str,
    champion_metrics: dict[str, float] | None,
) -> TrainingResult:
    return TrainingResult(
        mode=request.mode,
        week=request.week,
        new_model=decision.promoted,
        model_type=type(artifacts.final_model).__name__,
        model_metrics=artifacts.metrics,
        champion_metrics=champion_metrics,
        mlflow_run_id=logged_model.mlflow_run_id,
        model_uri=logged_model.model_uri,
        registered_model_name=candidate.registered_model_name,
        candidate_version=candidate.version,
        champion_version=(
            candidate.version if decision.promoted else decision.champion_version
        ),
        previous_champion_version=(
            decision.champion_version if decision.promoted else None
        ),
        promotion_reason=decision.reason,
        dataset_digest=dataset_digest,
        dvc_snapshot_path=None,
        dvc_snapshot_md5=None,
        idempotency_key=request.idempotency_key,
    )
