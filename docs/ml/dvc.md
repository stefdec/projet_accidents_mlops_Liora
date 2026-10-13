# Stockage et préparation DVC

Le remote par défaut est `dagshub`, décrit dans `.dvc/config`. Les credentials restent dans `.dvc/config.local`, ignoré par Git. Le remote `local_storage` peut aussi exister pour un usage local ; ne pas modifier ses données lors d’un nettoyage de code.

Configurer les identifiants S3 DagsHub localement, sans les placer dans le fichier public. Dans Bash :

```bash
read -rsp "Jeton DagsHub DVC : " DAGSHUB_DVC_TOKEN; echo
uv run --frozen dvc remote modify --local dagshub access_key_id "$DAGSHUB_DVC_TOKEN"
uv run --frozen dvc remote modify --local dagshub secret_access_key "$DAGSHUB_DVC_TOKEN"
unset DAGSHUB_DVC_TOKEN
```

```bash
make dvc-pull
make reproduce
make metrics
# Publier uniquement lorsque les changements de données sont intentionnels :
make dvc-push
```

`dvc.yaml` décrit clean → prepare → features → snapshot. `params.yaml` configure le snapshot ; la configuration du modèle actif est `src/train_api/training_config.yaml`. Les poids et expériences du modèle actif sont dans MLflow/BentoML, pas dans une ancienne sortie de training DVC.

Le worker Airflow partage `data/incoming`, monte `.dvc/config` et `.dvc/config.local`, utilise son cache dédié, puis versionne et pousse le lot collecté. Son étape suivante crée et pousse un commit du pointeur : voir [Airflow](../airflow/process.md). Ne pas activer ce chemin pendant une validation sans commits.

`data/mlflow` et `data/backups` sont exclus par `.dvcignore` ; ils doivent être sauvegardés séparément. Les [états MLflow](../operations/mlflow.md) ne sont pas synchronisés par `dvc pull`.
