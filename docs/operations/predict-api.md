# API de prédiction

Service `predict-api`, hôte 8009/interne 8000 ; [code](../../src/predict_api/service.py). BentoML charge le modèle sélectionné dans `/bentoml/current_model.txt`, sur le volume partagé `bentoml_store` ; fallback de tag accidents:latest si le pointeur manque.

| Route | Contrat |
| --- | --- |
| GET `/health` | Processus HTTP disponible |
| POST `/predict` | Bearer signé avec le secret login ; JSON enveloppé dans input_data |
| POST `/reload` | Bearer signé avec le secret train ; recharge le worker modèle |
| GET `/metrics` | Métriques Prometheus |

`JWT_SECRET_KEY` correspond à `JWT_SECRET_LOGIN` de auth-api. Reload utilise `JWT_SECRET_TRAIN`, donc un jeton login signé avec l’autre secret est refusé. Le middleware valide signature et expiration ; les jetons appropriés sont émis par auth-api selon les rôles autorisés.

La requête de référence est [payload.json](../../payload.json). Les champs numériques BAAC sont convertis selon les catégories du modèle ; une valeur non convertible est rejetée. La réponse contient prediction, probability et model_version. Une probabilité indisponible peut être nulle selon le modèle ; le smoke du champion actif exige une valeur exploitable.

`make predict-smoke` vérifie une prédiction authentifiée sans afficher le JWT. `/health` ne garantit pas qu’un modèle soit chargé. `/reload` retourne status/model_version après succès, 503 si le modèle est indisponible. Signature absente/invalide/expirée : 401 ; payload invalide : erreur de validation ou 400 selon la conversion.

L’interface proxy `/api/predict` ajoute l’enveloppe si nécessaire. `status=remote_api` confirme le modèle distant. Une exception réseau peut déclencher un secours heuristique : ce secours ne prouve pas que BentoML fonctionne.

Les anciens modèles embarquent leur code MLflow ; le champion existant a été testé après renommage des modules. Les nouveaux modèles embarquent les modules src.train_api. Voir [bootstrap](initial-training.md).
