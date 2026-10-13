# MLflow et PostgreSQL

Le Compose de ce dossier est piloté par `make init` ou `make stack-up`. [Guide MLflow](../../../docs/operations/mlflow.md) ; [données DVC](../../../docs/ml/dvc.md).

Persistance : data/mlflow/postgres et data/mlflow/artifacts, bind mounts hôte. Le serveur écoute en interne sur 5001 ; MLFLOW_PORT configure le port publié. stack-down conserve ces dossiers ; reset les efface. Le PostgreSQL existant conserve son mot de passe initial même si .env est ensuite modifié.
