# Exploitation de la stack

Le [README principal](../../README.md) décrit l’architecture et les prérequis.

| Procédure | Guide |
| --- | --- |
| Démarrer, initialiser, arrêter | [Makefile](orchestration.md) |
| JWT et utilisateurs | [auth-api](auth-api.md) |
| Collecte Parquet | [pull-data-api](pull-data-api.md) |
| Entraînement et promotion | [train-api](train-api.md) |
| Bootstrap | [initial-train](initial-training.md) |
| Prédiction et reload | [predict-api](predict-api.md) |
| Tracking et Registry | [MLflow](mlflow.md) |
| Métriques | [Prometheus](metrics-prometheus.md) |
| Logs Docker | [Alloy/Loki](logs-loki-alloy.md) |
| Dashboards | [Grafana](grafana.md) |
| Tests et limites | [Validation locale](local-validation.md) |

Les contrats sont maintenus dans les schémas Python et vérifiés par les tests. Utiliser `make help` pour les commandes disponibles ; arrêter avec `make stack-down`, sans reset.
