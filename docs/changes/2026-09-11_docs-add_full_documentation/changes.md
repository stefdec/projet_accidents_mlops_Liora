## Planifier la documentation opérationnelle du parcours v2

**Message de commit**

`docs(operations): plan v2 operational wiki documentation`

**Ce qui a changé**

- Création d'un plan pour documenter les APIs v2 une par une dans `docs/operations`.
- Ajout d'une étape finale dédiée à l'orchestration par `makefile2.mk` et au DAG Airflow associé.
- Exclusion explicite des variantes v1 du parcours documenté.

**Pourquoi**

- Stabiliser les règles métier et les critères de validation de chaque API avant de documenter leur enchaînement.
- Éviter de mélanger les composants v1 non utilisés avec le parcours opérationnel v2.

**Fichiers**

- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- Branche vérifiée : `docs/add_full_documentation`.
- Parcours v2 vérifié dans `makefile2.mk` et `docker-compose.apis.yml`.
- Aucun code applicatif modifié.

## Documenter les règles métier de l'authentification v2

**Message de commit**

`docs(operations): document auth API business rules`

**Ce qui a changé**

- Création de la fiche `auth-api` avec les endpoints, rôles JWT, prérequis et erreurs.
- Ajout des scénarios de validation pour les accès `login`, `pull`, `train` et administrateur.
- Ajout des précautions de diagnostic sans exposition de secrets.

**Pourquoi**

- Formaliser le contrat d'authentification utilisé par les APIs et l'orchestration v2.
- Permettre une validation reproductible avant la fiche de collecte.

**Fichiers**

- `docs/operations/auth-api.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `uv run pytest tests/test_auth_api.py` : bloqué par un accès interdit au cache global UV.
- `pytest tests/test_auth_api.py` : impossible, commande `pytest` absente.
- `git diff --check` : réussi.
- Relecture croisée avec `src/auth_api/main.py`, `tests/test_auth_api.py`, `.env.example` et `docker-compose.apis.yml`.

## Documenter les règles métier de la collecte hebdomadaire

**Message de commit**

`docs(operations): document data pull API business rules`

**Ce qui a changé**

- Création de la fiche `pull-data-api` avec les règles de calendrier 2024 et le contrat Parquet.
- Documentation de l'authentification pull, des erreurs, du stockage partagé et des contrôles de dataset.
- Ajout d'une procédure de validation reproductible et des points de diagnostic.

**Pourquoi**

- Formaliser le lot hebdomadaire consommé par `train-api-v2` et par le DAG `pull_train`.
- Vérifier les limites de période et les conditions qui doivent interrompre le parcours.

**Fichiers**

- `docs/operations/pull-data-api.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `uv run pytest tests/test_pull_data_api.py` : 5 tests réussis.
- `git diff --check` : réussi.
- Relecture croisée avec `src/pull_data_api/main.py`, `tests/test_pull_data_api.py`, `docker-compose.apis.yml` et `src/airflow_dags/dags/pull_train.py`.

## Documenter les règles métier de `train-api`

**Message de commit**

`docs(operations): document training API v2 business rules`

**Ce qui a changé**

- Création de la fiche métier `train-api` sous son nom fonctionnel demandé.
- Documentation des modes initial et weekly, de l'idempotence, de la concurrence et de la reprise.
- Documentation de la validation temporelle, de la promotion MLflow, des erreurs HTTP et des effets persistants.

**Pourquoi**

- Formaliser le contrat d'entraînement consommé par `initial-train` et le DAG `pull_train`.
- Rendre vérifiables les décisions de promotion et les comportements de reprise.

**Fichiers**

- `docs/operations/train-api.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `uv run pytest tests/train_api_v2/test_schemas.py tests/train_api_v2/test_initial_api.py tests/train_api_v2/test_weekly_api.py tests/train_api_v2/test_errors.py tests/train_api_v2/test_auth.py tests/train_api_v2/test_state.py tests/train_api_v2/test_initial_service.py` : 46 tests réussis.
- `git diff --check` : réussi.
- Relecture croisée avec les modules `src/train_api_v2`, les tests ciblés, `makefile2.mk` et `docker-compose.apis.yml`.

## Documenter le bootstrap `initial-train`

**Message de commit**

`docs(operations): document initial training bootstrap`

**Ce qui a changé**

- Création de la fiche dédiée au composant one-shot `initial-train`.
- Documentation de la séquence auth → train initial → publication BentoML → reload prédiction.
- Documentation des prérequis, variables, retries, codes de sortie, idempotence et diagnostics.

**Pourquoi**

- Formaliser l'initialisation du modèle avant l'exécution du parcours Airflow.
- Rendre vérifiable la synchronisation entre MLflow, BentoML et l'API de prédiction.

**Fichiers**

- `docs/operations/initial-training.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `uv run pytest tests/test_initial_train_trigger.py` : 11 tests réussis.
- `git diff --check` : réussi.
- Relecture croisée avec `src/inital_train/main.py`, `tests/test_initial_train_trigger.py`, `makefile2.mk` et `docker-compose.apis.yml`.

## Documenter les règles métier de l'API de prédiction v2

**Message de commit**

`docs(operations): document prediction API v2 business rules`

**Ce qui a changé**

- Création de la fiche de prédiction avec les contrats `/predict`, `/reload` et `/health`.
- Documentation du payload, des mappings de catégories, de l'authentification et des erreurs.
- Documentation du chargement BentoML, du pointeur courant, des métriques et des scénarios de diagnostic.
- Signalement de la vérification à effectuer sur le montage effectif de `/metrics`.

**Pourquoi**

- Formaliser le comportement de l'inférence et son lien avec le modèle publié par `initial-train`.
- Rendre vérifiables les cas de modèle indisponible, reload et conversion du payload.

**Fichiers**

- `docs/operations/predict-api-v2.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `uv run pytest tests/test_predict_api_v2_service.py` : 24 tests réussis.
- `git diff --check` : réussi.
- Relecture croisée avec `src/predict_api_v2/service.py`, `src/predict_api_v2/metrics.py`, les tests ciblés et `docker-compose.apis.yml`.

## Documenter MLflow et le cycle de vie du modèle

**Message de commit**

`docs(operations): document MLflow model lifecycle`

**Ce qui a changé**

- Création de la fiche MLflow avec l'architecture Tracking, Registry, PostgreSQL et artefacts.
- Documentation du cycle run → candidat → champion → BentoML.
- Documentation de la configuration, de la persistance, de la lineage et des diagnostics.

**Pourquoi**

- Formaliser la gestion du modèle utilisée par `train-api`, `initial-train` et la prédiction.
- Distinguer clairement le rôle de MLflow de celui de DVC dans le parcours v2.

**Fichiers**

- `docs/operations/mlflow.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `uv run pytest tests/train_api_v2/test_mlflow_service.py tests/train_api_v2/test_initial_service.py tests/train_api_v2/test_initial_api.py tests/train_api_v2/test_weekly_api.py` : 9 tests réussis.
- `git diff --check` : réussi.
- Relecture croisée avec `src/train_api_v2/mlflow_service.py`, `src/infra/mlflow/docker-compose.mlflow.yml`, `initial-train` et la configuration v2.

## Structurer l'index wiki opérationnel v2

**Message de commit**

`docs(operations): define v2 operational wiki architecture`

**Ce qui a changé**

- Refonte de `docs/operations/README.md` comme point d'entrée du wiki.
- Ajout d'un schéma Mermaid couvrant APIs v2, Makefile, Airflow, MLflow, données et observabilité.
- Ajout de l'ordre de validation et des règles communes de documentation.

**Pourquoi**

- Donner une vue complète du parcours v2 avant de documenter chaque composant.
- Préparer une navigation cohérente pour les fiches des étapes suivantes.

**Fichiers**

- `docs/operations/README.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `git diff --check` : réussi.
- Les composants du schéma ont été vérifiés dans `makefile2.mk`, les fichiers Compose et les configurations Prometheus/Alloy.
- Les liens vers les fiches futures sont inventoriés et seront résolus lors des étapes correspondantes.

## Étendre le plan à l'observabilité et à l'orchestration complète

**Message de commit**

`docs(operations): expand v2 operational documentation plan`

**Ce qui a changé**

- Ajout d'une fiche dédiée au bootstrap `initial-train`.
- Ajout des étapes MLflow, métriques/Prometheus, Loki/Alloy et Grafana.
- Extension de l'étape finale au Makefile v2 et au DAG Airflow `pull_train`.
- Ajout prévu d'un schéma Mermaid complet dans `docs/operations/README.md`.

**Pourquoi**

- Couvrir les composants indispensables au fonctionnement et au diagnostic de la stack v2.
- Rendre visible le parcours complet, de l'initialisation jusqu'à l'observabilité.

**Fichiers**

- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- Cibles Makefile v2, services Compose, DAG `pull_train` et configurations de monitoring relus.
- Aucun code applicatif modifié.

## Documenter les métriques et la collecte Prometheus

**Message de commit**

`docs(operations): document Prometheus metrics collection`

**Ce qui a changé**

- Création de la fiche Prometheus avec les jobs et cibles réellement configurés.
- Documentation des métriques de prédiction, drift, performance ML et soutenabilité.
- Documentation de la fraîcheur, de la cardinalité, des diagnostics et des règles d'alerte.
- Signalement de la vérification nécessaire sur le montage effectif de `/metrics` pour la prédiction.

**Pourquoi**

- Rendre exploitable la chaîne métriques → Prometheus → dashboards/alertes.
- Distinguer les métriques réellement collectées des endpoints `/health` et des logs utilisés pour les autres APIs.

**Fichiers**

- `docs/operations/metrics-prometheus.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- `docker compose --env-file .env -f docker-compose.monitoring.yml config` : réussi ; avertissement non bloquant sur `GF_SLACK_WEBHOOK` absent.
- `uv run pytest tests/train_api_v2/test_monitoring.py` : 4 tests réussis.
- `uv run pytest tests/test_docker_architecture.py` : 1 échec préexistant hors périmètre sur `sl-ocs-v1`, 9 tests réussis.
- `git diff --check` : réussi.

## Documenter les logs, dashboards et l'orchestration v2

**Message de commit**

`docs(operations): document v2 observability and orchestration`

**Ce qui a changé**

- Création des fiches Alloy/Loki et Grafana.
- Création de la fiche d'orchestration `makefile2.mk` et Airflow `pull_train`.
- Documentation des flux de logs, métriques, alertes, retries, branches de promotion et resets.
- Finalisation de la navigation wiki opérationnelle v2.

**Pourquoi**

- Couvrir les trois dernières étapes du parcours opérationnel : observabilité et orchestration complète.
- Fournir un seul parcours de diagnostic depuis le Makefile jusqu'aux APIs et dashboards.

**Fichiers**

- `docs/operations/logs-loki-alloy.md`
- `docs/operations/grafana.md`
- `docs/operations/orchestration-makefile-v2.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/plan.md`
- `docs/changes/2026-09-11_docs-add_full_documentation/changes.md`

**Validation**

- Configurations Compose monitoring, MLflow, APIs et Airflow : validées.
- `uv run pytest src/airflow_dags/tests/test_pull_train.py` : 19 tests réussis, 1 échec préexistant car le test attend `schedule=None` alors que le DAG définit `schedule="0 3 * * 1"`.
- Liens wiki internes vérifiés.
- `git diff --check` : réussi.
