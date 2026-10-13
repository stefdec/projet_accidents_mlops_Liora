# Orchestration Make

Le [Makefile](../../Makefile) est l’unique point d’entrée. Toutes les commandes s’exécutent depuis la racine.

| Commande | Effet |
| --- | --- |
| `make install` | Crée .env s’il manque, uv sync verrouillé avec monitoring |
| `make init` | MLflow → monitoring → API/interface → bootstrap → Airflow |
| `make stack-up` | Même stack, sans bootstrap |
| `make initial-train` | Construit/exécute le bootstrap one-shot sur services actifs |
| `make presentation` | Serveur Streamlit au premier plan, 127.0.0.1:8501 |
| `make predict-smoke` | Authentification et prédiction réelle de payload.json |
| `make stack-status` | État des quatre groupes Compose, jobs terminés inclus |
| `make stack-logs` | 100 lignes récentes par service |
| `make stack-down` | Arrêt Airflow → API → MLflow → monitoring, données conservées |
| `make monitoring-up/down` | Exploitation du monitoring |
| `make airflow-up` | Build Airflow unique puis démarrage de ses services |
| `make dvc-pull/push`, `make reproduce`, `make metrics` | Données DVC |
| `make reset` | Efface MLflow/train/BentoML et base Airflow ; datasets/monitoring conservés |
| `make reset-full` | Efface aussi images locales et volumes monitoring |

`emergency-interface` est inclus dans les API. Le monitoring ne démarre qu’une fois. Les resets sont destructifs et ne servent pas à vérifier le démarrage.

Variables Make : `ENV_FILE` (défaut .env), `LOCAL_UID/LOCAL_GID` (1000:1000), `TRAIN_USERNAME/TRAIN_PASSWORD` (compte démo), `INITIAL_IDEMPOTENCY_KEY` (initial-bootstrap), `PRESENTATION_PORT` (8501). Pour un autre propriétaire de bind mounts : passer explicitement les UID/GID au Makefile ; ne pas utiliser sudo Make.

`runtime-dirs` conserve la préparation actuelle des répertoires et droits ; `network` crée le réseau externe s’il manque. Aucune suppression de volume n’est faite par stack-down.

Les chemins `data/train-api-v2` et volume `train_api_v2_state` sont volontairement conservés pour l’état existant. Les autres noms actifs n’ont plus de suffixe de version. Retour au [README](../../README.md).
