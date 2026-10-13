from pathlib import Path
import shutil
import subprocess

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_compose_registers_train_api() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.apis.yml").read_text(encoding="utf-8")
    )

    service = compose["services"]["train-api"]

    assert service["build"] == {
        "context": ".",
        "dockerfile": "src/train_api/Dockerfile",
        "args": {
            "APP_UID": "${LOCAL_UID:-1000}",
            "APP_GID": "${LOCAL_GID:-1000}",
        },
    }
    assert service["container_name"] == "accident_train_api"
    assert service["ports"] == ["8010:8000"]
    assert service["networks"] == ["accidents-shared-network"]
    assert service["volumes"] == [
        "./data/features:/var/lib/train-api/input:ro",
        "./data/incoming:/var/lib/train-api/incoming:ro",
        "./data/train-api-v2/artifacts:/var/lib/train-api/artifacts",
        "train_api_v2_state:/var/lib/train-api/state",
        "./monitoring/drift:/app/monitoring/drift",
        "./monitoring/ml:/app/monitoring/ml",
        "./reports/carbon:/app/reports/carbon",
    ]

    assert service["environment"]["BASE_DATASET_PATH"] == "/var/lib/train-api/input/data_final_binaire.csv"
    assert service["environment"]["INCOMING_DATA_DIR"] == "/var/lib/train-api/incoming"
    assert service["environment"]["ARTIFACT_ROOT"] == "/var/lib/train-api/artifacts"
    assert service["environment"]["STATE_DB_PATH"] == "/var/lib/train-api/state/train-api.sqlite3"
    assert service["environment"]["TMP_DIR"] == "/var/lib/train-api/artifacts/.tmp"
    assert service["environment"]["MLFLOW_HTTP_POOL_MAXSIZE"] == 32


def test_isolated_image_runs_uvicorn_without_legacy_or_external_tools() -> None:
    dockerfile = (
        PROJECT_ROOT / "src" / "train_api" / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "src.train_api.main:app" in dockerfile
    assert 'COPY --chown=app:app src/train_api/ ./src/train_api/' in dockerfile
    assert "USER app" in dockerfile
    assert "training_cli" not in dockerfile
    assert "uv run" not in dockerfile
    assert "dvc" not in dockerfile.lower()


def test_initial_train_is_a_disposable_bentoml_publisher() -> None:
    compose = yaml.safe_load(
        (PROJECT_ROOT / "docker-compose.apis.yml").read_text(encoding="utf-8")
    )

    service = compose["services"]["initial-train"]

    assert service["build"] == {
        "context": "./src/inital_train",
        "args": {
            "APP_UID": "${LOCAL_UID:-1000}",
            "APP_GID": "${LOCAL_GID:-1000}",
        },
    }
    assert service["restart"] == "no"
    assert service["volumes"] == ["bentoml_store:/bentoml"]
    assert service["environment"]["BENTOML_HOME"] == "/bentoml"
    assert service["environment"]["CURRENT_MODEL_FILE"] == (
        "/bentoml/current_model.txt"
    )
    assert service["environment"]["MLFLOW_TRACKING_URI"] == (
        "http://mlflow-server:5001"
    )
    assert service["environment"]["MLFLOW_REGISTERED_MODEL_NAME"] == (
        "${MLFLOW_REGISTERED_MODEL_NAME:-accidents-gravity-classifier}"
    )
    assert service["environment"]["MLFLOW_CHAMPION_ALIAS"] == (
        "${MLFLOW_CHAMPION_ALIAS:-champion}"
    )


def test_make_runs_initial_train_as_a_removed_one_shot_container() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "initial-train:" in makefile
    assert "run --rm --no-deps initial-train" in makefile


def test_make_uses_stable_uid_and_gid_defaults_for_api_compose() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "LOCAL_UID ?= 1000" in makefile
    assert "LOCAL_GID ?= 1000" in makefile
    assert "LOCAL_UID=$(LOCAL_UID) LOCAL_GID=$(LOCAL_GID) docker compose" in makefile


def test_make_starts_monitoring_with_stack_and_bootstrap() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "MONITORING_COMPOSE := docker compose --env-file $(ENV_FILE) -f docker-compose.monitoring.yml" in makefile
    assert "monitoring-up: $(ENV_FILE) network" in makefile
    assert "$(MONITORING_COMPOSE) up -d --build --wait --wait-timeout 180" in makefile

    if shutil.which("make") is None:
        pytest.skip("GNU Make est requis pour simuler l'orchestration")

    for target in ("stack-up", "init"):
        result = subprocess.run(
            ["make", "--dry-run", target], cwd=PROJECT_ROOT,
            check=True, capture_output=True, text=True,
        )
        commands = result.stdout
        assert commands.count("docker-compose.monitoring.yml up -d") == 1
        assert "emergency-interface" in commands
        assert "--no-build --wait --wait-timeout 300" in commands
        assert ("run --rm --no-deps initial-train" in commands) == (target == "init")
        if target == "init":
            assert commands.index("run --rm --no-deps initial-train") < commands.index("--no-build --wait")


def test_make_reset_removes_only_generated_runtime_state() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "reset:" in makefile
    assert "train_api_v2_state bentoml_store" in makefile
    assert "data/train-api-v2/artifacts data/train-api-v2/state" in makefile
    assert "data/mlflow/postgres data/mlflow/artifacts" in makefile
    reset_recipe = makefile.split("reset:", maxsplit=1)[1].split(
        "initial-train:", maxsplit=1
    )[0]
    destructive_lines = "\n".join(
        line for line in reset_recipe.splitlines() if "rm " in line
    )
    assert "data/features" not in destructive_lines
    assert "data/incoming" not in destructive_lines


def test_initial_train_image_drops_privileges_after_preparing_the_volume() -> None:
    dockerfile = (
        PROJECT_ROOT / "src" / "inital_train" / "Dockerfile"
    ).read_text(encoding="utf-8")
    entrypoint = (
        PROJECT_ROOT / "src" / "inital_train" / "entrypoint.sh"
    ).read_text(encoding="utf-8")

    assert "ARG APP_UID=1000" in dockerfile
    assert "ARG APP_GID=1000" in dockerfile
    assert "--chown=${APP_UID}:${APP_GID}" in dockerfile
    assert 'ENTRYPOINT ["/usr/local/bin/initial-train-entrypoint"]' in dockerfile
    assert 'exec runuser -u app -- "$@"' in entrypoint
    assert 'chown -R app "$BENTOML_HOME/models"' in entrypoint
