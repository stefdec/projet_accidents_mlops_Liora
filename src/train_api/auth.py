"""JWT authentication boundary for training endpoints."""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import Header, HTTPException, status

from src.train_api.config import load_settings


def require_train_token(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Validate a bearer JWT carrying the claims required for training."""
    if authorization is None:
        raise _unauthorized("Missing authentication token")

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise _unauthorized("Invalid authentication scheme")

    settings = load_settings()
    if settings.jwt_secret_train is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Training authentication is not configured",
        )

    try:
        payload = jwt.decode(
            token.strip(),
            settings.jwt_secret_train,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise _unauthorized("Token has expired") from error
    except jwt.InvalidTokenError as error:
        raise _unauthorized("Invalid token") from error

    if payload.get("token_type") != "train" or payload.get("role") != "train":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient token claims",
        )
    return payload


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
