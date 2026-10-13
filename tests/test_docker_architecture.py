import json
import tomllib
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _compose(relative_path: str) -> dict:
    return yaml.safe_load(
        (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    )


def test_ml_package_keeps_its_python_name_under_train_api_utils() -> None:
    package = (
        PROJECT_ROOT
        / "src"
        / "train_api"
        / "utils"
        / "projet_accidents_mlops"
    )
    assert (package / "__init__.py").is_file()
    assert not (PROJECT_ROOT / "src" / "projet_accidents_mlops").exists()

    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    build_backend = pyproject["tool"]["uv"]["build-backend"]
    assert build_backend["module-name"] == "projet_accidents_mlops"
    assert build_backend["module-root"] == "src/train_api/utils"


def test_mlflow_state_is_bound_to_backupable_host_directories() -> None:
    compose = _compose("src/infra/mlflow/docker-compose.mlflow.yml")

    assert compose["services"]["mlflow-db"]["volumes"] == [
        "../../../data/mlflow/postgres:/var/lib/postgresql/data"
    ]
    assert compose["services"]["mlflow-server"]["volumes"] == [
        "../../../data/mlflow/artifacts:/mlartifacts"
    ]
    assert "volumes" not in compose


def test_mlflow_infrastructure_lives_under_src() -> None:
    assert (PROJECT_ROOT / "src" / "infra" / "mlflow").is_dir()
    assert not (PROJECT_ROOT / "infra").exists()

    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "COMPOSE_FILE := src/infra/mlflow/docker-compose.mlflow.yml" in makefile


def test_mlflow_runtime_state_is_not_scanned_by_dvc() -> None:
    dvcignore = (PROJECT_ROOT / ".dvcignore").read_text(encoding="utf-8")

    assert "/data/mlflow/" in dvcignore.splitlines()


def test_monitoring_has_an_independent_compose_project() -> None:
    monitoring = _compose("docker-compose.monitoring.yml")

    assert monitoring["name"] == "accidents-monitoring"
    assert "api" not in monitoring["services"]
    assert {
        "prometheus",
        "grafana",
        "sustainability-exporter",
        "drift-exporter",
        "ml-exporter",
        "loki",
        "alloy",
    }.issubset(monitoring["services"])

    loki = monitoring["services"]["loki"]
    assert loki["image"] == "grafana/loki:3.5.3"
    assert loki["volumes"] == [
        "./monitoring/loki/loki.yml:/etc/loki/config.yml:ro",
        "loki-data:/loki",
    ]
    assert loki["healthcheck"]["test"] == [
        "CMD",
        "wget",
        "--no-verbose",
        "--spider",
        "http://localhost:3100/ready",
    ]

    alloy = monitoring["services"]["alloy"]
    assert alloy["image"] == "grafana/alloy:v1.9.2"
    assert alloy["user"] == "0:0"
    assert alloy["volumes"] == [
        "./monitoring/alloy/config.alloy:/etc/alloy/config.alloy:ro",
        "/var/run/docker.sock:/var/run/docker.sock:ro",
        "alloy-data:/var/lib/alloy/data",
    ]
    assert alloy["depends_on"] == {"loki": {"condition": "service_healthy"}}
    assert {"loki-data", "alloy-data"}.issubset(monitoring["volumes"])


def test_grafana_provisions_loki_and_the_active_api_logs_dashboard() -> None:
    datasource = yaml.safe_load(
        (
            PROJECT_ROOT
            / "monitoring"
            / "grafana"
            / "provisioning"
            / "datasources"
            / "loki.yml"
        ).read_text(encoding="utf-8")
    )
    loki = datasource["datasources"][0]
    assert loki == {
        "name": "Loki",
        "uid": "loki",
        "type": "loki",
        "access": "proxy",
        "url": "http://loki:3100",
        "editable": True,
    }

    dashboard = json.loads(
        (
            PROJECT_ROOT
            / "monitoring"
            / "grafana"
            / "dashboards"
            / "api-logs-dashboard.json"
        ).read_text(encoding="utf-8")
    )
    assert dashboard["metadata"]["name"] == "api-logs"
    spec = dashboard["spec"]
    assert spec["title"] == "Accidents - Logs des API"
    panel = spec["elements"]["panel-1"]["spec"]
    assert panel["vizConfig"]["group"] == "logs"
    query = panel["data"]["spec"]["queries"][0]["spec"]["query"]
    assert query["datasource"]["name"] == "loki"
    assert query["spec"]["expr"] == (
        '{project="accidents-mlops", service=~"$service", detected_level=~"$level"}'
    )
    service = next(v["spec"] for v in spec["variables"] if v["spec"]["name"] == "service")
    assert service["regex"] == "/^(auth-api|pull-data-api|train-api|predict-api)$/"


def test_airflow_dag_runtime_is_connected_and_configured() -> None:
    compose = _compose("src/airflow_dags/docker-compose.yaml")
    common = compose["x-airflow-common"]
    environment = common["environment"]

    assert common["build"] == "."
    assert environment["AUTH_API_URL"] == "http://auth-api:8000/login"
    assert environment["PULL_API_URL"] == "http://pull-data-api:8000/pull_data"
    assert environment["TRAIN_API_URL"] == "http://train-api:8000/train"
    assert environment["PREDICT_API_URL"] == "http://predict-api:8000/reload"
    assert environment["MLFLOW_TRACKING_URI"] == "http://mlflow-server:5001"
    assert environment["CURRENT_MODEL_FILE"] == "/bentoml/current_model.txt"
    assert environment["AIRFLOW__CELERY__WORKER_CONCURRENCY"] == "2"
    assert compose["networks"]["accidents-shared-network"]["name"] == (
        "accidents-shared-network"
    )
    assert "bentoml_store:/bentoml" in compose["services"]["airflow-worker"][
        "volumes"
    ]
    bentoml_init = compose["services"]["bentoml-init"]
    assert bentoml_init["user"] == "0:0"
    assert bentoml_init["volumes"] == ["bentoml_store:/bentoml"]
    assert bentoml_init["restart"] == "no"
    bentoml_init_command = "\n".join(bentoml_init["command"])
    assert 'chown -R "${AIRFLOW_UID:-50000}:0" /bentoml' in bentoml_init_command
    assert compose["services"]["airflow-worker"]["depends_on"]["bentoml-init"] == {
        "condition": "service_completed_successfully"
    }
    airflow_init_command = "\n".join(compose["services"]["airflow-init"]["command"])
    assert (
        'airflow pools set train_api_training 1 "Serialize model training requests"'
        in airflow_init_command
    )

    requirements = (
        PROJECT_ROOT / "src" / "airflow_dags" / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert "bentoml==" in requirements
    assert "mlflow==" in requirements

