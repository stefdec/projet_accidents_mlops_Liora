import datetime
import json
import logging
import os
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)


# Classes de schéma Pydantic pour les requêtes et réponses de l'API
class UserRequestSchema(BaseModel):
    username: str = Field(
        ..., description="Nom d'utilisateur de l'utilisateur", min_length=3
    )
    password: str = Field(
        ..., description="Mot de passe de l'utilisateur", min_length=5
    )
    token_type: str | None = Field(
        None, description="Type de jeton à générer (login, pull ou train)"
    )


class TokenResponseSchema(BaseModel):
    access_token: str = Field(..., description="Jeton d'accès JWT généré")


class UserListResponseSchema(BaseModel):
    users: list[str] = Field(
        ..., description="Liste des noms d'utilisateur des utilisateurs configurés"
    )


# Creation de la fonction de gestion du cycle de vie de l'application FastAPI avec les variables d'état et les paramètres JWT
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise les utilisateurs et paramètres JWT au démarrage de l'API."""
    logger.info("Starting up...")

    app.state.token_types = ["login", "pull", "train"]
    app.state.USERS = json.loads(os.environ["USERS"])
    app.state.ADMIN_USERS = json.loads(os.environ["ADMIN_USERS"])
    app.state.PULL_USERS = json.loads(os.environ["PULL_USERS"])
    app.state.TRAIN_USERS = json.loads(os.environ["TRAIN_USERS"])
    app.state.JWT_SECRET_LOGIN = os.environ["JWT_SECRET_LOGIN"]
    app.state.JWT_SECRET_PULL = os.environ["JWT_SECRET_PULL"]
    app.state.JWT_SECRET_TRAIN = os.environ["JWT_SECRET_TRAIN"]
    app.state.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    app.state.JWT_EXPIRATION_MINUTES = 60

    yield

    logger.info("Shutting down...")


# Initialisation de l'application FastAPI
app = FastAPI(
    title="Projet Accidents MLOps Authentification",
    description="API qui gere l'authentification des utilisateurs pour le projet Accidents MLOps",
    version="0.1.0",
    lifespan=lifespan,
)


def _authenticate_user(username: str, password: str):
    """Vérifie que les identifiants correspondent à un utilisateur configuré."""
    return app.state.USERS.get(username) == password


def _encode_jwt(user: str, token_type: str):
    payload = {
        "username": user,
        "token_type": token_type,
        "role": token_type,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=app.state.JWT_EXPIRATION_MINUTES),
    }
    if token_type == "pull":
        secret = app.state.JWT_SECRET_PULL
    elif token_type == "train":
        secret = app.state.JWT_SECRET_TRAIN
    else:
        secret = app.state.JWT_SECRET_LOGIN
    return jwt.encode(payload, secret, algorithm=app.state.JWT_ALGORITHM)


def _generate_pull_token(username: str):
    """Génère un jeton pull pour un utilisateur autorisé."""
    if username not in app.state.PULL_USERS:
        logger.warning("Unauthorized pull token request for user: %s", username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur non autorisé à obtenir un jeton pull",
        )
    logger.info("Generating pull token for user: %s", username)
    return _encode_jwt(username, "pull")


def _generate_train_token(username: str):
    """Génère un jeton portant le rôle train pour un compte autorisé."""
    if username not in app.state.TRAIN_USERS:
        logger.warning("Unauthorized train token request for user: %s", username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur non autorisé à obtenir un jeton train",
        )
    logger.info("Generating train token for user: %s", username)
    return _encode_jwt(username, "train")


def _generate_token(username: str, token_type: str):
    """Valide le type demandé et génère le jeton JWT correspondant."""
    if token_type not in app.state.token_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de jeton invalide.",
        )
    logger.info("Generating %s token for user: %s", token_type, username)

    if token_type == "pull":
        logger.info("Generating pull token for user: %s", username)
        return _generate_pull_token(username)

    if token_type == "train":
        return _generate_train_token(username)

    logger.info("Generating login token for user: %s", username)
    return _encode_jwt(username, "login")


@app.post("/login")
def login(user: UserRequestSchema):
    """Authentifie un utilisateur et retourne le jeton JWT demandé."""
    logger.info("Login attempt for user: %s", user.username)
    if not _authenticate_user(user.username, user.password):
        logger.warning("Failed login attempt for user: %s", user.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
        )

    logger.info("Successful login for user: %s", user.username)
    token = _generate_token(user.username, token_type=user.token_type)
    return TokenResponseSchema(access_token=token)


@app.get("/health")
def health_check():
    """Retourne l'état de disponibilité du service."""
    return {"status": "ok"}


@app.get("/users")
def list_users(user: UserRequestSchema):
    """Retourne les noms des utilisateurs accessibles après authentification."""
    logger.info("List users attempt by user: %s", user.username)
    if (
        not _authenticate_user(user.username, user.password)
        or user.username not in app.state.ADMIN_USERS
    ):
        logger.warning("Unauthorized list users attempt by user: %s", user.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
        )
    return UserListResponseSchema(users=list(app.state.USERS.keys()))
