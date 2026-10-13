# Contrats API

| Service | Port hôte | Guide |
| --- | --- | --- |
| auth-api | 8005 | [JWT et rôles](../operations/auth-api.md) |
| pull-data-api | 8006 | [Collecte](../operations/pull-data-api.md) |
| train-api | 8010 | [Training](../operations/train-api.md) |
| predict-api | 8009 | [Prédiction et reload](../operations/predict-api.md) |

Ports internes : 8000. Les FastAPI exposent `/docs` et `/openapi.json`. `payload.json` à la racine fournit la requête de prédiction active.
