# Bootstrap initial-train

Le code [src/inital_train/main.py](../../src/inital_train/main.py) s’exécute dans un conteneur one-shot du profil manual. Le nom existant du dossier est conservé. Le Makefile construit l’image puis lance `run --rm --no-deps`.

```bash
make init
# Ou, sur une stack déjà disponible :
make initial-train
```

Parcours : jeton train → POST train-api/train en mode initial → candidat MLflow → publication du premier champion, ou synchronisation du champion déjà existant → pointeur BentoML atomique → jeton train pour POST predict-api/reload.

Le bootstrap ne remplace pas automatiquement un champion existant par un candidat initial. La clé `INITIAL_IDEMPOTENCY_KEY` (défaut initial-bootstrap) permet de retrouver le résultat enregistré et de rejouer publication/reload sans réentraîner. Les mêmes entrées doivent être utilisées pour une même clé.

Variables : TRAIN_USERNAME/TRAIN_PASSWORD, INITIAL_IDEMPOTENCY_KEY ; URLs internes auth/train/predict ; MLFLOW_TRACKING_URI, nom enregistré/alias champion, BENTO_MODEL_NAME, CURRENT_MODEL_FILE. Les défauts se trouvent dans Compose et load_settings.

Les services doivent être actifs et un dataset doit être disponible. `make init` entraîne avant de démarrer Airflow pour limiter la concurrence mémoire. Docker 16 Go a été validé sur le poste testé. Le store partagé est conservé après suppression du conteneur ; son entrypoint prépare les droits puis exécute le publisher non-root. Airflow bentoml-init prépare aussi les droits avant son worker.

Codes de sortie : 2 configuration, 3 réseau/API, 4 réponse training invalide, 5 publication BentoML, 6 reload. Un échec ne constitue pas une initialisation réussie. Inspecter les logs expurgés et rejouer après correction, sans reset automatique.
