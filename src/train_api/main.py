"""Minimal FastAPI entry point for train_api."""

import logging
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from src.train_api import __version__
from src.train_api.auth import require_train_token
from src.train_api.config import load_settings
from src.train_api.data import prepare_runtime_volumes
from src.train_api.errors import (
    DatasetInvalid,
    DatasetNotFound,
    MlflowUnavailable,
    TrainingApiError,
    TrainingConflict,
)
from src.train_api.schemas import TrainingResult, TrainRequest
from src.train_api.service import TrainingService
from src.train_api.state import TrainingStateStore

logger = logging.getLogger(__name__)


def recover_interrupted_training() -> int:
    """Recover reservations that cannot belong to the newly started process."""
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_format)
    prepare_runtime_volumes(settings)
    recovered = TrainingStateStore(settings.state_db_path).recover_interrupted_runs()
    if recovered:
        logger.warning("Recovered %s interrupted training reservation(s)", recovered)
    return recovered


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Recover crash state once, before this single API process serves requests."""
    recover_interrupted_training()
    yield


class RedactingFormatter(logging.Formatter):
    """Keep useful server traces while removing common credential forms."""

    _patterns = (
        re.compile(r"(?i)(secret|token|password|authorization)=?[^\s,]+"),
        re.compile(r"//([^:/\s]+):([^@\s]+)@"),
    )

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        rendered = self._patterns[0].sub(r"\1=[REDACTED]", rendered)
        return self._patterns[1].sub("//[REDACTED]@[", rendered).replace("@[", "@")


app = FastAPI(
    title="Projet Accidents MLOps Train API",
    description="Training API for the Accidents MLOps project.",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the HTTP process is running."""
    return {"status": "ok"}


def get_training_service() -> TrainingService:
    """Build request-scoped adapters from the runtime configuration."""
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_format)
    return TrainingService(settings)


def configure_logging(level: str, output_format: str) -> None:
    """Configure standard-library logging without introducing another framework."""
    template = (
        '{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
        if output_format == "json"
        else "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter(template))
    logging.basicConfig(level=getattr(logging, level), handlers=[handler], force=True)


@app.post("/train", response_model=TrainingResult)
def train(
    request: TrainRequest,
    _: Annotated[dict[str, object], Depends(require_train_token)],
    service: Annotated[TrainingService, Depends(get_training_service)],
) -> TrainingResult:
    """Execute the requested supported training workflow."""
    try:
        return service.train(request)
    except TrainingConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except DatasetNotFound as error:
        logger.exception(
            "❌ Dataset unavailable mode=%s week=%s key=%s",
            request.mode,
            request.week,
            request.idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset requis introuvable"
        ) from error
    except DatasetInvalid as error:
        logger.exception(
            "❌ Dataset invalid mode=%s week=%s key=%s",
            request.mode,
            request.week,
            request.idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Dataset invalide"
        ) from error
    except MlflowUnavailable as error:
        logger.exception(
            "❌ MLflow unavailable mode=%s week=%s key=%s",
            request.mode,
            request.week,
            request.idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLflow indisponible",
        ) from error
    except (TrainingApiError, ValueError) as error:
        logger.exception(
            "❌ Training request failed mode=%s week=%s key=%s",
            request.mode,
            request.week,
            request.idempotency_key,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec interne de l'entraînement",
        ) from error
