import hashlib
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bentoml
import mlflow
import requests
from airflow.exceptions import AirflowFailException
from airflow.operators.python import get_current_context
from airflow.sdk import dag, task
from bentoml import mlflow as bentoml_mlflow
from bentoml import models as bento_models
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DAG_DOCUMENTATION = """
## Flux partagé de réentraînement hebdomadaire des accidents.

Ce DAG :

1. Récupère les données brutes des accidents de la semaine en cours.
2. Versionne et sauvegarde le lot hebdomadaire dans le remote DVC.
3. Transmet le lot à l'API de training.
4. Évalue les résultats retournés par l'API de training.
5. Publie et recharge le modèle lorsqu'un nouveau champion est promu.
"""
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TriggerSettings:
    """Configuration runtime du déclencheur hebdomadaire."""

    auth_api_url: str
    pull_api_url: str
    train_api_url: str
    predict_api_url: str
    pull_user: str
    pull_password: str
    train_user: str
    train_password: str
    retries: int
    connect_timeout_seconds: float
    auth_timeout_seconds: float
    pull_timeout_seconds: float
    train_timeout_seconds: float
    mlflow_tracking_uri: str
    bento_model_name: str
    current_model_file: Path


class ModelPublicationError(RuntimeError):
    """Signale l'échec de publication du modèle entraîné dans BentoML."""


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} doit être un entier positif ou nul") from error
    if parsed < 0:
        raise ValueError(f"{name} doit être un entier positif ou nul")
    return parsed


def _positive_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{name} doit être un nombre positif") from error
    if parsed <= 0:
        raise ValueError(f"{name} doit être strictement positif")
    return parsed


def load_settings(environment: dict[str, str] | None = None) -> TriggerSettings:
    """Charge et valide la configuration depuis l'environnement du worker."""
    values = os.environ if environment is None else environment
    required = (
        "PULL_USERNAME",
        "PULL_PASSWORD",
        "TRAIN_USERNAME",
        "TRAIN_PASSWORD",
    )
    missing = [name for name in required if not values.get(name, "").strip()]
    if missing:
        raise ValueError("Variables obligatoires absentes : " + ", ".join(missing))

    return TriggerSettings(
        auth_api_url=values.get("AUTH_API_URL", "http://auth-api:8000/login"),
        pull_api_url=values.get("PULL_API_URL", "http://pull-data-api:8000/pull_data"),
        train_api_url=values.get("TRAIN_API_URL", "http://train-api:8000/train"),
        predict_api_url=values.get(
            "PREDICT_API_URL", "http://predict-api:8000/reload"
        ),
        pull_user=values["PULL_USERNAME"],
        pull_password=values["PULL_PASSWORD"],
        train_user=values["TRAIN_USERNAME"],
        train_password=values["TRAIN_PASSWORD"],
        retries=_positive_int(values.get("API_RETRIES", "3"), "API_RETRIES"),
        connect_timeout_seconds=_positive_float(
            values.get("API_CONNECT_TIMEOUT_SECONDS", "10"),
            "API_CONNECT_TIMEOUT_SECONDS",
        ),
        auth_timeout_seconds=_positive_float(
            values.get("AUTH_API_TIMEOUT_SECONDS", "30"),
            "AUTH_API_TIMEOUT_SECONDS",
        ),
        pull_timeout_seconds=_positive_float(
            values.get("PULL_API_TIMEOUT_SECONDS", "7200"),
            "PULL_API_TIMEOUT_SECONDS",
        ),
        train_timeout_seconds=_positive_float(
            values.get("TRAIN_API_TIMEOUT_SECONDS", "7200"),
            "TRAIN_API_TIMEOUT_SECONDS",
        ),
        mlflow_tracking_uri=values.get(
            "MLFLOW_TRACKING_URI", "http://mlflow-server:5001"
        ),
        bento_model_name=values.get("BENTO_MODEL_NAME", "accidents"),
        current_model_file=Path(
            values.get("CURRENT_MODEL_FILE", "/bentoml/current_model.txt")
        ),
    )


def build_session(retries: int) -> requests.Session:
    """Construit une session avec retry des erreurs HTTP transitoires."""
    policy = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=policy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def request_token(
    session: requests.Session,
    settings: TriggerSettings,
    token_type: str,
) -> str:
    """Demande un JWT limité au type d'opération demandé."""
    if token_type not in ("pull", "train"):
        raise AirflowFailException(f"Invalid token type: {token_type}")
    if token_type == "pull":
        user = settings.pull_user
        password = settings.pull_password
    elif token_type == "train":
        user = settings.train_user
        password = settings.train_password

    payload = {
        "username": user,
        "password": password,
        "token_type": token_type,
    }
    print(f"Requesting {token_type} token with payload: {payload}")

    response = session.post(
        settings.auth_api_url,
        json=payload,
        timeout=(settings.connect_timeout_seconds, settings.auth_timeout_seconds),
    )
    _raise_for_status(response, "Authentication")
    try:
        response_data = response.json()
        auth_token = response_data["access_token"]
    except (KeyError, TypeError, ValueError) as error:
        raise AirflowFailException(
            "Authentication response contains no valid access token"
        ) from error
    if not isinstance(auth_token, str) or not auth_token.strip():
        raise AirflowFailException(
            "Authentication response contains no valid access token"
        )
    return auth_token.strip()


def _raise_for_status(response: requests.Response, operation: str) -> None:
    """Rejette sans retry les erreurs HTTP fonctionnelles permanentes."""
    if 400 <= response.status_code < 500 and response.status_code != 429:
        logger.error(
            "%s rejected with non-retryable HTTP status %s",
            operation,
            response.status_code,
        )
        raise AirflowFailException(
            f"{operation} rejected with HTTP status {response.status_code}"
        )

    response.raise_for_status()


def trigger_weekly_data_pull(
    session: requests.Session,
    settings: TriggerSettings,
    token: str,
    week: int,
) -> dict:
    """Collecte et valide le fichier de données d'une semaine 2024."""
    if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 52:
        raise AirflowFailException("week doit être un entier compris entre 1 et 52")

    response = session.get(
        settings.pull_api_url,
        params={"week": week},
        headers={"Authorization": f"Bearer {token}"},
        timeout=(settings.connect_timeout_seconds, settings.pull_timeout_seconds),
    )
    _raise_for_status(response, "Data collection")
    try:
        payload = response.json()
    except ValueError as error:
        raise AirflowFailException(
            "pull-data-api returned an invalid JSON response"
        ) from error

    required_text_fields = ("start_date", "end_date_exclusive", "file_path")
    valid_text_fields = (
        all(
            isinstance(payload.get(field), str) and payload[field].strip()
            for field in required_text_fields
        )
        if isinstance(payload, dict)
        else False
    )
    if (
        not isinstance(payload, dict)
        or payload.get("week") != week
        or not valid_text_fields
        or isinstance(payload.get("record_count"), bool)
        or not isinstance(payload.get("record_count"), int)
        or payload["record_count"] < 0
    ):
        raise AirflowFailException("pull-data-api returned an unusable response")
    return payload


@task(
    retries=3,
    retry_delay=timedelta(minutes=2),
)
def pull_data(week: int | str) -> dict:
    """Tâche : récupère les données hebdomadaires des accidents."""
    try:
        resolved_week = int(week)
    except (TypeError, ValueError) as error:
        raise AirflowFailException(
            "week doit être un entier compris entre 1 et 52"
        ) from error

    settings = load_settings()
    session = build_session(settings.retries)
    auth_token = request_token(session, settings, "pull")
    data = trigger_weekly_data_pull(session, settings, auth_token, resolved_week)

    logger.info(
        "Pull data details - Week: %s, Start: %s, End exclusive: %s, "
        "File path: %s, Record count: %s",
        data["week"],
        data["start_date"],
        data["end_date_exclusive"],
        data["file_path"],
        data["record_count"],
    )
    return data


def _weekly_dvc_paths(
    pull_result: dict[str, Any], project_root: Path
) -> tuple[Path, Path]:
    """Valide le résultat de collecte et retourne les cibles DVC locales."""
    week = pull_result.get("week")
    api_file_path = pull_result.get("file_path")
    if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 52:
        raise AirflowFailException("pull_data n'a pas retourné une semaine valide")
    if not isinstance(api_file_path, str) or not api_file_path.strip():
        raise AirflowFailException("pull_data n'a pas retourné un file_path valide")

    expected_name = f"accidents_2024_w{week:02d}.parquet"
    if Path(api_file_path).name != expected_name:
        raise AirflowFailException(
            "pull_data a retourné un nom de fichier inattendu pour la semaine"
        )

    resolved_root = project_root.resolve()
    data_path = (resolved_root / "data" / "incoming" / expected_name).resolve()
    try:
        relative_data_path = data_path.relative_to(resolved_root)
    except ValueError as error:
        raise AirflowFailException(
            "Le fichier collecté est hors du dépôt DVC"
        ) from error
    if not data_path.is_file():
        raise AirflowFailException(
            f"Le fichier collecté est introuvable dans le worker : {relative_data_path}"
        )
    return relative_data_path, Path(f"{relative_data_path}.dvc")


def push_weekly_data_to_dvc(pull_result: dict[str, Any], project_root: Path) -> Path:
    """Versionne et pousse uniquement le Parquet hebdomadaire collecté."""
    data_target, pointer_target = _weekly_dvc_paths(pull_result, project_root)
    commands = (
        [sys.executable, "-m", "dvc", "add", "--no-relink", str(data_target)],
        [sys.executable, "-m", "dvc", "push", str(pointer_target)],
    )
    try:
        for command in commands:
            subprocess.run(
                command,
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError as error:
        raise AirflowFailException("Le module dvc est absent du worker") from error
    except subprocess.CalledProcessError as error:
        operation = "dvc add" if error.cmd[3] == "add" else "dvc push"
        detail = (error.stderr or error.stdout or "").strip()
        for secret_name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
            secret = os.getenv(secret_name)
            if secret:
                detail = detail.replace(secret, "<redacted>")
        if len(detail) > 1000:
            detail = detail[-1000:]
        suffix = f": {detail}" if detail else ""
        raise AirflowFailException(
            f"Échec de {operation} pour {data_target}{suffix}"
        ) from error
    return pointer_target


def _configure_git_push_auth(environment: dict[str, str]) -> Path | None:
    """Configure un askpass temporaire quand un token de push est fourni."""
    if not environment.get("GIT_PUSH_TOKEN", "").strip():
        environment["GIT_TERMINAL_PROMPT"] = "0"
        return None

    descriptor, temporary_name = tempfile.mkstemp(prefix="git-askpass-", text=True)
    askpass_path = Path(temporary_name)
    with os.fdopen(descriptor, "w", encoding="utf-8") as askpass_file:
        askpass_file.write(
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  *Username*) printf '%s\\n' \"${GIT_PUSH_USERNAME:-x-access-token}\" ;;\n"
            "  *) printf '%s\\n' \"$GIT_PUSH_TOKEN\" ;;\n"
            "esac\n"
        )
    askpass_path.chmod(0o700)
    environment["GIT_ASKPASS"] = str(askpass_path)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return askpass_path


def commit_and_push_dvc_pointer(pointer_target: Path, project_root: Path) -> None:
    """Publie le pointeur DVC dans Git afin qu'il soit résolu par DagsHub."""
    remote = os.getenv("DVC_GIT_REMOTE", "origin").strip()
    if not remote:
        raise AirflowFailException("DVC_GIT_REMOTE ne peut pas être vide")

    environment = os.environ.copy()
    environment.setdefault("GIT_AUTHOR_NAME", "airflow-dvc-bot")
    environment.setdefault("GIT_AUTHOR_EMAIL", "airflow-dvc-bot@localhost")
    environment.setdefault("GIT_COMMITTER_NAME", environment["GIT_AUTHOR_NAME"])
    environment.setdefault("GIT_COMMITTER_EMAIL", environment["GIT_AUTHOR_EMAIL"])
    git_command = ["git", "-c", f"safe.directory={project_root.resolve()}"]
    askpass_path = _configure_git_push_auth(environment)
    try:
        branch_result = subprocess.run(
            [*git_command, "branch", "--show-current"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        branch = branch_result.stdout.strip()
        if not branch:
            raise AirflowFailException(
                "Le worker Git est en état detached HEAD ; branche de push inconnue"
            )

        subprocess.run(
            [*git_command, "add", "--", str(pointer_target)],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        staged_result = subprocess.run(
            [*git_command, "diff", "--cached", "--quiet", "--", str(pointer_target)],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        if staged_result.returncode == 1:
            subprocess.run(
                [
                    *git_command,
                    "commit",
                    "-m",
                    f"data: track {pointer_target.stem}",
                    "--",
                    str(pointer_target),
                ],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
        elif staged_result.returncode != 0:
            staged_result.check_returncode()

        subprocess.run(
            [*git_command, "push", remote, f"HEAD:refs/heads/{branch}"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    except FileNotFoundError as error:
        raise AirflowFailException("La commande git est absente du worker") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        if len(detail) > 1000:
            detail = detail[-1000:]
        suffix = f": {detail}" if detail else ""
        raise AirflowFailException(
            f"Échec de la publication Git de {pointer_target}{suffix}"
        ) from error
    finally:
        if askpass_path is not None:
            askpass_path.unlink(missing_ok=True)


@task(
    retries=3,
    retry_delay=timedelta(minutes=2),
)
def version_and_push_data(pull_result: dict[str, Any]) -> dict[str, Any]:
    """Sauvegarde le lot collecté dans le remote DVC avant le training."""
    project_root = Path(os.getenv("DVC_PROJECT_ROOT", "/workspace"))
    pointer_target = push_weekly_data_to_dvc(pull_result, project_root)
    commit_and_push_dvc_pointer(pointer_target, project_root)
    logger.info("Weekly data pushed to DVC: %s", pointer_target)
    return pull_result


def build_idempotency_key(dag_run_id: str, week: int) -> str:
    """Construit une clé stable et de taille fixe pour un run Airflow."""
    if not isinstance(dag_run_id, str) or not dag_run_id.strip():
        raise AirflowFailException("dag_run_id ne peut pas être vide")
    digest = hashlib.sha256(
        f"pull_train:{dag_run_id.strip()}:week:{week}".encode()
    ).hexdigest()
    return f"weekly-{week:02d}-{digest}"


def trigger_weekly_training(
    session: requests.Session,
    settings: TriggerSettings,
    token: str,
    week: int,
    file_path: str,
    idempotency_key: str,
) -> dict[str, Any]:
    """Déclenche un entraînement weekly et valide sa réponse."""
    response = session.post(
        settings.train_api_url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "weekly",
            "week": week,
            "file_path": file_path,
            "idempotency_key": idempotency_key,
        },
        timeout=(settings.connect_timeout_seconds, settings.train_timeout_seconds),
    )
    _raise_for_status(response, "Training")
    try:
        payload = response.json()
    except ValueError as error:
        raise AirflowFailException(
            "train-api returned an invalid JSON response"
        ) from error

    required_text_fields = (
        "model_type",
        "mlflow_run_id",
        "model_uri",
        "registered_model_name",
        "candidate_version",
        "promotion_reason",
        "dataset_digest",
        "idempotency_key",
    )
    valid_text_fields = (
        all(
            isinstance(payload.get(field), str) and payload[field].strip()
            for field in required_text_fields
        )
        if isinstance(payload, dict)
        else False
    )
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or payload.get("mode") != "weekly"
        or payload.get("week") != week
        or not isinstance(payload.get("new_model"), bool)
        or not isinstance(payload.get("model_metrics"), dict)
        or not valid_text_fields
        or payload.get("idempotency_key") != idempotency_key
    ):
        raise AirflowFailException("train-api returned an unusable response")
    return payload


@task(
    retries=3,
    retry_delay=timedelta(minutes=5),
    pool="train_api_training",
    pool_slots=1,
)
def call_train_api(pull_result: dict, dag_run_id: str) -> dict[str, Any]:
    """Tâche : entraîne un candidat à partir du fichier hebdomadaire collecté."""
    week = pull_result.get("week")
    file_path = pull_result.get("file_path")
    if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 52:
        raise AirflowFailException("pull_data n'a pas retourné une semaine valide")
    if not isinstance(file_path, str) or not file_path.strip():
        raise AirflowFailException("pull_data n'a pas retourné un file_path valide")

    settings = load_settings()
    session = build_session(settings.retries)
    train_token = request_token(session, settings, "train")
    idempotency_key = build_idempotency_key(dag_run_id, week)
    result = trigger_weekly_training(
        session,
        settings,
        train_token,
        week,
        file_path.strip(),
        idempotency_key,
    )
    logger.info(
        "Weekly training completed - Week: %s, Run: %s, New model: %s",
        week,
        result["mlflow_run_id"],
        result["new_model"],
    )
    return result


def trigger_model_reload(
    session: requests.Session,
    settings: TriggerSettings,
    token: str,
) -> dict[str, Any]:
    """Demande à predict-api de recharger le modèle courant."""
    response = session.post(
        settings.predict_api_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=(settings.connect_timeout_seconds, settings.train_timeout_seconds),
    )
    _raise_for_status(response, "Model reload")
    try:
        payload = response.json()
    except ValueError as error:
        raise AirflowFailException(
            "predict-api returned an invalid JSON response"
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "Model reloaded successfully"
    ):
        raise AirflowFailException("predict-api returned an unusable response")
    return payload


@task(
    retries=3,
    retry_delay=timedelta(minutes=5),
)
def call_reload_api(deployment_result: dict[str, Any]) -> dict[str, Any]:
    """Tâche : recharge le modèle après une publication BentoML réussie."""
    if deployment_result.get("deployed") is not True:
        raise AirflowFailException(
            "Model reload requested without a successful BentoML deployment"
        )

    settings = load_settings()
    session = build_session(settings.retries)
    reload_token = request_token(session, settings, "train")
    result = trigger_model_reload(session, settings, reload_token)
    logger.info(
        "Model reloaded successfully - BentoML tag: %s",
        deployment_result.get("bento_model"),
    )
    return result


def _required_result_text(training_result: dict[str, Any], field: str) -> str:
    value = training_result.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ModelPublicationError(
            f"train-api n'a pas retourné un champ {field} exploitable"
        )
    return value.strip()


def _find_model_tag(model_name: str, mlflow_run_id: str) -> str | None:
    """Retourne le tag déjà importé pour ce run MLflow, s'il existe."""
    try:
        models = bento_models.list(model_name)
    except bentoml.exceptions.NotFound:
        return None
    for model in models:
        if model.info.labels.get("mlflow_run_id") == mlflow_run_id:
            return str(model.tag)
    return None


def _write_current_model(destination: Path, model_tag: str) -> None:
    """Remplace atomiquement le pointeur vers le modèle courant."""
    if not destination.is_absolute():
        raise ModelPublicationError("CURRENT_MODEL_FILE doit être un chemin absolu")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"{model_tag}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def publish_weekly_model(
    training_result: dict[str, Any], settings: TriggerSettings
) -> str:
    """Importe une seule fois le modèle MLflow et le sélectionne pour l'inférence."""
    run_id = _required_result_text(training_result, "mlflow_run_id")
    model_uri = _required_result_text(training_result, "model_uri")
    model_type = _required_result_text(training_result, "model_type")

    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        model_tag = _find_model_tag(settings.bento_model_name, run_id)
        if model_tag is None:
            model = bentoml_mlflow.import_model(
                name=settings.bento_model_name,
                model_uri=model_uri,
                labels={"mlflow_run_id": run_id, "model_type": model_type},
            )
            model_tag = str(model.tag)
        _write_current_model(settings.current_model_file, model_tag)
    except ModelPublicationError:
        raise
    except Exception as error:
        raise ModelPublicationError(
            "impossible de publier le modèle weekly dans BentoML"
        ) from error
    return model_tag


@task(
    retries=3,
    retry_delay=timedelta(minutes=2),
)
def deploy_to_bento(training_result: dict[str, Any]) -> dict[str, Any]:
    """Tâche : publie le nouveau champion dans le store BentoML partagé."""
    if not training_result.get("new_model"):
        return {
            "deployed": False,
            "reason": "No new model",
        }

    settings = load_settings()
    model_tag = publish_weekly_model(training_result, settings)

    return {
        "deployed": True,
        "run_id": training_result["mlflow_run_id"],
        "bento_model": model_tag,
    }


@task.branch
def choose_model_path(training_result: dict[str, Any]) -> str:
    """Sélectionne la branche avec ou sans publication du candidat."""
    if training_result.get("new_model") is True:
        return "deploy_to_bento"
    return "skip_deployment"


@task
def skip_deployment(training_result: dict[str, Any]) -> dict[str, Any]:
    """Termine proprement le DAG lorsqu'aucun nouveau champion n'est promu."""
    logger.info(
        "No new model promoted - Week: %s, Run: %s, Reason: %s",
        training_result.get("week"),
        training_result.get("mlflow_run_id"),
        training_result.get("promotion_reason"),
    )
    return {
        "deployed": False,
        "reason": "No new model",
        "run_id": training_result.get("mlflow_run_id"),
    }


@task(trigger_rule="none_failed_min_one_success")
def summarize(training_result: dict[str, Any]) -> dict[str, Any]:
    """Produit la synthèse finale après l'une des deux branches."""
    new_model = training_result["new_model"]
    message = (
        "New model saved, deployed and reloaded"
        if new_model
        else "Pull and train completed without a new promoted model"
    )
    summary = {
        "message": message,
        "week": training_result["week"],
        "new_model": new_model,
        "model_type": training_result["model_type"],
        "model_metrics": training_result["model_metrics"],
        "mlflow_run_id": training_result["mlflow_run_id"],
        "promotion_reason": training_result["promotion_reason"],
    }
    logger.info("Pull train summary: %s", summary)
    return summary


