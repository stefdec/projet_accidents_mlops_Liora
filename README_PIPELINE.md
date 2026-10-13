# Préparation des données

`make reproduce` exécute les étapes DVC : nettoyage, préparation, features et snapshot.

- `pipeline/01_clean.py` : CSV brut vers données nettoyées.
- `pipeline/02_prepare.py` : normalisation BAAC.
- `pipeline/03_features.py` : dataset binaire `data/features/data_final_binaire.csv`.
- `pipeline/04_snapshot.py` : snapshot selon `params.yaml` et lots entrants.

Le dataset binaire est lu par l’API de training active. Le training et le monitoring sont réalisés directement par cette API, puis publiés dans MLflow. La préparation exige les données brutes : `make dvc-pull` avec le remote local correctement configuré. Aucun ancien pipeline de training CLI n’est nécessaire.
