FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BASE_DATASET_PATH=/var/lib/train-api/input/data_final_binaire.csv \
    INCOMING_DATA_DIR=/var/lib/train-api/incoming \
    ARTIFACT_ROOT=/var/lib/train-api/artifacts \
    STATE_DB_PATH=/var/lib/train-api/state/train-api.sqlite3 \
    TMP_DIR=/var/lib/train-api/artifacts/.tmp

ARG SOURCE_GIT_COMMIT=unknown
ARG APP_UID=1000
ARG APP_GID=1000
ENV SOURCE_GIT_COMMIT=${SOURCE_GIT_COMMIT}

WORKDIR /app

# Dépendances système nécessaires, notamment OpenMP pour LightGBM
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv
RUN pip install --no-cache-dir uv

# Installation des dépendances Python
COPY src/train_api/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install \
        --system \
        --requirement requirements.txt

# Création de l'utilisateur non-root avec les identifiants du propriétaire hôte.
# Cela permet l'écriture dans le bind mount data/train-api-v2/artifacts.
RUN if getent group "${APP_GID}" >/dev/null; then \
        APP_GROUP="$(getent group "${APP_GID}" | cut -d: -f1)"; \
    else \
        groupadd --gid "${APP_GID}" app; \
        APP_GROUP=app; \
    fi \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --home-dir /app --no-create-home app \
    && mkdir -p \
        /var/lib/train-api/input \
        /var/lib/train-api/incoming \
        /var/lib/train-api/artifacts \
        /var/lib/train-api/state \
        /var/lib/train-api/artifacts/.tmp \
    && chown -R app:"${APP_GID}" \
        /app \
        /var/lib/train-api

# Code applicatif
COPY --chown=app:app src/train_api/ ./src/train_api/

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]

CMD ["uvicorn", "src.train_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
