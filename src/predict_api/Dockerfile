FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVICE=service:PredictionService \
    PORT=8000

WORKDIR /app

# Dépendances système nécessaires à LightGBM
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv
RUN pip install --no-cache-dir uv

# Installation des dépendances Python
COPY requirements.txt ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# Code applicatif
COPY service.py ./
COPY metrics.py ./

EXPOSE 8000

CMD ["/bin/sh", "-c", "bentoml serve ${SERVICE} --port ${PORT}", "--api-workers", "1"]
