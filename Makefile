SHELL := /bin/bash
.DEFAULT_GOAL := help
# Les opérations de démarrage et de reset doivent rester séquentielles.
.NOTPARALLEL:

ENV_FILE ?= .env
NETWORK := accidents-shared-network
# Stable defaults for reproducible builds; override explicitly on bind-mounted hosts.
LOCAL_UID ?= 1000
LOCAL_GID ?= 1000
COMPOSE_FILE := src/infra/mlflow/docker-compose.mlflow.yml
MLFLOW_COMPOSE := docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE)
API_COMPOSE := LOCAL_UID=$(LOCAL_UID) LOCAL_GID=$(LOCAL_GID) docker compose --env-file $(ENV_FILE) -f docker-compose.apis.yml
MONITORING_COMPOSE := docker compose --env-file $(ENV_FILE) -f docker-compose.monitoring.yml
AIRFLOW_DIR := src/airflow_dags
AIRFLOW_COMPOSE := ENV_FILE_PATH=$(abspath $(ENV_FILE)) AIRFLOW_UID=$(LOCAL_UID) docker compose --env-file $(ENV_FILE) -f $(AIRFLOW_DIR)/docker-compose.yaml

# Surcharge possible : make init TRAIN_USERNAME=... TRAIN_PASSWORD=...
TRAIN_USERNAME ?= alice
TRAIN_PASSWORD ?= wonderland
INITIAL_IDEMPOTENCY_KEY ?= initial-bootstrap

export ENV_FILE TRAIN_USERNAME TRAIN_PASSWORD INITIAL_IDEMPOTENCY_KEY
API_SERVICES := auth-api pull-data-api train-api predict-api emergency-interface
PRESENTATION_PORT ?= 8501

.PHONY: help install presentation core-stack-up stack-up init initial-train monitoring-up monitoring-down airflow-up stack-down stack-status stack-logs predict-smoke dvc-pull dvc-push reproduce metrics network runtime-dirs reset reset-full

help:
	@echo "make install         Installe les dépendances verrouillées et prépare .env"
	@echo "make init            Démarre la stack et initialise/publie le champion"
	@echo "make stack-up        Démarre MLflow, monitoring, API, emergency-interface et Airflow"
	@echo "make stack-down      Arrête la stack en conservant ses données et volumes"
	@echo "make stack-status    Affiche tous les services"
	@echo "make stack-logs      Affiche les 100 dernières lignes par service"
	@echo "make presentation    Lance app-pres.py au premier plan sur le port 8501 (Ctrl+C)"
	@echo "make initial-train   Construit et exécute le bootstrap one-shot (stack déjà active)"
	@echo "make predict-smoke   Vérifie une prédiction authentifiée avec payload.json"
	@echo "make airflow-up / monitoring-up / monitoring-down"
	@echo "make dvc-pull / dvc-push / reproduce / metrics"
	@echo "make reset / reset-full  DESTRUCTIF : efface les états runtime ; datasets conservés"

install: $(ENV_FILE)
	@uv sync --frozen --extra monitoring

presentation:
	@uv run --frozen python app-pres.py --server.headless true --server.address 127.0.0.1 --server.port $(PRESENTATION_PORT)

# Ordre partagé par stack-up et init : MLflow, monitoring, API + interface.
core-stack-up: $(ENV_FILE) network runtime-dirs
	@$(MLFLOW_COMPOSE) up -d --build --wait --wait-timeout 180
	@$(MAKE) --no-print-directory monitoring-up
	@$(API_COMPOSE) build $(API_SERVICES)
	@$(API_COMPOSE) up -d --wait --wait-timeout 180 $(API_SERVICES)

stack-up: core-stack-up
	@$(MAKE) --no-print-directory airflow-up
	@echo "Stack démarrée sans entraînement initial. Présentation : make presentation dans un second terminal."

init: core-stack-up
	@$(MAKE) --no-print-directory initial-train
	@$(MAKE) --no-print-directory airflow-up
	@echo "Stack initialisée. Présentation : make presentation dans un second terminal."

initial-train: $(ENV_FILE)
	@$(API_COMPOSE) --profile manual build initial-train
	@$(API_COMPOSE) --profile manual run --rm --no-deps initial-train

monitoring-up: $(ENV_FILE) network
	@$(MONITORING_COMPOSE) up -d --build --wait --wait-timeout 180

monitoring-down: $(ENV_FILE)
	@$(MONITORING_COMPOSE) down --remove-orphans

# Les services Airflow partagent une image : construire une seule fois.
airflow-up: $(ENV_FILE) network runtime-dirs
	@$(AIRFLOW_COMPOSE) build airflow-init
	@$(AIRFLOW_COMPOSE) up -d --no-build --wait --wait-timeout 300

stack-down: $(ENV_FILE)
	@$(AIRFLOW_COMPOSE) down --remove-orphans
	@$(API_COMPOSE) down --remove-orphans
	@$(MLFLOW_COMPOSE) down --remove-orphans
	@$(MONITORING_COMPOSE) down --remove-orphans

stack-status: $(ENV_FILE)
	@$(MLFLOW_COMPOSE) ps --all
	@$(API_COMPOSE) ps --all
	@$(AIRFLOW_COMPOSE) ps --all
	@$(MONITORING_COMPOSE) ps --all

stack-logs: $(ENV_FILE)
	@$(MLFLOW_COMPOSE) logs --tail=100
	@$(API_COMPOSE) logs --tail=100
	@$(AIRFLOW_COMPOSE) logs --tail=100
	@$(MONITORING_COMPOSE) logs --tail=100

predict-smoke: $(ENV_FILE)
	@uv run --frozen python scripts/predict_api_smoke_test.py

dvc-pull:
	@uv run --frozen dvc pull

dvc-push:
	@uv run --frozen dvc push

reproduce:
	@uv run --frozen dvc repro

metrics:
	@uv run --frozen dvc metrics show

$(ENV_FILE):
	@cp .env.example $(ENV_FILE)
	@echo ".env créé depuis .env.example"

network:
	@docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK) >/dev/null

runtime-dirs:
	@mkdir -p data/incoming data/mlflow/postgres data/mlflow/artifacts $(AIRFLOW_DIR)/logs
	@docker run --rm -v "$(CURDIR)/data:/d" alpine sh -c 'mkdir -p /d/train-api-v2/artifacts /d/train-api-v2/state && chmod -R 777 /d/train-api-v2'
	@docker run --rm -v "$(CURDIR)/data:/d" alpine sh -c 'chgrp -R 0 /d/incoming && chmod -R 775 /d/incoming'


# Commande pour réinitialiser l'état de la stack et supprimer les volumes Docker associés
# ⚠️ Cette commande arrête les conteneurs, supprime les volumes Docker et les répertoires runtime, mais conserve les datasets.
reset:
	@echo "🧹 Arrêt d’Airflow et suppression de sa base…"
	@$(AIRFLOW_COMPOSE) down --remove-orphans --volumes
	@echo "🧹 Arrêt des API et suppression de leur état runtime…"
	@$(API_COMPOSE) down --remove-orphans
	@echo "🧹 Arrêt de MLflow et suppression de son état runtime…"
	@$(MLFLOW_COMPOSE) down --remove-orphans
	@echo "🧹 Arrêt du monitoring…"
	@$(MONITORING_COMPOSE) down --remove-orphans
	@set -e; for volume in train_api_v2_state bentoml_store; do \
		if docker volume inspect "$$volume" >/dev/null 2>&1; then \
			docker volume rm "$$volume" >/dev/null; \
		fi; \
	done
	@rm -rf -- data/train-api-v2/artifacts data/train-api-v2/state
	@docker run --rm -v "$(CURDIR)/data/mlflow:/d" alpine rm -rf /d/postgres /d/artifacts
	@docker run --rm -v "$(CURDIR)/$(AIRFLOW_DIR)/logs:/d" alpine sh -c 'rm -rf /d/*'
	@$(MAKE) --no-print-directory runtime-dirs
	@echo "✅ État réinitialisé. Les datasets data/features et data/incoming sont conservés."

# Commande pour réinitialiser complètement la stack, y compris les images locales Docker
# ⚠️ Cette commande arrête les conteneurs, supprime les images locales Docker, les volumes Docker et les répertoires runtime, mais conserve les datasets.
reset-full:
	@echo "🧹 Arrêt d’Airflow et suppression de sa base et de ses images locales…"
	@$(AIRFLOW_COMPOSE) down --remove-orphans --volumes --rmi local
	@echo "🧹 Arrêt des API et suppression de leur état runtime…"
	@$(API_COMPOSE) down --remove-orphans --rmi local
	@echo "🧹 Arrêt de MLflow et suppression de son état runtime…"
	@$(MLFLOW_COMPOSE) down --remove-orphans --rmi local
	@echo "🧹 Arrêt du monitoring et suppression de ses images/volumes locaux…"
	@$(MONITORING_COMPOSE) down --remove-orphans --volumes --rmi local

	@set -e; for volume in train_api_v2_state bentoml_store; do \
		if docker volume inspect "$$volume" >/dev/null 2>&1; then \
			docker volume rm "$$volume" >/dev/null; \
		fi; \
	done

	@rm -rf -- data/train-api-v2/artifacts data/train-api-v2/state
	@docker run --rm -v "$(CURDIR)/data/mlflow:/d" alpine rm -rf /d/postgres /d/artifacts
	@docker run --rm -v "$(CURDIR)/$(AIRFLOW_DIR)/logs:/d" alpine sh -c 'rm -rf /d/*'

	@$(MAKE) --no-print-directory runtime-dirs

	@echo "✅ État réinitialisé, images locales supprimées. Les datasets data/features et data/incoming sont conservés."
