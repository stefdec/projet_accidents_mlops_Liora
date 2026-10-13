# Workflows Airflow

Airflow 3 utilise Celery, Redis et PostgreSQL, avec api-server, scheduler, dag-processor, worker et triggerer. Les fonctions métier communes sont dans [accidents_workflow.py](../../src/airflow_dags/dags/accidents_workflow.py).

| DAG | Horaire | Sélection de semaine |
| --- | --- | --- |
| pull_train | Lundi 03:00 UTC | Semaine ISO de logical_date moins 36 |
| pull_weekly | Toutes les 5 minutes | Variable last_processed_week + 1, jusqu’à 12 |

Les deux usages sont des simulations sur données 2024. Ils ne sont pas interchangeables. La formule calendrier doit donner une semaine valide 1–52. La simulation accélérée exige last_processed_week initialisée à 0 ; elle la met à jour avant le lot, et se pause après les 12 semaines. Une relance peut donc nécessiter de vérifier le compteur ; ne pas le modifier durant un run actif.

## Séquence

1. Calcul de semaine.
2. JWT pull et collecte du Parquet.
3. DVC add --no-relink puis push du pointeur, sur le stockage configuré.
4. Commit/push Git du seul pointeur .dvc si changé (ou push du commit existant lors d’un retry).
5. JWT train et appel weekly de train-api ; clé d’idempotence liée au run et à la semaine.
6. Branche new_model : publication du run exact dans BentoML et reload avec jeton train, ou skip.
7. Synthèse après la branche réussie.

Les tâches ont leurs retries ; le pool train_api_training (un slot) sérialise le training. `catchup=False`, `max_active_runs=1`. Le pool ne remplace pas le verrou/idempotence de l’API.

## Prérequis et activation

Démarrer par `make stack-up`, contrôler les DAGs dans http://localhost:8080. Configurer utilisateurs/secrets de service, accès DagsHub, remote DVC, remote Git/branche authentifiés, permissions et compteur de simulation avant activation.

Le worker monte les DAGs, data/incoming, .git et configs DVC ; son cache DVC est un volume dédié. Aligner LOCAL_UID sur le propriétaire des bind mounts Git pour éviter les erreurs d’écriture ; renseigner les secrets localement.

Pour initialiser le compteur sur une stack active (adapter AIRFLOW_UID à celui du Makefile utilisé) :

```bash
ENV_FILE_PATH="$PWD/.env" AIRFLOW_UID=1000 docker compose --env-file .env \
  -f src/airflow_dags/docker-compose.yaml exec -T airflow-scheduler \
  airflow variables set last_processed_week 0
```

Les DAGs peuvent créer/pousser des commits et des données distantes. Pour une validation sans commits, les laisser pausés et utiliser une copie isolée avec un harnais qui neutralise uniquement la publication Git et un remote DVC local. Ce harnais ne valide pas le push Git/DagsHub de production.

Contrôles : absence d’import-errors, stabilité des workers, artefacts du run MLflow, décision champion, tag/pointeur BentoML, réponse remote_api de l’interface et métriques de monitoring. Aucun reset nécessaire pour rejouer une clé idempotente après interruption.
