FROM python:3.12-slim

ARG MLFLOW_VERSION=3.15.2
ARG FASTAPI_VERSION=0.141.1
ARG STARLETTE_VERSION=1.6.0
ARG ANYIO_VERSION=4.14.2
ARG UVICORN_VERSION=0.52.4
ARG APP_UID=1000
ARG APP_GID=1000

RUN pip install --no-cache-dir \
    "mlflow==${MLFLOW_VERSION}" \
    "fastapi==${FASTAPI_VERSION}" \
    "starlette==${STARLETTE_VERSION}" \
    "anyio==${ANYIO_VERSION}" \
    "uvicorn==${UVICORN_VERSION}" \
    "psycopg2-binary>=2.9,<3" \
    && if getent group "${APP_GID}" >/dev/null; then :; else groupadd --gid "${APP_GID}" mlflow; fi \
    && useradd --create-home --uid "${APP_UID}" --gid "${APP_GID}" mlflow \
    && mkdir -p /mlartifacts \
    && chown -R mlflow:"${APP_GID}" /mlartifacts

USER mlflow
WORKDIR /home/mlflow

EXPOSE 5000

ENTRYPOINT ["mlflow"]
