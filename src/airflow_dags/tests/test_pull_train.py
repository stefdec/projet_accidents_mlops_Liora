import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

DAG_PATH = Path(__file__).parents[1] / "dags" / "pull_train.py"


class SymbolicTaskOutput:
    def __getitem__(self, _key):
        return self

    def __rshift__(self, _other):
        return self

    def __rrshift__(self, _other):
        return self

    def __str__(self):
        return "symbolic-task-output"


class FakeTask:
    def __init__(self, python_callable, decorator_kwargs):
        self.python_callable = python_callable
        self.decorator_kwargs = decorator_kwargs

    def __call__(self, *_args, **_kwargs):
        return SymbolicTaskOutput()


class FakeTaskFactory:
    def _decorate(self, python_callable, decorator_kwargs):
        return FakeTask(python_callable, decorator_kwargs)

    def __call__(self, python_callable=None, **decorator_kwargs):
        if python_callable is not None:
            return self._decorate(python_callable, decorator_kwargs)

        def decorate(callable_):
            return self._decorate(callable_, decorator_kwargs)

        return decorate

    def branch(self, python_callable):
        return self._decorate(python_callable, {"branch": True})


@pytest.fixture(params=["pull_train", "pull_weekly"])
def pull_train_module(monkeypatch, request):
    sdk_module = ModuleType("airflow.sdk")
    exceptions_module = ModuleType("airflow.exceptions")
    operators_module = ModuleType("airflow.operators")
    python_operators_module = ModuleType("airflow.operators.python")

    class AirflowFailException(Exception):
        pass

    exceptions_module.AirflowFailException = AirflowFailException
    exceptions_module.AirflowSkipException = type("AirflowSkipException", (Exception,), {})
    sdk_module.Variable = SimpleNamespace(get=Mock(return_value="0"), set=Mock())
    sdk_module.task = FakeTaskFactory()
    python_operators_module.get_current_context = Mock()

    def dag(**decorator_kwargs):
        def decorate(dag_callable):
            dag_callable.dag_kwargs = decorator_kwargs
            return dag_callable

        return decorate

    sdk_module.dag = dag
    airflow_module = ModuleType("airflow")
    airflow_module.sdk = sdk_module
    airflow_module.exceptions = exceptions_module

    import_model = Mock(return_value=SimpleNamespace(tag="accidents:latest"))
    list_models = Mock(return_value=[])
    bentoml_module = ModuleType("bentoml")
    bentoml_module.mlflow = SimpleNamespace(import_model=import_model)
    bentoml_module.models = SimpleNamespace(list=list_models)
    bentoml_module.exceptions = SimpleNamespace(NotFound=LookupError)
    mlflow_module = ModuleType("mlflow")
    mlflow_module.set_tracking_uri = Mock()

    monkeypatch.setitem(sys.modules, "airflow", airflow_module)
    monkeypatch.setitem(sys.modules, "airflow.sdk", sdk_module)
    monkeypatch.setitem(sys.modules, "airflow.exceptions", exceptions_module)
    monkeypatch.setitem(sys.modules, "airflow.operators", operators_module)
    monkeypatch.setitem(
        sys.modules, "airflow.operators.python", python_operators_module
    )
    monkeypatch.setitem(sys.modules, "bentoml", bentoml_module)
    monkeypatch.setitem(sys.modules, "mlflow", mlflow_module)

    monkeypatch.syspath_prepend(str(DAG_PATH.parent))
    workflow_spec = importlib.util.spec_from_file_location(
        "accidents_workflow", DAG_PATH.with_name("accidents_workflow.py")
    )
    workflow = importlib.util.module_from_spec(workflow_spec)
    monkeypatch.setitem(sys.modules, "accidents_workflow", workflow)
    workflow_spec.loader.exec_module(workflow)
    module_name = "pull_train_under_test"
    sys.modules.pop(module_name, None)
    dag_path = DAG_PATH.with_name(request.param + ".py")
    spec = importlib.util.spec_from_file_location(module_name, dag_path)
    dag_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = dag_module
    spec.loader.exec_module(dag_module)
    workflow.pull_train = dag_module.pull_train
    module = workflow
    yield SimpleNamespace(
        module=module,
        dag_id=request.param,
        airflow_error=AirflowFailException,
        import_model=import_model,
        list_models=list_models,
        set_tracking_uri=mlflow_module.set_tracking_uri,
    )
    sys.modules.pop(module_name, None)


@pytest.fixture
def settings(pull_train_module, tmp_path):
    module = pull_train_module.module
    return module.TriggerSettings(
        auth_api_url="http://auth/login",
        pull_api_url="http://pull/pull_data",
        train_api_url="http://train/train",
        predict_api_url="http://predict/reload",
        pull_user="airflow",
        pull_password="secret",
        train_user="airflow",
        train_password="secret",
        retries=3,
        connect_timeout_seconds=10,
        auth_timeout_seconds=30,
        pull_timeout_seconds=600,
        train_timeout_seconds=7200,
        mlflow_tracking_uri="http://mlflow:5001",
        bento_model_name="accidents",
        current_model_file=tmp_path / "current_model.txt",
    )


def training_result(*, new_model=True, week=12, key="weekly-key"):
    return {
        "status": "success",
        "mode": "weekly",
        "week": week,
        "new_model": new_model,
        "model_type": "LightGBMClassifier",
        "model_metrics": {"accuracy": 0.95},
        "champion_metrics": {"accuracy": 0.94},
        "mlflow_run_id": "run-123",
        "model_uri": "runs:/run-123/model",
        "registered_model_name": "accidents-gravity-classifier",
        "candidate_version": "2",
        "champion_version": "2" if new_model else "1",
        "previous_champion_version": "1",
        "promotion_reason": "metric_improved" if new_model else "metric_not_improved",
        "dataset_digest": "sha256-value",
        "dvc_snapshot_path": None,
        "dvc_snapshot_md5": None,
        "idempotency_key": key,
    }


def test_load_settings_reads_credentials_and_defaults(pull_train_module):
    loaded = pull_train_module.module.load_settings(
        {
            "PULL_USERNAME": "alice",
            "PULL_PASSWORD": "wonderland",
            "TRAIN_USERNAME": "alice",
            "TRAIN_PASSWORD": "wonderland",
        }
    )
    assert loaded.pull_user == "alice"
    assert loaded.train_user == "alice"
    assert loaded.train_api_url == "http://train-api:8000/train"
    assert loaded.bento_model_name == "accidents"


def test_load_settings_rejects_missing_credentials(pull_train_module):
    with pytest.raises(ValueError, match="PULL_PASSWORD"):
        pull_train_module.module.load_settings(
            {
                "PULL_USERNAME": "alice",
                "TRAIN_USERNAME": "alice",
                "TRAIN_PASSWORD": "wonderland",
            }
        )


def test_request_token_uses_requested_scope(pull_train_module, settings):
    response = Mock(status_code=200)
    response.json.return_value = {"access_token": "  train-token  "}
    session = Mock()
    session.post.return_value = response
    assert (
        pull_train_module.module.request_token(session, settings, "train")
        == "train-token"
    )
    session.post.assert_called_once_with(
        settings.auth_api_url,
        json={
            "username": "airflow",
            "password": "secret",
            "token_type": "train",
        },
        timeout=(10, 30),
    )


@pytest.mark.parametrize("token", [None, "", "   ", 42])
def test_request_token_rejects_invalid_token(pull_train_module, settings, token):
    response = Mock(status_code=200)
    response.json.return_value = {"access_token": token}
    session = Mock()
    session.post.return_value = response
    with pytest.raises(pull_train_module.airflow_error, match="access token"):
        pull_train_module.module.request_token(session, settings, "pull")


def test_trigger_weekly_data_pull_uses_real_contract(pull_train_module, settings):
    payload = {
        "week": 12,
        "start_date": "2024-03-18",
        "end_date_exclusive": "2024-03-25",
        "file_path": "/shared-data/accidents_2024_w12.parquet",
        "record_count": 42,
    }
    response = Mock(status_code=200)
    response.json.return_value = payload
    session = Mock()
    session.get.return_value = response
    result = pull_train_module.module.trigger_weekly_data_pull(
        session, settings, "pull-token", 12
    )
    assert result == payload
    session.get.assert_called_once_with(
        settings.pull_api_url,
        params={"week": 12},
        headers={"Authorization": "Bearer pull-token"},
        timeout=(10, 600),
    )


def test_trigger_weekly_data_pull_rejects_wrong_week(pull_train_module, settings):
    response = Mock(status_code=200)
    response.json.return_value = {
        "week": 11,
        "start_date": "2024-03-11",
        "end_date_exclusive": "2024-03-18",
        "file_path": "/shared-data/week.parquet",
        "record_count": 42,
    }
    session = Mock()
    session.get.return_value = response
    with pytest.raises(pull_train_module.airflow_error, match="unusable"):
        pull_train_module.module.trigger_weekly_data_pull(
            session, settings, "pull-token", 12
        )


def test_push_weekly_data_to_dvc_targets_only_collected_week(
    pull_train_module, monkeypatch, tmp_path
):
    data_dir = tmp_path / "data" / "incoming"
    data_dir.mkdir(parents=True)
    weekly_file = data_dir / "accidents_2024_w12.parquet"
    weekly_file.write_bytes(b"parquet-data")
    run = Mock()
    monkeypatch.setattr(pull_train_module.module.subprocess, "run", run)

    pointer = pull_train_module.module.push_weekly_data_to_dvc(
        {
            "week": 12,
            "file_path": "/shared-data/accidents_2024_w12.parquet",
        },
        tmp_path,
    )

    assert pointer == Path("data/incoming/accidents_2024_w12.parquet.dvc")
    assert [call.args[0] for call in run.call_args_list] == [
        [
            sys.executable,
            "-m",
            "dvc",
            "add",
            "--no-relink",
            "data/incoming/accidents_2024_w12.parquet",
        ],
        [
            sys.executable,
            "-m",
            "dvc",
            "push",
            "data/incoming/accidents_2024_w12.parquet.dvc",
        ],
    ]
    assert all(call.kwargs["cwd"] == tmp_path for call in run.call_args_list)
    assert all(call.kwargs["check"] is True for call in run.call_args_list)


def test_push_weekly_data_to_dvc_rejects_unexpected_file_name(
    pull_train_module, tmp_path
):
    with pytest.raises(pull_train_module.airflow_error, match="nom de fichier"):
        pull_train_module.module.push_weekly_data_to_dvc(
            {"week": 12, "file_path": "/shared-data/another-file.parquet"},
            tmp_path,
        )


def test_commit_and_push_dvc_pointer_commits_only_changed_pointer(
    pull_train_module, monkeypatch, tmp_path
):
    run = Mock(
        side_effect=[
            SimpleNamespace(stdout="feature/weekly-data\n"),
            SimpleNamespace(),
            SimpleNamespace(returncode=1),
            SimpleNamespace(),
            SimpleNamespace(),
        ]
    )
    monkeypatch.setattr(pull_train_module.module.subprocess, "run", run)

    pull_train_module.module.commit_and_push_dvc_pointer(
        Path("data/incoming/accidents_2024_w12.parquet.dvc"), tmp_path
    )

    git = ["git", "-c", f"safe.directory={tmp_path.resolve()}"]
    assert [call.args[0] for call in run.call_args_list] == [
        [*git, "branch", "--show-current"],
        [*git, "add", "--", "data/incoming/accidents_2024_w12.parquet.dvc"],
        [*git,
            "diff",
            "--cached",
            "--quiet",
            "--",
            "data/incoming/accidents_2024_w12.parquet.dvc",
        ],
        [*git,
            "commit",
            "-m",
            "data: track accidents_2024_w12.parquet",
            "--",
            "data/incoming/accidents_2024_w12.parquet.dvc",
        ],
        [*git, "push", "origin", "HEAD:refs/heads/feature/weekly-data"],
    ]
    assert run.call_args_list[2].kwargs["check"] is False


def test_commit_and_push_dvc_pointer_pushes_existing_commit_after_retry(
    pull_train_module, monkeypatch, tmp_path
):
    run = Mock(
        side_effect=[
            SimpleNamespace(stdout="feature/weekly-data\n"),
            SimpleNamespace(),
            SimpleNamespace(returncode=0),
            SimpleNamespace(),
        ]
    )
    monkeypatch.setattr(pull_train_module.module.subprocess, "run", run)

    pull_train_module.module.commit_and_push_dvc_pointer(
        Path("data/incoming/accidents_2024_w12.parquet.dvc"), tmp_path
    )

    commands = [call.args[0] for call in run.call_args_list]
    assert not any(command[:2] == ["git", "commit"] for command in commands)
    assert commands[-1] == [
        "git",
        "-c",
        f"safe.directory={tmp_path.resolve()}",
        "push",
        "origin",
        "HEAD:refs/heads/feature/weekly-data",
    ]


def test_configure_git_push_auth_keeps_token_out_of_askpass_file(
    pull_train_module,
):
    environment = {"GIT_PUSH_TOKEN": "test-token"}

    askpass_path = pull_train_module.module._configure_git_push_auth(environment)

    assert askpass_path is not None
    assert environment["GIT_ASKPASS"] == str(askpass_path)
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert "test-token" not in askpass_path.read_text(encoding="utf-8")
    askpass_path.unlink()


def test_configure_git_push_auth_disables_interactive_prompt_without_token(
    pull_train_module,
):
    environment = {}

    assert pull_train_module.module._configure_git_push_auth(environment) is None
    assert environment == {"GIT_TERMINAL_PROMPT": "0"}


def test_idempotency_key_is_stable_and_run_specific(pull_train_module):
    build = pull_train_module.module.build_idempotency_key
    assert build("manual-run", 12) == build("manual-run", 12)
    assert build("manual-run", 12) != build("another-run", 12)
    assert len(build("manual-run", 12)) <= 128


def test_trigger_weekly_training_uses_weekly_contract(pull_train_module, settings):
    payload = training_result(key="weekly-key")
    response = Mock(status_code=200)
    response.json.return_value = payload
    session = Mock()
    session.post.return_value = response
    result = pull_train_module.module.trigger_weekly_training(
        session,
        settings,
        "train-token",
        12,
        "/shared-data/accidents_2024_w12.parquet",
        "weekly-key",
    )
    assert result == payload
    session.post.assert_called_once_with(
        settings.train_api_url,
        headers={"Authorization": "Bearer train-token"},
        json={
            "mode": "weekly",
            "week": 12,
            "file_path": "/shared-data/accidents_2024_w12.parquet",
            "idempotency_key": "weekly-key",
        },
        timeout=(10, 7200),
    )


def test_trigger_weekly_training_rejects_wrong_idempotency_key(
    pull_train_module, settings
):
    response = Mock(status_code=200)
    response.json.return_value = training_result(key="different-key")
    session = Mock()
    session.post.return_value = response
    with pytest.raises(pull_train_module.airflow_error, match="unusable"):
        pull_train_module.module.trigger_weekly_training(
            session, settings, "token", 12, "/shared-data/week.parquet", "expected"
        )


def test_publish_weekly_model_imports_and_selects_model(
    pull_train_module, settings
):
    tag = pull_train_module.module.publish_weekly_model(training_result(), settings)
    assert tag == "accidents:latest"
    pull_train_module.set_tracking_uri.assert_called_once_with(
        settings.mlflow_tracking_uri
    )
    pull_train_module.import_model.assert_called_once_with(
        name="accidents",
        model_uri="runs:/run-123/model",
        labels={
            "mlflow_run_id": "run-123",
            "model_type": "LightGBMClassifier",
        },
    )
    assert settings.current_model_file.read_text() == "accidents:latest\n"


def test_publish_weekly_model_reuses_existing_import(pull_train_module, settings):
    pull_train_module.list_models.return_value = [
        SimpleNamespace(
            tag="accidents:existing",
            info=SimpleNamespace(labels={"mlflow_run_id": "run-123"}),
        )
    ]
    tag = pull_train_module.module.publish_weekly_model(training_result(), settings)
    assert tag == "accidents:existing"
    pull_train_module.import_model.assert_not_called()
    assert settings.current_model_file.read_text() == "accidents:existing\n"


def test_trigger_model_reload_validates_predict_response(pull_train_module, settings):
    response = Mock(status_code=200)
    response.json.return_value = {"status": "Model reloaded successfully"}
    session = Mock()
    session.post.return_value = response
    result = pull_train_module.module.trigger_model_reload(
        session, settings, "login-token"
    )
    assert result == {"status": "Model reloaded successfully"}
    session.post.assert_called_once_with(
        settings.predict_api_url,
        headers={"Authorization": "Bearer login-token"},
        timeout=(10, 7200),
    )


def test_branch_selects_deployment_only_for_new_model(pull_train_module):
    choose = pull_train_module.module.choose_model_path.python_callable
    assert choose(training_result(new_model=True)) == "deploy_to_bento"
    assert choose(training_result(new_model=False)) == "skip_deployment"


def test_summary_reports_non_promoted_candidate(pull_train_module):
    summarize = pull_train_module.module.summarize.python_callable
    result = summarize(training_result(new_model=False))
    assert result["new_model"] is False
    assert result["message"] == (
        "Pull and train completed without a new promoted model"
    )


def test_dag_and_tasks_expose_expected_configuration(pull_train_module):
    module = pull_train_module.module
    assert module.pull_train.dag_kwargs["dag_id"] == pull_train_module.dag_id
    assert module.pull_train.dag_kwargs["max_active_runs"] == 1
    assert module.pull_data.decorator_kwargs["retries"] == 3
    assert module.version_and_push_data.decorator_kwargs["retries"] == 3
    assert module.call_train_api.decorator_kwargs["retries"] == 3
    assert module.call_train_api.decorator_kwargs["pool"] == "train_api_training"
    assert module.call_train_api.decorator_kwargs["pool_slots"] == 1
    assert module.pull_train.dag_kwargs["schedule"] == (
        "0 3 * * 1" if pull_train_module.dag_id == "pull_train" else "*/5 * * * *"
    )
    assert module.choose_model_path.decorator_kwargs["branch"] is True
    assert module.summarize.decorator_kwargs["trigger_rule"] == (
        "none_failed_min_one_success"
    )
