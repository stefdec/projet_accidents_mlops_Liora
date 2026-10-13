import logging
import os
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import jwt
import pandas as pd
import requests
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

DATASET_URL_DEFAULT = (
    "https://dagshub.com/Sacha3198/projet_accidents_MLOps/"
    "raw/main/data/features/data_final_binaire.csv"
)
START_2024 = pd.Timestamp("2024-01-01")
END_2024 = pd.Timestamp("2025-01-01")
MAX_WEEK_2024 = 52


class ResponseSchema(BaseModel):
    week: int = Field(..., description="Numéro de la semaine simulée en 2024")
    start_date: str = Field(..., description="Première date incluse")
    end_date_exclusive: str = Field(..., description="Borne finale exclusive")
    file_path: str = Field(..., description="Chemin du fichier Parquet sauvegardé")
    record_count: int = Field(..., description="Nombre de lignes exportées")


class JWTBearer(HTTPBearer):
    @staticmethod
    def _decode_jwt(token: str):
        secret = os.environ.get("JWT_SECRET_PULL")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        if not secret:
            return {}
        try:
            return jwt.decode(token, secret, algorithms=[algorithm])
        except jwt.InvalidTokenError:
            return {}

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials.scheme != "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
        if not self._decode_jwt(credentials.credentials):
            raise HTTPException(status_code=403, detail="Invalid token or expired token.")
        return credentials.credentials


def week_bounds_2024(week: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Retourne la fenêtre [début, fin) partagée avec le pipeline ML."""
    if isinstance(week, bool) or not isinstance(week, int):
        raise TypeError("week doit être un entier")
    if not 1 <= week <= MAX_WEEK_2024:
        raise ValueError(f"week doit être compris entre 1 et {MAX_WEEK_2024}")
    start = START_2024 + pd.to_timedelta(7 * (week - 1), unit="D")
    end = min(start + pd.to_timedelta(7, unit="D"), END_2024)
    return start, end


def extract_week(df: pd.DataFrame, week: int) -> pd.DataFrame:
    """Extrait une semaine réelle sans casser un accident entre deux fichiers."""
    required = {"Num_Acc", "accident_date"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Colonnes requises absentes : {missing}")

    start, end = week_bounds_2024(week)
    dates = pd.to_datetime(df["accident_date"], errors="coerce").dt.normalize()
    if dates.isna().any():
        raise ValueError("Le dataset contient des accident_date invalides")

    mask = (dates >= start) & (dates < end)
    weekly = df.loc[mask].copy()
    if weekly.empty:
        raise ValueError(f"Aucune donnée disponible pour la semaine {week}")
    weekly["accident_date"] = dates.loc[mask].to_numpy()

    group_dates = weekly.groupby("Num_Acc", dropna=False)["accident_date"].nunique()
    if group_dates.gt(1).any():
        raise ValueError("Un accident possède plusieurs dates dans la semaine")
    return weekly.sort_values(["accident_date", "Num_Acc"], kind="stable")


def download_dataset() -> pd.DataFrame:
    username = os.environ.get("DAGSHUB_USERNAME")
    token = os.environ.get("DAGSHUB_TOKEN")
    if not username or not token:
        raise RuntimeError("DAGSHUB_USERNAME et DAGSHUB_TOKEN sont obligatoires")
    response = requests.get(
        os.getenv("DAGSHUB_DATASET_URL", DATASET_URL_DEFAULT),
        auth=(username, token),
        timeout=60,
    )
    response.raise_for_status()
    return pd.read_csv(BytesIO(response.content), low_memory=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading dataset from DagsHub...")
    app.state.dataset = download_dataset()
    logger.info("Dataset loaded successfully: %d rows", len(app.state.dataset))
    yield


app = FastAPI(
    title="Projet Accidents MLOps Pull Data",
    description=(
        "Exporte une semaine 2024 au format Parquet, selon le même calendrier "
        "que le pipeline de réentraînement DVC."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/pull_data", dependencies=[Depends(JWTBearer())])
async def return_weekly_data(
    week: int = Query(..., ge=1, le=MAX_WEEK_2024),
):
    start, end = week_bounds_2024(week)
    weekly = extract_week(app.state.dataset, week)
    output_dir = Path(os.getenv("SHARED_DATA_DIRECTORY", "/shared-data"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"accidents_2024_w{week:02d}.parquet"
    weekly.to_parquet(output_path, index=False)
    logger.info("Exported week %02d: %d rows", week, len(weekly))

    return ResponseSchema(
        week=week,
        start_date=start.date().isoformat(),
        end_date_exclusive=end.date().isoformat(),
        file_path=str(output_path),
        record_count=len(weekly),
    )
