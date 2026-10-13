# Données et modèles

- [Préparation DVC](../../README_PIPELINE.md)
- [Configuration du stockage DVC](dvc.md)
- [Training, évaluation et promotion](../operations/train-api.md)
- [MLflow : tracking, Registry et persistance](../operations/mlflow.md)
- [Bootstrap BentoML](../operations/initial-training.md)

DVC versionne les données. Le training actif appelle directement Python et MLflow ; la publication du champion dans BentoML est réalisée par le bootstrap ou le worker Airflow.
