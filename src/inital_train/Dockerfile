FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BENTOML_HOME=/bentoml

ARG APP_UID=1000
ARG APP_GID=1000

WORKDIR /app

RUN if getent group "${APP_GID}" >/dev/null; then \
        APP_GROUP="$(getent group "${APP_GID}" | cut -d: -f1)"; \
    else \
        groupadd --gid "${APP_GID}" app; \
        APP_GROUP=app; \
    fi \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --home-dir /app --no-create-home app \
    && mkdir -p /bentoml \
    && chown app:"${APP_GROUP}" /app /bentoml

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=${APP_UID}:${APP_GID} main.py ./main.py
COPY --chmod=755 entrypoint.sh /usr/local/bin/initial-train-entrypoint

ENTRYPOINT ["/usr/local/bin/initial-train-entrypoint"]
CMD ["python", "main.py"]
