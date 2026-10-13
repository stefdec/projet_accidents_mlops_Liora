# Plan d'implémentation

## Objectif

Créer une documentation opérationnelle sous forme de wiki dans `docs/operations`, avec `README.md` comme point d'entrée et un schéma Mermaid complet. La documentation doit valider séparément les APIs v2, documenter `initial-train`, MLflow et l'observabilité, puis décrire l'orchestration complète du parcours piloté par `makefile2.mk` et le DAG Airflow `pull_train`.

## Contexte

Le parcours de référence est la stack v2 pilotée par `makefile2.mk` : MLflow, monitoring, APIs v2, `initial-train`, puis Airflow. Le DAG `pull_train` est le flux métier hebdomadaire important : authentification, collecte, entraînement, évaluation, publication et rechargement du modèle lorsque nécessaire.

Le format retenu est un fichier par API v2 de référence, relié par un index Markdown. Chaque fiche comportera au minimum : responsabilité métier, prérequis, entrées et sorties, règles métier, erreurs attendues, dépendances, procédure de validation et critères d'acceptation. `initial-train` sera documenté dans une fiche dédiée comme composant one-shot, et non comme une API.

## Périmètre

### Inclus

- Refonte de `docs/operations/README.md` en index wiki, guide de lecture et schéma Mermaid complet.
- Documentation séquentielle des APIs v2 : authentification, collecte, entraînement et prédiction.
- Documentation dédiée de `initial-train`, MLflow, Prometheus, Grafana, Loki et Alloy.
- Procédures de validation métier et opérationnelle reproductibles, fondées sur le code, les tests et les configurations existants.
- Documentation finale de l'orchestration Makefile v2 et du DAG Airflow `pull_train`.

### Hors périmètre

- Modification du code applicatif, des contrats HTTP ou de la configuration Docker.
- Correction des incohérences métier éventuellement découvertes pendant la rédaction.
- Déploiement réel, exécution d'une stack distante ou création de secrets.
- Documentation exhaustive de Streamlit et des variantes v1.

## Étape 1 — Définir l'architecture du wiki et le parcours v2

**État : terminée**

### Objectif

Établir une navigation cohérente centrée exclusivement sur le parcours v2 orchestré par `makefile2.mk`, avec une vue d'ensemble de l'observabilité.

### Modifications prévues

- Transformer `docs/operations/README.md` en sommaire opérationnel avec ordre de validation.
- Ajouter les conventions communes de rédaction et le périmètre v2.
- Ajouter un schéma Mermaid complet reliant utilisateurs, APIs, Makefile, Airflow, MLflow, stockage, métriques, logs, Prometheus, Loki, Alloy et Grafana.
- Prévoir les liens vers chaque fiche et vers la fiche finale d'orchestration.

### Fichiers potentiellement concernés

- `docs/operations/README.md`

### Validation prévue

- Vérifier les liens relatifs déjà disponibles et inventorier les liens vers les fiches prévues aux étapes suivantes.
- Vérifier l'absence de référence opérationnelle aux variantes v1.
- Vérifier que les services, ports, volumes et flux du schéma correspondent aux fichiers Compose et aux cibles de `makefile2.mk`.

### Message de commit proposé

`docs(operations): define v2 operational wiki architecture`

## Étape 2 — Documenter et valider la logique métier de l'authentification

**État : terminée**

### Objectif

Décrire le rôle de `auth-api`, les types de jetons, les autorisations associées, les réponses d'erreur et les critères de validation du parcours d'authentification.

### Modifications prévues

- Créer une fiche dédiée à `auth-api`.
- Documenter `/login`, `/health` et, si pertinent pour l'exploitation, `/users`.
- Décrire les prérequis de configuration sans exposer de secrets.

### Fichiers potentiellement concernés

- `docs/operations/auth-api.md`
- `src/auth_api/main.py`
- `tests/test_auth_api.py`

### Validation prévue

- Relecture croisée des règles avec le code et les tests.
- Vérification des cas nominal, identifiants invalides, type de jeton invalide et rôle insuffisant.

### Message de commit proposé

`docs(operations): document auth API business rules`

## Étape 3 — Documenter et valider la logique métier de la collecte de données

**État : terminée**

### Objectif

Décrire la collecte hebdomadaire, les bornes de semaine 2024, le fichier produit, les contrôles d'accès et les erreurs attendues de `pull-data-api`.

### Modifications prévues

- Créer une fiche dédiée à `pull-data-api`.
- Documenter `/pull_data` et `/health`, notamment le paramètre `week`, la période couverte et la sortie Parquet.
- Relier la fiche aux attentes de stockage utilisées par le training.

### Fichiers potentiellement concernés

- `docs/operations/pull-data-api.md`
- `src/pull_data_api/main.py`
- `tests/test_pull_data_api.py`

### Validation prévue

- Vérifier les semaines valides et invalides, l'authentification pull et le contenu de la réponse.
- Vérifier la cohérence avec les volumes et variables de `docker-compose.apis.yml`.

### Message de commit proposé

`docs(operations): document data pull API business rules`

## Étape 4 — Documenter et valider la logique métier de l'entraînement v2

**État : terminée**

### Objectif

Décrire les modes initial et hebdomadaire, l'idempotence, les règles de données, l'évaluation, la promotion MLflow et les erreurs métier de `train-api-v2`.

### Modifications prévues

- Créer une fiche dédiée à `train-api-v2`.
- Documenter `/train` et `/health`, les requêtes, réponses, statuts HTTP et effets persistants.
- Décrire séparément le rôle de `initial-train` comme déclencheur de bootstrap, sans le présenter comme une API.

### Fichiers potentiellement concernés

- `docs/operations/train-api-v2.md`
- `src/train_api_v2/main.py`
- `src/train_api_v2/schemas.py`
- `src/train_api_v2/service.py`
- `tests/train_api_v2/test_initial_api.py`
- `tests/train_api_v2/test_weekly_api.py`
- `tests/train_api_v2/test_errors.py`

### Validation prévue

- Vérifier les scénarios initial, hebdomadaire, répétition idempotente, conflit, dataset absent/invalide et MLflow indisponible.
- Vérifier la cohérence avec les volumes, l'état SQLite et les variables de `docker-compose.apis.yml`.

### Message de commit proposé

`docs(operations): document training API v2 business rules`

## Étape 5 — Documenter le bootstrap `initial-train`

**État : terminée**

### Objectif

Décrire le composant one-shot qui déclenche le premier entraînement, publie le modèle dans BentoML et recharge l'API de prédiction.

### Modifications prévues

- Créer `initial-training.md`.
- Documenter la cible `initial-train`, ses prérequis, son idempotency key et ses timeouts.
- Décrire la séquence auth → train initial → publication du modèle → reload predict.
- Clarifier sa différence avec `/train` et son rôle dans la cible `init`.

### Fichiers potentiellement concernés

- `docs/operations/initial-training.md`
- `src/inital_train/main.py`
- `docker-compose.apis.yml`
- `makefile2.mk`
- `tests/test_initial_train_trigger.py`

### Validation prévue

- Vérifier les prérequis manquants, l'idempotence, la publication du modèle et l'échec du reload.
- Vérifier l'ordre réel exécuté par `make -f makefile2.mk init`.

### Message de commit proposé

`docs(operations): document initial training bootstrap`

## Étape 6 — Documenter et valider l'API de prédiction v2

**État : terminée**

### Objectif

Décrire le chargement du modèle courant, la prédiction authentifiée, le rechargement et les signaux de santé.

### Modifications prévues

- Créer `predict-api-v2.md`.
- Documenter `/predict`, `/reload`, `/health` et `/metrics` selon leur rôle opérationnel.
- Relier le modèle servi au modèle publié par le training et au fichier de sélection BentoML.

### Fichiers potentiellement concernés

- `docs/operations/predict-api-v2.md`
- `src/predict_api_v2/service.py`
- `src/predict_api_v2/metrics.py`
- `tests/test_predict_api_v2_service.py`

### Validation prévue

- Vérifier les scénarios sans modèle, modèle chargé, prédiction authentifiée, reload autorisé et payload invalide.
- Vérifier les métriques de requêtes, erreurs, latence et état du modèle.

### Message de commit proposé

`docs(operations): document prediction API v2 business rules`

## Étape 7 — Documenter MLflow et le cycle de vie du modèle

**État : terminée**

### Objectif

Expliquer le rôle de MLflow dans le tracking, les artefacts, le Registry, les versions candidates et l'alias champion.

### Modifications prévues

- Créer `mlflow.md`.
- Documenter MLflow/PostgreSQL, les volumes, l'URI de tracking et les accès utiles.
- Décrire le lien entre train-api-v2, `initial-train`, Registry MLflow et predict-api-v2.

### Fichiers potentiellement concernés

- `docs/operations/mlflow.md`
- `src/infra/mlflow/docker-compose.mlflow.yml`
- `src/train_api_v2/mlflow_service.py`
- `src/inital_train/main.py`

### Validation prévue

- Vérifier noms de services, ports, volumes et variables dans Compose.
- Vérifier le cycle candidat → promotion → modèle servi.

### Message de commit proposé

`docs(operations): document MLflow model lifecycle`

## Étape 8 — Documenter les métriques et Prometheus

**État : terminée**

### Objectif

Décrire la collecte des métriques techniques, métier, drift, performance ML et soutenabilité.

### Modifications prévues

- Créer `metrics-prometheus.md`.
- Documenter les endpoints `/metrics` et les exporters drift, ML et soutenabilité.
- Décrire les jobs Prometheus, les labels, la rétention et les diagnostics.
- Relier les métriques aux dashboards Grafana.

### Fichiers potentiellement concernés

- `docs/operations/metrics-prometheus.md`
- `docker-compose.monitoring.yml`
- `monitoring/prometheus/prometheus.yml`
- `src/predict_api_v2/metrics.py`
- `monitoring/exporters/drift/drift_metrics.py`
- `monitoring/exporters/ml/ml_metrics.py`
- `monitoring/exporters/sustainability/sustain_metrics.py`

### Validation prévue

- Vérifier les cibles et ports déclarés dans Prometheus.
- Vérifier la présence des métriques critiques et les liens vers les dashboards.
- Exécuter la validation Compose si l'environnement est disponible.

### Message de commit proposé

`docs(operations): document Prometheus metrics collection`

## Étape 9 — Documenter les logs avec Alloy et Loki

**État : terminée**

### Objectif

Décrire la collecte, le filtrage, la conservation et la recherche des logs des services v2.

### Modifications prévues

- Créer `logs-loki-alloy.md`.
- Documenter le flux Docker → Alloy → Loki → Grafana, les labels, les volumes et les contraintes de sécurité du socket Docker.
- Documenter les requêtes LogQL et le diagnostic d'une absence de logs.

### Fichiers potentiellement concernés

- `docs/operations/logs-loki-alloy.md`
- `docker-compose.monitoring.yml`
- `monitoring/alloy/config.alloy`
- `monitoring/loki/loki.yml`
- `docs/loki/README.md`

### Validation prévue

- Vérifier les services et dépendances Alloy/Loki dans Compose.
- Vérifier que les logs des APIs v2 sont ciblés et qu'aucun secret n'est documenté comme observable.

### Message de commit proposé

`docs(operations): document v2 observability and orchestration`

## Étape 10 — Documenter Grafana et les dashboards opérationnels

**État : terminée**

### Objectif

Donner aux opérateurs un point d'accès aux dashboards et une méthode de diagnostic croisant métriques et logs.

### Modifications prévues

- Créer `grafana.md`.
- Documenter le provisioning, les sources Prometheus/Loki, les dossiers et dashboards utiles.
- Relier les dashboards aux métriques et logs précédemment décrits.

### Fichiers potentiellement concernés

- `docs/operations/grafana.md`
- `docker-compose.monitoring.yml`
- `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `monitoring/grafana/dashboards/*.json`

### Validation prévue

- Vérifier les sources provisionnées, les dashboards présents et les URLs locales.

### Message de commit proposé

`docs(operations): document v2 observability and orchestration`

## Étape 11 — Documenter l'orchestration Makefile v2 et Airflow

**État : terminée**

### Objectif

Documenter le flux complet de `makefile2.mk` uniquement une fois les APIs, le modèle et l'observabilité stabilisés et reliés.

### Modifications prévues

- Créer `orchestration-makefile-v2.md` décrivant les cibles `init`, `stack-up`, `initial-train`, `airflow-up`, `monitoring-up`, `reset` et `reset-full`.
- Décrire l'ordre de démarrage MLflow → monitoring → APIs v2 → bootstrap initial → Airflow.
- Documenter le rôle du DAG Airflow dans l'orchestration finale : auth → pull → train → publication/rechargement.
- Documenter les dépendances, retries, timeouts, idempotence, conditions d'échec, points de reprise et conséquences des resets.
- Ajouter les liens vers toutes les fiches précédentes plutôt que de recopier leurs contrats.

### Fichiers potentiellement concernés

- `docs/operations/orchestration-makefile-v2.md`
- `makefile2.mk`
- `src/airflow_dags/dags/pull_train.py`
- `src/airflow_dags/tests/test_pull_train.py`
- `src/airflow_dags/docker-compose.yaml`
- `docs/operations/README.md`

### Validation prévue

- Vérifier chaque cible Makefile et chaque transition du DAG avec le code et les tests existants.
- Vérifier que les noms de services, endpoints et variables correspondent à `docker-compose.apis.yml`.
- Vérifier les liens internes du wiki et relire le parcours complet depuis `README.md`.

### Message de commit proposé

`docs(operations): document v2 observability and orchestration`

## Critères de fin

- `docs/operations/README.md` est le point d'entrée fonctionnel et tous ses liens sont valides.
- Chaque API v2 possède une fiche séparée avec logique métier, erreurs et procédure de validation.
- `initial-train` possède une fiche dédiée et son rôle de bootstrap est relié à `makefile2.mk init`.
- MLflow, Prometheus, métriques, Grafana, Loki et Alloy sont documentés avec leurs flux et diagnostics.
- Les variantes v1 ne sont pas présentées comme faisant partie du parcours opérationnel.
- Le DAG `pull_train` et l'orchestration Makefile v2 sont documentés en dernier et renvoient vers les fiches validées.
- Aucun secret, comportement inventé ou changement de code applicatif n'est introduit.
- Chaque étape est relue, validée et documentée dans `changes.md` avec un message de commit en anglais cohérent.
