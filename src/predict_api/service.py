import logging
import os
from datetime import datetime, timezone

import bentoml
import jwt
import numpy as np
import pandas as pd
from fastapi import FastAPI
from metrics import (
    record_error,
    record_prediction,
    record_request,
    set_model_loaded,
    track_latency,
)
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Projet Accidents MLOps Predict API",
    description=("Reçoit des données d'accidents et prédit la gravité de l'accident."),
    version="0.1.0",
)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_SECRET_TRAIN = os.getenv("JWT_SECRET_TRAIN")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

CURRENT_MODEL_FILE = "/bentoml/current_model.txt"


# Codes publics de l'API -> catégories brutes attendues par le pipeline MLflow.
# Ces libellés correspondent aux mappings de src/train_api/features.py.
CATEGORY_LABELS = {
    "day_of_week": dict(
        enumerate(
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
            1,
        )
    ),
    "day_period": {1: "matin", 2: "apres_midi", 3: "soir", 4: "nuit"},
    "catv_group": dict(
        enumerate(
            [
                "Véhicules légers",
                "Deux-roues motorisés",
                "Mobilités douces / individuelles",
                "Utilitaires",
                "Poids lourds / marchandises",
                "Transport collectif",
                "Autres / indéterminés",
                "Véhicules spéciaux / agricoles",
                "Rail / tramway",
            ]
        )
    ),
    "macro_choc": dict(
        enumerate(["Aucun", "Frontal", "Arriere", "Lateral", "Multiple", "Inconnu"])
    ),
    "presence_obstacle_fixe": {0: "Non/Inconnu", 1: "Oui"},
    "macro_obsm": dict(
        enumerate(["Aucun", "Vehicule", "Pieton", "Animal", "Autre/Inconnu"])
    ),
    "type_crash": dict(
        enumerate(
            [
                "Vehicule_vs_Vehicule",
                "Vehicule_vs_Pieton",
                "Seul_contre_Obstacle_Fixe",
                "Autre/Multiple",
            ]
        )
    ),
}


class InputData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Num_Acc: int = Field(
        ..., alias="Num_Acc", description="Numéro d'accident unique", gt=0
    )
    place: float = Field(
        ...,
        alias="place",
        description="Place du conducteur dans le véhicule",
        ge=0,
        le=9,
    )
    catu: int = Field(..., alias="catu", description="Catégorie d'usager", ge=1, le=3)
    sexe: float = Field(..., alias="sexe", description="Sexe du conducteur", ge=1, le=2)
    trajet: float = Field(
        ..., alias="trajet", description="Type de trajet", ge=-1, le=9
    )
    locp: float = Field(
        ...,
        alias="locp",
        description="Localisation du conducteur dans le véhicule",
        ge=-1,
        le=9,
    )
    actp: float = Field(
        ...,
        alias="actp",
        description="Action du conducteur avant l'accident",
        ge=-1,
        le=9,
    )
    etatp: float = Field(
        ...,
        alias="etatp",
        description="État du conducteur avant l'accident",
        ge=-1,
        le=3,
    )
    manv: float = Field(
        ...,
        alias="manv",
        description="Manœuvre du véhicule avant l'accident ",
        ge=-1,
        le=26,
    )
    catr: int = Field(..., alias="catr", description="Catégorie de route", ge=1, le=9)
    circ: float = Field(
        ..., alias="circ", description="Régime de circulation", ge=-1, le=4
    )
    vosp: float = Field(
        ..., alias="vosp", description="Existence d'une voie réservée", ge=-1, le=4
    )
    prof: float = Field(
        ..., alias="prof", description="Profil de la route", ge=-1, le=4
    )
    surf: float = Field(
        ..., alias="surf", description="État de la surface de la route", ge=-1, le=9
    )
    infra: float = Field(
        ..., alias="infra", description="Type d'infrastructure routière", ge=-1, le=9
    )
    situ: float = Field(
        ..., alias="situ", description="Situation de l'accident", ge=-1, le=8
    )
    mois: int = Field(..., alias="mois", description="Mois de l'accident", ge=1, le=12)
    lum: float = Field(..., alias="lum", description="Luminosité", ge=1, le=5)
    agg: int = Field(..., alias="agg", description="Agglomération", ge=1, le=2)
    atm: float = Field(
        ..., alias="atm", description="Conditions atmosphériques", ge=1, le=9
    )
    col: float
    lat: float
    long: float
    year: int = Field(
        ...,
        alias="year",
        description="Année de l'accident",
        ge=2000,
        le=datetime.now(timezone.utc).year,
    )
    secu1: float
    secu2: float
    secu3: float
    motor: float
    vma: float = Field(
        ..., alias="vma", description="Vitesse maximale autorisée", ge=0, le=130
    )
    day_of_week: int = Field(..., alias="jour_semaine", ge=1, le=7)
    hour: int = Field(..., alias="heure", ge=0, le=23)
    day_period: int = Field(..., alias="periode_journee", ge=1, le=4)
    age: float = Field(..., alias="age_conducteur", ge=0, le=120)
    catv_group: int = Field(..., alias="categorie_vehicule", ge=0, le=8)
    macro_choc: int = Field(..., alias="type_choc", ge=0, le=5)
    presence_obstacle_fixe: int = Field(..., alias="presence_obstacle_fixe", ge=0, le=1)
    macro_obsm: int = Field(..., alias="type_obstacle", ge=0, le=4)
    type_crash: int = Field(..., alias="type_collision", ge=0, le=3)


@app.get("/health")
def health() -> dict:

    return {"status": "ok"}


def get_current_model_name() -> str:
    try:
        with open(CURRENT_MODEL_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(
            "Fichier du modèle courant introuvable; utilisation du modèle par défaut."
        )
        return "accidents:latest"


def load_model(model_name: str):
    try:
        model = bentoml.mlflow.load_model(model_name)
        try:
            raw = (
                model.get_raw_model()
            )  # ThresholdedBinaryClassifier -> expose predict_proba
        except Exception:  # noqa: BLE001 — flavor sans modèle natif : on garde le pyfunc
            raw = None
        if raw is not None:
            model = raw
        logger.info("Modèle chargé: %s", model_name)
        return model
    except bentoml.exceptions.NotFound:
        logger.warning("Modèle introuvable dans le registre BentoML: %s", model_name)
    except (FileNotFoundError, OSError, ValueError, RuntimeError):
        logger.exception("Échec du chargement du modèle: %s", model_name)
    return None


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.endswith("/predict") or request.url.path.endswith(
            "/reload"
        ):
            if request.url.path.endswith("/reload"):
                jwt_secret_key = JWT_SECRET_TRAIN
            else:
                jwt_secret_key = JWT_SECRET_KEY

            token = request.headers.get("Authorization")
            if not token:
                logger.warning(
                    "Requête de prédiction refusée: jeton d'authentification absent."
                )
                record_error(401)
                return JSONResponse(
                    status_code=401, content={"detail": "Missing authentication token"}
                )
            try:
                token = token.split()[1]  # Bearer <token>
                payload = jwt.decode(token, jwt_secret_key, algorithms=[JWT_ALGORITHM])
            except jwt.ExpiredSignatureError:
                logger.warning("Requête de prédiction refusée: jeton expiré.")
                record_error(401)
                return JSONResponse(
                    status_code=401, content={"detail": "Token has expired"}
                )
            except jwt.InvalidTokenError:
                logger.warning("Requête de prédiction refusée: jeton invalide.")
                record_error(401)
                return JSONResponse(
                    status_code=401, content={"detail": "Invalid token"}
                )
            request.state.user = payload.get("sub")
        return await call_next(request)


@bentoml.service
class ModelService:
    def __init__(self):
        self.model_name = get_current_model_name()
        self.model = load_model(self.model_name)
        set_model_loaded(self.model is not None, self.model_name)

    @bentoml.api
    def reload_model(self) -> dict:
        """Reload the selected model inside the model worker process."""
        model_name = get_current_model_name()
        model = load_model(model_name)
        if model is None:
            raise RuntimeError("Aucun modèle de prédiction n'est disponible.")
        self.model = model
        self.model_name = model_name
        set_model_loaded(True, model_name)
        logger.info("Modèle rechargé: %s", model_name)
        return {
            "status": "Model reloaded successfully",
            "model_version": model_name,
        }

    @bentoml.api
    def predict_array(self, features: dict[str, int | float | str]) -> dict:
        if self.model is None:
            raise RuntimeError("Aucun modèle de prédiction n'est disponible.")
        x = pd.DataFrame([features])
        predicted_class = int(np.asarray(self.model.predict(x)).ravel()[0])

        probability = None
        predict_proba = getattr(self.model, "predict_proba", None)
        if callable(predict_proba):
            try:
                proba = np.asarray(predict_proba(x), dtype=float).ravel()
                probability = float(proba[-1])
            except (ValueError, TypeError, IndexError, RuntimeError):
                logger.exception("Probabilité indisponible pour le modèle courant.")

        return {
            "prediction": predicted_class,
            "probability": probability,
            "model_version": self.model_name,
        }


@bentoml.asgi_app(app)
@bentoml.service
class PredictionService:
    model_service = bentoml.depends(ModelService)

    @bentoml.api(route="/reload")
    def reload_model(self) -> dict:
        try:
            return self.model_service.reload_model()
        except (RuntimeError, bentoml.exceptions.BentoMLException):
            logger.exception("Échec du rechargement dans le service modèle.")
            record_error(503)
            return JSONResponse(
                status_code=503,
                content={"detail": "Modèle de prédiction indisponible"},
            )

    @bentoml.api(route="/predict")
    def predict(self, input_data: InputData) -> dict:
        record_request()
        with track_latency():
            try:
                features = input_data.model_dump()
                features["month"] = features["mois"]
                for name, labels in CATEGORY_LABELS.items():
                    features[name] = labels[features[name]]
            except (ValueError, KeyError):
                logger.warning(
                    "Requête de prédiction rejetée: données non convertibles."
                )
                record_error(400)
                return JSONResponse(
                    status_code=400, content={"detail": "Invalid input data"}
                )

            try:
                result = self.model_service.predict_array(features)
                record_prediction(
                    result["prediction"],
                    result.get("probability"),
                    result.get("model_version", "unknown"),
                )
                return {
                    "prediction": result["prediction"],
                    "probability": result.get("probability"),
                    "model_version": result.get("model_version", "unknown"),
                }
            except (RuntimeError, bentoml.exceptions.BentoMLException):
                logger.exception("Service modèle indisponible ou en échec.")
                record_error(503)
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Modèle de prédiction indisponible"},
                )
            except (TypeError, ValueError, KeyError) as e:
                logger.exception("Échec de la prédiction.")
                record_error(500)
                return JSONResponse(
                    status_code=500,
                    content={"detail": f"Prediction error: {e!s}"},
                )


# Appliquer le middleware sur tout le service
PredictionService.add_asgi_middleware(JWTAuthMiddleware)
