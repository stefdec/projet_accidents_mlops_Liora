# Plan d'implémentation

## Objectif

Nettoyer le dépôt pour ne conserver que le parcours opérationnel piloté par `makefile2.mk`, l'interface web `interface`, la présentation `app/pres-sl`, leurs dépendances, leurs tests utiles et leur documentation active.

## Contexte

Le parcours actif démarre MLflow, le monitoring, `auth-api`, `pull-data-api`, `train-api-v2`, `predict-api-v2`, l'entraînement initial et Airflow. L'interface `interface` fait partie du projet, mais `makefile2.mk` ne construit et ne démarre pas encore le service `emergency-interface` pourtant déclaré dans `docker-compose.apis.yml`.

Deux points empêchent une suppression immédiate et sûre :

- `train-api-v2` exige `data/features/data_final_binaire.csv`, tandis que sa seule chaîne de génération versionnée est encore l'ancien pipeline `dvc.yaml` + `pipeline/` ;
- Airflow charge simultanément `pull_train.py` et `pull_weekly.py`, deux DAGs presque identiques avec des calendriers différents. Le DAG actif doit être choisi explicitement avant d'en retirer un.

### Périmètre actif à conserver

- Orchestration : `makefile2.mk`, `docker-compose.apis.yml`, `docker-compose.monitoring.yml`, `src/infra/mlflow/` et `src/airflow_dags/` après dédoublonnage du DAG.
- Services : `src/auth_api/`, `src/pull_data_api/`, `src/train_api_v2/`, `src/predict_api_v2/` et `src/inital_train/`.
- Interface : `interface/` et son service `emergency-interface`.
- Présentation : `app-pres.py` et `app/pres-sl/`.
- Observabilité active : exporters, configurations Prometheus, Grafana, Loki et Alloy, ainsi que `reports/carbon/`.
- Persistance et données actives : `.dvc/`, `.dvcignore`, `data/features/`, `data/incoming/`, `data/mlflow/` et `data/train-api-v2/`.
- Dépendances et outillage nécessaires au build courant : `Dockerfile`, `.dockerignore`, `.env.example`, `pyproject.toml`, `uv.lock`, `.python-version` et les fichiers Git usuels.
- Tests ciblant directement les composants actifs et `app/pres-sl/tests/`.
- Documentation opérationnelle sous `docs/operations/`, documentation de l'interface, README de `pres-sl` et historique `docs/changes/`.

### Inventaire initial des éléments inutilisés

#### Applications et présentations remplacées

- `app/presentation/` et `app_presentation.py`.
- `app/soutenance/` et `app_soutenance.py`.
- `app/sl_OCS_v1/` et `app_sl_OCS_v1.py`.
- `app/sl_app/` et `app_sl_app.py`.
- `app/sl_legacy/` et `app_sl_legacy.py`.
- `app/pres-sl/assets/images/daghub.png`, non référencée par la présentation active.
- `scripts/sl_OCS_v1_smoke_test.py`.

#### Ancienne chaîne ML remplacée par les services v2

- `src/train_api/`.
- `src/predict_api/`.
- `pipeline/`.
- `dvc.yaml`, `dvc.lock` et `params.yaml`, après sécurisation du dataset de base.
- `data/raw/accidents_2017_2024.csv.dvc`, `data/raw/.gitignore` et `data/processed/.gitignore`.
- `models/.gitignore` et `models/final/.gitignore`.
- `reports/snapshot_manifest.json` et `reports/.gitignore` si aucun rapport actif n'utilise encore `reports/figures/`.
- `README_PIPELINE.md`.
- Le `requirements.txt` racine, qui ne contient aucune dépendance et n'est utilisé par aucun build actif.

#### Scripts de monitoring hérités

Ces scripts appartiennent à l'ancienne `train_api`; `train-api-v2` calcule et exporte directement les mêmes résultats :

- `monitoring/drift/prepare_drift_data.py`.
- `monitoring/drift/run_drift.py`.
- `monitoring/drift/run_monitoring.py`.
- `monitoring/ml/run_model_performance.py`.

Les exporters `monitoring/exporters/` et les fichiers JSON générés au runtime restent actifs.

#### Tests devenus obsolètes avec la chaîne v1

- `tests/conftest.py` dans sa forme actuelle, car il force le backend historique DVC.
- `tests/test_features.py`.
- `tests/test_inference.py`.
- `tests/test_mlflow_admin.py`.
- `tests/test_modeling.py`.
- `tests/test_predict_service.py`.
- `tests/test_registry.py`.
- `tests/test_retraining.py`.
- `tests/test_temporal.py`.
- `tests/test_tracking.py`.
- `tests/test_train_api.py`.
- `tests/test_training_cli.py`.
- `tests/test_training_contract.py`.
- `tests/test_weekly_data.py`.
- Les parties de `tests/test_docker_architecture.py` qui vérifient `Makefile`, `train-api`, `predict-api` ou `sl_OCS_v1`.
- `tests/test_predict_api_smoke.py` tant que le smoke test associé cible encore le port `8008` et `src/predict_api/sample.json`.

Les tests `tests/train_api_v2/`, `tests/test_auth_api.py`, `tests/test_pull_data_api.py`, `tests/test_initial_train_trigger.py`, `tests/test_predict_api_v2_service.py`, `src/airflow_dags/tests/` et `app/pres-sl/tests/` restent dans le périmètre actif.

#### Fichiers racine et utilitaires hors parcours actif

- `Makefile`, remplacé par `makefile2.mk`.
- `create_github_issues_generales.sh` et `roadmap_MLOps_accidents_generale_github.csv`.
- `scripts/migrate_legacy_backups.sh`, après confirmation que la migration historique est terminée.
- `scripts/migrate_mlflow_storage.sh`, après confirmation que le stockage MLflow a déjà été migré.
- `scripts/predict_api_smoke_test.py` dans son état actuel : il doit être adapté à `predict-api-v2` et au port `8009`, ou supprimé.
- `docker-compose.apis.yml` contient le volume nommé `shared-api-data`, qui n'est monté par aucun service.

#### Documentation obsolète ou redondante

- `docs/airflow/process.md` et `docs/airflow/process_draft1.md`, qui décrivent l'ancien parcours.
- `docs/api/train-api.md` et les entrées v1 de `docs/api/README.md`.
- `docs/applications/guide-demo-sl-ocs-v1.md` et les liens vers les applications Streamlit retirées dans `docs/applications/README.md`.
- `docs/ml/`, centré sur `src/train_api`, `src/predict_api`, `pipeline/`, `dvc.yaml` et `params.yaml`.
- `docs/refactor/`, qui documente les migrations déjà terminées.
- `docs/audit-yann.md`, rapport ponctuel qui n'est pas une procédure d'exploitation.
- `docs/loki/README.md`, à fusionner avec `docs/operations/logs-loki-alloy.md` avant retrait.
- Les sections obsolètes de `README.md`, `README_monitoring.md` et `docs/README.md`.
- `PRODUCT.md`, à réécrire pour `app/pres-sl` et `interface` car il désigne encore `app/presentation` et `app/soutenance` comme références.
- `interface/rapport.md` si son contenu n'apporte rien au guide actif de l'interface.

### Éléments à examiner avant suppression

- `pull_train.py` et `pull_weekly.py` : un seul doit rester, mais le choix du calendrier actif doit être confirmé par le comportement attendu.
- La chaîne `dvc.yaml` + `pipeline/` : inactive au runtime, mais encore nécessaire pour reconstruire `data/features/data_final_binaire.csv` depuis un clone neuf. Le nettoyage doit fournir un remplacement reproductible avant son retrait.
- `.agents/`, `.codex/`, `.github/skills`, `.github/agents`, `.github/hooks` et `.impeccable/` : hors runtime produit, mais utilisés comme outillage de conception et d'agent. Ils ne seront pas supprimés avec le code applicatif sans décision dédiée.
- `scripts/mlflow_smoke_test.py` : non appelé par `makefile2.mk`, mais encore compatible avec le serveur MLflow actif et utile comme diagnostic opérateur.
- Les historiques `docs/changes/` : non exécutés, mais conservés comme trace des changements selon les règles du dépôt.
- Les fichiers ignorés contenant des données ou de l'état (`.env`, `.dvc/config.local`, caches DVC, datasets, volumes MLflow, état train-api-v2, résultats de monitoring) : ils ne doivent pas être confondus avec des fichiers morts.

### Artéfacts locaux nettoyables sans modifier le produit

- `.DS_Store`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` et les caches Python imbriqués.
- `interface/node_modules/`, reconstructible avec le lockfile npm.
- Les caches des anciennes applications après leur suppression.
- `_ARCHIVE/` doit faire l'objet d'un inventaire séparé avant suppression, car il peut contenir des sauvegardes utilisateur non suivies par Git.

## Périmètre

### Inclus

- Définition et documentation de la frontière active du dépôt.
- Raccordement de `interface` au workflow principal.
- Suppression des applications, APIs, pipelines, tests, scripts et documents remplacés.
- Conservation d'un bootstrap reproductible du dataset historique.
- Dédoublonnage du DAG Airflow.
- Mise à jour des tests, README, exemples et règles d'exclusion.
- Nettoyage des artéfacts locaux régénérables après revue explicite des chemins.

### Hors périmètre

- Modification des contrats métier des API v2.
- Changement du modèle, des règles de promotion ou des métriques.
- Suppression de datasets, secrets locaux, caches DVC utiles ou états persistants Docker.
- Réécriture de l'interface ou de la présentation.
- Suppression automatique de l'outillage d'agent et de conception.

## Étape 1 — Rendre le périmètre actif autonome

### Objectif

Éliminer les ambiguïtés qui empêchent de distinguer une dépendance active d'un vestige.

### Modifications prévues

- Ajouter `emergency-interface` aux builds et démarrages de `stack-up` et `init`.
- Retirer le volume Compose `shared-api-data` non monté.
- Choisir le DAG Airflow actif, migrer les éventuelles différences utiles, puis ne charger qu'un seul DAG.
- Définir une source reproductible pour `data/features/data_final_binaire.csv` sans dépendre de toute la chaîne ML historique, par exemple un pointeur DVC dédié ou une étape explicite de bootstrap.
- Ajouter des vérifications d'architecture qui décrivent cette frontière active.

### Fichiers potentiellement concernés

- `makefile2.mk`
- `docker-compose.apis.yml`
- `src/airflow_dags/dags/pull_train.py`
- `src/airflow_dags/dags/pull_weekly.py`
- `src/airflow_dags/tests/test_pull_train.py`
- `.env.example`
- `.dvc/config`
- `data/features/`
- `tests/test_docker_architecture.py`

### Validation prévue

- `docker compose --env-file .env.example -f docker-compose.apis.yml config`
- `docker compose --env-file .env.example -f src/airflow_dags/docker-compose.yaml config`
- Tests Airflow, Compose, API v2 et interface concernés.
- Vérification qu'un clone neuf peut obtenir le dataset de base requis.

### Message de commit proposé

`chore(repo): define the active project boundary`

## Étape 2 — Retirer les applications et présentations remplacées

### Objectif

Ne conserver que `interface` et `app/pres-sl` comme surfaces utilisateur.

### Modifications prévues

- Supprimer les cinq anciennes applications Streamlit, leurs lanceurs et leurs tests.
- Supprimer le smoke test OCS v1.
- Supprimer l'image `daghub.png` non référencée dans `pres-sl`.
- Nettoyer les références directes à ces applications dans la configuration et la documentation active.

### Fichiers potentiellement concernés

- `app/presentation/`
- `app/soutenance/`
- `app/sl_OCS_v1/`
- `app/sl_app/`
- `app/sl_legacy/`
- `app_presentation.py`
- `app_soutenance.py`
- `app_sl_OCS_v1.py`
- `app_sl_app.py`
- `app_sl_legacy.py`
- `scripts/sl_OCS_v1_smoke_test.py`
- `app/pres-sl/assets/images/daghub.png`

### Validation prévue

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest app/pres-sl/tests -q -p no:cacheprovider`
- Lancement de `app-pres.py` et vérification des huit slides.
- Recherche globale des imports et chemins supprimés.

### Message de commit proposé

`chore(apps): remove replaced streamlit applications`

## Étape 3 — Retirer la chaîne ML v1 et les scripts de monitoring hérités

### Objectif

Supprimer le code d'entraînement, d'inférence et de monitoring remplacé par les services v2, une fois le dataset de base sécurisé.

### Modifications prévues

- Supprimer `src/train_api`, `src/predict_api`, `pipeline` et leurs fichiers de configuration historiques.
- Supprimer les pointeurs, placeholders et rapports utilisés uniquement par cette chaîne.
- Supprimer les quatre scripts de monitoring v1 tout en conservant les exporters et sorties runtime v2.
- Simplifier `pyproject.toml` pour retirer le backend de package pointant vers `src/train_api/utils` et les dépendances devenues inutiles.
- Régénérer `uv.lock` après réduction des dépendances.

### Fichiers potentiellement concernés

- `src/train_api/`
- `src/predict_api/`
- `pipeline/`
- `dvc.yaml`
- `dvc.lock`
- `params.yaml`
- `data/raw/`
- `data/processed/`
- `models/`
- `reports/snapshot_manifest.json`
- `monitoring/drift/*.py`
- `monitoring/ml/run_model_performance.py`
- `requirements.txt`
- `pyproject.toml`
- `uv.lock`

### Validation prévue

- `uv sync --locked`
- Tests complets des API v2, de l'entraînement initial et des exporters.
- Build des images `train-api-v2`, `predict-api-v2`, `initial-train` et des exporters.
- Recherche globale de toute référence aux chemins supprimés.

### Message de commit proposé

`chore(ml): remove the legacy training and inference stack`

## Étape 4 — Recentrer les tests et les outils opérateur

### Objectif

Conserver une suite de validation qui couvre uniquement le parcours actif et corriger les diagnostics encore utiles.

### Modifications prévues

- Supprimer les tests unitaires propres à la chaîne v1.
- Réécrire `tests/test_docker_architecture.py` autour de `makefile2.mk`, des services v2, de l'interface et de `pres-sl`.
- Retirer le comportement historique de `tests/conftest.py` s'il n'est plus requis.
- Adapter le smoke test de prédiction à `predict-api-v2`, au port `8009` et au contrat actuel, puis conserver son test.
- Retirer les scripts de migration dont l'usage est terminé ; documenter ceux qui doivent rester comme procédures ponctuelles.

### Fichiers potentiellement concernés

- `tests/`
- `scripts/predict_api_smoke_test.py`
- `scripts/migrate_legacy_backups.sh`
- `scripts/migrate_mlflow_storage.sh`
- `scripts/mlflow_smoke_test.py`
- `payload.json`
- `src/predict_api_v2/README_curl.md`

### Validation prévue

- Suite Pytest restante complète.
- Exécution du smoke test MLflow.
- Exécution du smoke test de prédiction contre la stack v2.
- Vérification qu'aucun test ne référence un composant supprimé.

### Message de commit proposé

`test(repo): align validation with the active stack`

## Étape 5 — Nettoyer les fichiers racine et la documentation

### Objectif

Présenter un seul parcours d'installation, d'exploitation et de démonstration sans liens vers les variantes supprimées.

### Modifications prévues

- Supprimer l'ancien `Makefile`, les fichiers de roadmap et le script de création d'issues.
- Supprimer ou fusionner la documentation obsolète listée dans l'inventaire.
- Réécrire `README.md`, `docs/README.md`, `docs/applications/README.md` et `PRODUCT.md` autour de `makefile2.mk`, `interface` et `pres-sl`.
- Mettre à jour `README_monitoring.md` et les fiches `docs/operations/` pour refléter le DAG et le bootstrap retenus.
- Vérifier tous les liens relatifs restants.

### Fichiers potentiellement concernés

- `Makefile`
- `README.md`
- `README_PIPELINE.md`
- `README_monitoring.md`
- `PRODUCT.md`
- `create_github_issues_generales.sh`
- `roadmap_MLOps_accidents_generale_github.csv`
- `docs/README.md`
- `docs/airflow/`
- `docs/api/`
- `docs/applications/`
- `docs/audit-yann.md`
- `docs/loki/`
- `docs/ml/`
- `docs/operations/`
- `docs/refactor/`
- `interface/rapport.md`

### Validation prévue

- Recherche globale des noms et chemins supprimés.
- Vérification automatisée ou manuelle des liens Markdown relatifs.
- Exécution des commandes documentées avec `--help`, `config` ou une validation non destructive lorsque possible.

### Message de commit proposé

`docs(repo): document the consolidated project workflow`

## Étape 6 — Nettoyer les artéfacts locaux régénérables

### Objectif

Retirer les caches et sorties locales sans toucher aux données, secrets ou états persistants nécessaires.

### Modifications prévues

- Supprimer les caches Python, Pytest, Ruff, fichiers `.DS_Store` et `interface/node_modules`.
- Examiner `_ARCHIVE/` et déplacer ou supprimer son contenu seulement après avoir identifié ce qui doit être conservé.
- Vérifier les règles `.gitignore` pour empêcher le retour des artéfacts inutiles.
- Conserver explicitement `.env`, les données DVC, les datasets actifs, MLflow, l'état de training et les sorties de monitoring.

### Fichiers potentiellement concernés

- `.gitignore`
- `interface/.gitignore`
- Artéfacts ignorés listés par `git clean -ndX`
- `_ARCHIVE/`

### Validation prévue

- `git status --short --ignored`
- Vérification que `uv sync`, `npm ci --prefix interface` et les tests recréent uniquement les caches attendus.
- Vérification que les données et états persistants sont toujours présents.

### Message de commit proposé

`chore(repo): remove regenerable local artifacts`

## Étape 7 — Valider le dépôt nettoyé de bout en bout

### Objectif

Démontrer que le dépôt réduit permet encore de construire, démarrer, tester et présenter le projet complet.

### Modifications prévues

- Corriger uniquement les dernières références cassées révélées par la validation.
- Finaliser le journal de changements avec les suppressions et conséquences opérationnelles.

### Fichiers potentiellement concernés

- `docs/changes/2026-09-21_main/changes.md`
- Fichiers actifs révélés par les validations finales.

### Validation prévue

- `docker compose config` pour les quatre configurations pilotées par `makefile2.mk`.
- Build de toutes les images actives, y compris `emergency-interface`.
- Suite Pytest restante complète.
- `npm ci --prefix interface` puis build de l'interface.
- Lancement de `app-pres.py` et vérification des huit slides.
- `make -f makefile2.mk stack-up`, contrôles de santé, smoke tests, puis arrêt propre.
- `git diff --check` et vérification finale du statut Git.

### Message de commit proposé

`chore(repo): validate the consolidated project`

## Critères de fin

- `makefile2.mk` démarre toute la stack active, interface comprise.
- Un seul DAG Airflow actif porte le workflow hebdomadaire attendu.
- Le dataset de base peut être obtenu de manière reproductible depuis un clone neuf.
- Seuls `interface` et `app/pres-sl` restent comme interfaces utilisateur.
- Les API, pipelines, scripts, tests et documents v1 ont disparu sans référence résiduelle.
- Les builds Docker, tests, smoke tests et contrôles de santé actifs passent.
- Les données et états persistants n'ont pas été supprimés pendant le nettoyage.
- La documentation décrit uniquement le parcours consolidé.
