# API d’entraînement

Service `train-api`, hôte 8010/interne 8000 ; code [src/train_api](../../src/train_api/main.py). `/health` vérifie le processus HTTP ; `/docs` décrit le contrat. POST `/train` exige un JWT signé avec `JWT_SECRET_TRAIN`, `token_type=train`, rôle train.

## Requêtes et idempotence

```json
{"mode":"initial","idempotency_key":"initial-bootstrap"}
```

```json
{"mode":"weekly","week":1,"file_path":"/shared-data/accidents_2024_w01.parquet","idempotency_key":"<clé-unique>"}
```

Initial refuse week/file_path. Weekly exige une semaine 1–52 ; le lot doit correspondre à la semaine et au nom attendu. Les champs supplémentaires sont refusés. Une clé réussie retrouve le résultat enregistré ; en cours ou réutilisée avec une empreinte différente : 409. Les réservations héritées d’un arrêt sont marquées failed et peuvent être rejouées.

La réponse success contient mode/week, new_model, model_metrics/champion_metrics, mlflow_run_id, model_uri, candidate_version/champion_version, promotion_reason, dataset_digest et idempotency_key. [schemas.py](../../src/train_api/schemas.py) est la référence complète.

## Training et promotion

Le modèle utilise le feature engineering appris sur le passé, une séparation temporelle, LightGBM et un seuil explicite. Les paramètres du modèle sont dans [training_config.yaml](../../src/train_api/training_config.yaml). Les fenêtres temporelles et adaptateurs sont configurés dans [config.py](../../src/train_api/config.py).

Le training ne lance pas de CLI DVC ni de sous-processus métier. Il lit le CSV de base et les lots entrants, calcule une empreinte, entraîne/évalue, enregistre candidat et artefacts dans MLflow, puis publie les résultats drift/ML/carbone pour les exporters. Le mode initial promeut le premier modèle seulement ; le mode weekly compare le candidat au champion selon la métrique/seuil configurés.

La publication BentoML et le reload sont réalisés par initial-train ou Airflow. Avec new_model=false, le DAG conserve le champion et saute cette publication.

## Persistance et erreurs

- Input : `/var/lib/train-api/input` et `/var/lib/train-api/incoming`, lecture seule.
- Artefacts : bind `data/train-api-v2/artifacts` ; état SQLite : volume `train_api_v2_state`.
- Exports : `monitoring/drift/drift_results.json`, `monitoring/ml/model_performance.json`, `reports/carbon/emissions.csv`.
- Erreurs : 401/403 auth, 404 dataset absent, 422 schéma/dataset invalide, 409 conflit, 503 MLflow indisponible, 500 échec interne. Les détails sensibles restent côté serveur expurgé.

Validation : tests/train_api sous Linux pour OpenMP/LightGBM ; `make init` pour le flux réel. Voir [validation locale](local-validation.md).
