"""Tests de predict_api (service.py + metrics.py)."""

import asyncio
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import jwt
import mlflow
import pytest

SERVICE_DIR = Path(__file__).parents[1] / "src" / "predict_api"
SERVICE_PATH = SERVICE_DIR / "service.py"
JWT_SECRET = "test-predict-v2-secret-with-at-least-32-bytes"
JWT_TRAIN_SECRET = "test-train-v2-secret-with-at-least-32-bytes"
JWT_ALGORITHM = "HS256"


def _make_fake_bentoml():
    b = ModuleType("bentoml")

    def service(cls=None, /, **_kw):
        def wrap(t):
            if not hasattr(t, "add_asgi_middleware"):
                t.add_asgi_middleware = classmethod(lambda _c, *_a, **_k: None)
            return t
        return wrap(cls) if cls is not None else wrap

    def api(func=None, /, *, route=None, **_kw):
        def wrap(t):
            return t
        return wrap(func) if func is not None else wrap

    def asgi_app(_app, /, **_kw):
        return lambda t: t

    def depends(_s, /, **_kw):
        return None

    mlflow = ModuleType("bentoml.mlflow")
    mlflow.load_model = lambda *_a, **_k: None

    exc = ModuleType("bentoml.exceptions")

    class BentoMLException(Exception):
        pass

    class NotFound(BentoMLException):
        pass

    exc.BentoMLException = BentoMLException
    exc.NotFound = NotFound

    b.service, b.api, b.asgi_app, b.depends = service, api, asgi_app, depends
    b.mlflow, b.exceptions = mlflow, exc
    return b, mlflow, exc


@pytest.fixture(scope="module")
def svc():
    mp = pytest.MonkeyPatch()
    fake_b, fake_mlflow, fake_exc = _make_fake_bentoml()
    mp.setitem(sys.modules, "bentoml", fake_b)
    mp.setitem(sys.modules, "bentoml.mlflow", fake_mlflow)
    mp.setitem(sys.modules, "bentoml.exceptions", fake_exc)
    mp.setenv("JWT_SECRET_KEY", JWT_SECRET)
    mp.setenv("JWT_SECRET_TRAIN", JWT_TRAIN_SECRET)
    mp.setenv("JWT_ALGORITHM", JWT_ALGORITHM)
    mp.syspath_prepend(str(SERVICE_DIR))  # pour `import metrics`

    from prometheus_client import REGISTRY

    saved = list(REGISTRY._collector_to_names)
    for c in saved:
        REGISTRY.unregister(c)

    sys.modules.pop("metrics", None)
    name = "predict_api_service_under_test"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.metrics = sys.modules["metrics"]
    try:
        yield module
    finally:
        sys.modules.pop(name, None)
        sys.modules.pop("metrics", None)
        for c in list(REGISTRY._collector_to_names):
            REGISTRY.unregister(c)
        for c in saved:
            REGISTRY.register(c)
        mp.undo()


def _payload() -> dict:
    return {
        "Num_Acc": 202400000001, "place": 1.0, "catu": 1, "sexe": 1.0,
        "trajet": 1.0, "locp": 0.0, "actp": 0.0, "etatp": 1.0, "manv": 1.0,
        "catr": 3, "circ": 2.0, "vosp": 0.0, "prof": 1.0, "surf": 1.0,
        "infra": 0.0, "situ": 1.0, "mois": 6, "lum": 1.0, "agg": 2, "atm": 1.0,
        "col": 6.0, "lat": 48.85, "long": 2.35,
        "year": datetime.now(timezone.utc).year - 1,
        "secu1": 1.0, "secu2": 0.0, "secu3": 0.0, "motor": 1.0, "vma": 50.0,
        "jour_semaine": 2, "heure": 14, "periode_journee": 2,
        "age_conducteur": 35.0, "categorie_vehicule": 1, "type_choc": 3,
        "presence_obstacle_fixe": 0, "type_obstacle": 2, "type_collision": 1,
    }


def _sample(metric, suffix, **labels):
    for fam in metric.collect():
        for s in fam.samples:
            if s.name.endswith(suffix) and all(
                s.labels.get(k) == v for k, v in labels.items()
            ):
                return s.value
    return 0.0


def _model_stub(*, result=None, error=None, reload_result=None, reload_error=None):
    class _S:
        def __init__(self):
            self.model = object()
            self.model_name = "accidents:test"
            self.calls = []
            self.reload_calls = 0

        def predict_array(self, features):
            self.calls.append(features)
            if error is not None:
                raise error
            return result

        def reload_model(self):
            self.reload_calls += 1
            if reload_error is not None:
                raise reload_error
            return reload_result

    return _S()


def _request(path, authorization=None):
    headers = {} if authorization is None else {"Authorization": authorization}
    return SimpleNamespace(
        url=SimpleNamespace(path=path), headers=headers, state=SimpleNamespace()
    )


def test_load_model_exposes_raw_model_probabilities(svc, monkeypatch):
    sentinel = object()

    class LoadedModel:
        def get_raw_model(self):
            return sentinel

    monkeypatch.setattr(svc.bentoml.mlflow, "load_model", lambda _name: LoadedModel())

    assert svc.load_model("accidents:test") is sentinel


def test_load_model_keeps_pyfunc_when_raw_model_is_unavailable(svc, monkeypatch):
    class LoadedModel:
        def get_raw_model(self):
            raise RuntimeError("raw model unavailable")

    loaded = LoadedModel()
    monkeypatch.setattr(svc.bentoml.mlflow, "load_model", lambda _name: loaded)

    assert svc.load_model("accidents:pyfunc") is loaded


def _dispatch(svc, request):
    mw = svc.JWTAuthMiddleware(app=lambda *_a, **_k: None)
    called = {}

    async def call_next(_r):
        called["hit"] = True
        return "OK"

    return asyncio.run(mw.dispatch(request, call_next)), called


# --- /predict ------------------------------------------------------------
def test_predict_happy_records_all_metrics(svc):
    s = svc.PredictionService()
    s.model_service = _model_stub(
        result={"prediction": 1, "probability": 0.87, "model_version": "42"}
    )
    m = svc.metrics
    lat0 = _sample(m.RESPONSE_TIME, "_count")
    cnt0 = _sample(m.PREDICTION_COUNT, "_total")
    prob0 = _sample(m.PREDICTION_PROB, "_count")

    resp = s.predict(svc.InputData(**_payload()))

    assert resp == {
        "prediction": 1,
        "probability": 0.87,
        "model_version": "42",
    }
    assert _sample(m.RESPONSE_TIME, "_count") == lat0 + 1
    assert _sample(m.PREDICTION_COUNT, "_total") == cnt0 + 1
    assert _sample(m.PREDICTION_PROB, "_count") == prob0 + 1
    assert _sample(m.PREDICTED_CLASS_DIST, "_total", class_label="1") >= 1
    assert _sample(m.SUCCESS_COUNT, "_total") >= 1
    assert _sample(m.MODEL_INFO, "", version="42") == 1
    assert _sample(m.MODEL_LOAD_STATE, "model_load_state") == 1


def test_predict_probability_none(svc):
    s = svc.PredictionService()
    s.model_service = _model_stub(
        result={"prediction": 0, "probability": None, "model_version": "42"}
    )
    m = svc.metrics
    prob0 = _sample(m.PREDICTION_PROB, "_count")

    resp = s.predict(svc.InputData(**_payload()))

    assert resp == {
        "prediction": 0,
        "probability": None,
        "model_version": "42",
    }
    assert _sample(m.PREDICTION_PROB, "_count") == prob0
    assert _sample(m.PREDICTED_CLASS_DIST, "_total", class_label="0") >= 1


def test_predict_model_unavailable_503_still_times(svc):
    s = svc.PredictionService()
    s.model_service = _model_stub(error=RuntimeError("no model"))
    m = svc.metrics
    lat0 = _sample(m.RESPONSE_TIME, "_count")
    err0 = _sample(m.ERROR_COUNT, "_total", status_code="503")

    resp = s.predict(svc.InputData(**_payload()))

    assert isinstance(resp, svc.JSONResponse)
    assert resp.status_code == 503
    assert _sample(m.ERROR_COUNT, "_total", status_code="503") == err0 + 1
    assert _sample(m.RESPONSE_TIME, "_count") == lat0 + 1


def test_predict_bad_features_400(svc):
    s = svc.PredictionService()
    s.model_service = _model_stub(result={"prediction": 1})
    m = svc.metrics
    err0 = _sample(m.ERROR_COUNT, "_total", status_code="400")

    class _Bad:
        def model_dump(self):
            return {"a": 1.0, "b": "nan-str"}

    resp = s.predict(_Bad())

    assert isinstance(resp, svc.JSONResponse)
    assert resp.status_code == 400
    assert _sample(m.ERROR_COUNT, "_total", status_code="400") == err0 + 1
    assert s.model_service.calls == []


# --- metrics.record_prediction ----------------------------------------
def test_record_prediction_full_and_partial(svc):
    m = svc.metrics
    before = _sample(m.PREDICTION_COUNT, "_total")
    m.record_prediction(1, 0.5, "9")
    m.record_prediction(0, None, "9")
    assert _sample(m.PREDICTION_COUNT, "_total") == before + 2


# --- /reload -----------------------------------------------------------
def test_reload_success(svc, monkeypatch):
    s = svc.PredictionService()
    expected = {
        "status": "Model reloaded successfully",
        "model_version": "accidents:5",
    }
    stub = _model_stub(result={}, reload_result=expected)
    s.model_service = stub

    out = s.reload_model()

    assert out == expected
    assert stub.reload_calls == 1


def test_model_worker_reload_updates_model(svc, monkeypatch):
    sentinel = object()
    monkeypatch.setattr(svc, "load_model", lambda _n: sentinel)
    monkeypatch.setattr(svc, "get_current_model_name", lambda: "accidents:5")

    worker = svc.ModelService()
    worker.model = None
    out = worker.reload_model()

    assert out == {
        "status": "Model reloaded successfully",
        "model_version": "accidents:5",
    }
    assert worker.model is sentinel
    assert worker.model_name == "accidents:5"


def test_reload_failure_503(svc, monkeypatch):
    s = svc.PredictionService()
    s.model_service = _model_stub(
        result={}, reload_error=RuntimeError("model unavailable")
    )
    m = svc.metrics
    err0 = _sample(m.ERROR_COUNT, "_total", status_code="503")

    out = s.reload_model()

    assert isinstance(out, svc.JSONResponse)
    assert out.status_code == 503
    assert _sample(m.ERROR_COUNT, "_total", status_code="503") == err0 + 1


# --- middleware ------------------------------------------------------
def test_mw_unprotected_path(svc):
    out, called = _dispatch(svc, _request("/health"))
    assert called.get("hit") is True and out == "OK"


def test_mw_missing_token(svc):
    out, called = _dispatch(svc, _request("/predict"))
    assert isinstance(out, svc.JSONResponse) and out.status_code == 401
    assert "hit" not in called


def test_mw_expired_token(svc):
    tok = jwt.encode(
        {"sub": "alice", "exp": datetime(2000, 1, 1, tzinfo=timezone.utc)},
        JWT_TRAIN_SECRET, algorithm=JWT_ALGORITHM,
    )
    out, called = _dispatch(svc, _request("/reload", f"Bearer {tok}"))
    assert isinstance(out, svc.JSONResponse) and out.status_code == 401


def test_mw_valid_token(svc):
    tok = jwt.encode({"sub": "alice"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    req = _request("/predict", f"Bearer {tok}")
    out, called = _dispatch(svc, req)
    assert called.get("hit") is True and out == "OK"
    assert req.state.user == "alice"


def test_mw_reload_requires_train_token(svc):
    login_token = jwt.encode({"sub": "alice"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    rejected, called = _dispatch(svc, _request("/reload", f"Bearer {login_token}"))
    assert rejected.status_code == 401
    assert "hit" not in called

    train_token = jwt.encode({"sub": "alice"}, JWT_TRAIN_SECRET, algorithm=JWT_ALGORITHM)
    accepted, called = _dispatch(svc, _request("/reload", f"Bearer {train_token}"))
    assert accepted == "OK" and called.get("hit") is True


@pytest.mark.parametrize("field,value", [
    ("jour_semaine", 0), ("jour_semaine", 8),
    ("periode_journee", 0), ("categorie_vehicule", 9),
    ("type_choc", 6), ("presence_obstacle_fixe", 2),
    ("type_obstacle", 5), ("type_collision", 4),
])
def test_unknown_category_rejected(svc, field, value):
    from pydantic import ValidationError

    payload = _payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        svc.InputData(**payload)


def test_public_payload_matches_mlflow_schema(svc, monkeypatch, tmp_path):
    import pandas as pd
    from mlflow.models import ModelSignature
    from mlflow.types import ColSpec, Schema

    # Signature du modèle dans les logs : 39 colonnes nommées et typées.
    longs = "Num_Acc catu catr mois agg year month hour".split()
    doubles = (
        "place sexe trajet locp actp etatp manv circ vosp prof surf infra situ "
        "lum atm col lat long secu1 secu2 secu3 motor vma age"
    ).split()
    strings = (
        "day_of_week day_period catv_group macro_choc "
        "presence_obstacle_fixe macro_obsm type_crash"
    ).split()
    signature = ModelSignature(inputs=Schema(
        [ColSpec("long", name) for name in longs]
        + [ColSpec("double", name) for name in doubles]
        + [ColSpec("string", name) for name in strings]
    ))

    class SchemaCheckedModel(mlflow.pyfunc.PythonModel):
        def predict(self, context, model_input, params=None):
            assert isinstance(model_input, pd.DataFrame)
            assert model_input.shape == (1, 39)
            row = model_input.iloc[0]
            assert row["month"] == row["mois"] == 6
            assert row["day_of_week"] == "Tuesday"
            assert row["day_period"] == "apres_midi"
            assert row["catv_group"] == "Deux-roues motorisés"
            assert row["macro_choc"] == "Lateral"
            assert row["presence_obstacle_fixe"] == "Non/Inconnu"
            assert row["macro_obsm"] == "Pieton"
            assert row["type_crash"] == "Vehicule_vs_Pieton"
            return [1]

    path = str(tmp_path / "model")
    mlflow.pyfunc.save_model(path, python_model=SchemaCheckedModel(), signature=signature)
    model = mlflow.pyfunc.load_model(path)
    monkeypatch.setattr(svc, "load_model", lambda _: model)
    monkeypatch.setattr(svc, "get_current_model_name", lambda: "accidents:test")
    service = svc.PredictionService()
    service.model_service = svc.ModelService()
    assert service.predict(svc.InputData(**_payload())) == {
        "prediction": 1,
        "probability": None,
        "model_version": "accidents:test",
    }


def test_category_labels_match_training(svc):
    from src.train_api.features import (
        CATV_GROUP_MAPPING, DAY_OF_WEEK_MAPPING, DAY_PERIOD_MAPPING, VALUE_MAPPINGS,
    )

    mappings = dict(VALUE_MAPPINGS, day_of_week=DAY_OF_WEEK_MAPPING,
                    day_period=DAY_PERIOD_MAPPING, catv_group=CATV_GROUP_MAPPING)
    assert svc.CATEGORY_LABELS == {
        name: {code: label for label, code in mapping.items()}
        for name, mapping in mappings.items()
    }
