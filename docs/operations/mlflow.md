# MLflow — tracking, Registry et modèle champion

## Responsabilité opérationnelle

MLflow conserve les runs d'entraînement, leurs paramètres, métriques, artefacts
et modèles. Son Model Registry conserve les versions candidates et l'alias
`champion` utilisé pour sélectionner le modèle de référence.

MLflow ne remplace pas DVC : DVC versionne les datasets et snapshots, tandis que
MLflow suit les entraînements et décide quelle version du modèle est servie.

## Architecture

| Composant | Rôle | Persistance / accès |
| --- | --- | --- |
| `mlflow-server` | Serveur Tracking et Registry | `http://localhost:5001` depuis l'hôte ; `http://mlflow-server:5001` dans le réseau Compose. |
| `mlflow-db` | PostgreSQL du backend MLflow | `data/mlflow/postgres`. |
| Stockage artefacts | Modèles, rapports et fichiers de run | `data/mlflow/artifacts`, monté en `/mlartifacts`. |
| Réseau | Communication avec les API actives et Airflow | `accidents-shared-network`. |

Le serveur dépend de `mlflow-db` healthy avant de démarrer. Le healthcheck du
serveur appelle `/health` sur le port 5001.

## Configuration de référence

| Variable | Valeur par défaut / rôle |
| --- | --- |
| `MLFLOW_TRACKING_URI` | `http://mlflow-server:5001` pour les conteneurs clients. |
| `MLFLOW_EXPERIMENT_NAME` | `accidents-gravity`. |
| `MLFLOW_REGISTERED_MODEL_NAME` | `accidents-gravity-classifier`. |
| `MLFLOW_CHAMPION_ALIAS` | `champion`. |
| `MLFLOW_PORT` | `5001` côté hôte. |
| `MLFLOW_DB_NAME` | `mlflow`. |
| `MLFLOW_DB_USER` | `mlflow`. |
| `MLFLOW_DB_PASSWORD` | Secret local à conserver dans `.env`. |
| `MLFLOW_ALLOWED_HOSTS` | Hôtes autorisés par le serveur MLflow. |

Les API actives, `initial-train` et le DAG Airflow utilisent la même URI interne
afin de partager le Tracking et le Registry. Une URI différente créerait un
cycle de vie de modèle séparé et invaliderait le parcours opérationnel.

## Cycle de vie d'un entraînement

### 1. Tracking du run

`train-api` :

1. sélectionne l'expérience configurée ;
2. ouvre un run nommé `train-api-initial` ou
   `train-api-weekly-wNN` ;
3. journalise les paramètres, les métriques, le seuil de classification, le
   digest dataset, la configuration et la lineage du code ;
4. journalise le snapshot manifest, la signature du modèle, l'exemple d'entrée
   et les artefacts locaux ;
5. enregistre le modèle sous l'URI `runs:/<run_id>/model`.

Les métriques de performance et, en mode weekly, les informations du champion
et du drift sont associées au run candidat.

### 2. Enregistrement du candidat

Le modèle est enregistré sous le nom
`accidents-gravity-classifier`. Une nouvelle version est créée et reçoit le tag
Registry `role=candidate`. Cette opération ne déplace pas l'alias `champion`.

### 3. Résolution et promotion du champion

- L'absence de champion permet de promouvoir le premier candidat.
- Le mode initial ne remplace pas un champion existant.
- Le mode weekly compare le `pr_auc` du candidat et celui du champion évalué
  sur la même fenêtre.
- La promotion exige un gain strictement supérieur à
  `PROMOTION_MIN_IMPROVEMENT`.
- Lors d'une promotion, le candidat reçoit `role=champion`, l'ancien champion
  reçoit `role=archived` et l'alias `champion` pointe vers la nouvelle version.

L'alias est la référence fonctionnelle ; les clients doivent résoudre l'alias
ou la version exacte plutôt que supposer qu'une version numérique est toujours
la plus récente ou la meilleure.

### 4. Publication vers l'inférence

`initial-train` importe dans BentoML le run exact retourné par `train-api`, ou
la version exacte résolue depuis l'alias `champion` si le candidat initial n'est
pas promu. Il écrit ensuite le tag BentoML dans le pointeur partagé et demande
le reload de l'API de prédiction.

L'API de prédiction ne charge donc pas directement l'alias MLflow à chaque
requête : elle sert le modèle sélectionné dans BentoML.

## Artefacts et lineage

Les runs peuvent contenir :

- métriques de classification et d'évaluation ;
- paramètres du modèle et seuil de décision ;
- `snapshot_manifest.json` ;
- digest du dataset et informations du commit source ;
- signature et exemple d'entrée MLflow ;
- modèle sérialisé et artefacts de rapport ;
- rapport de drift et métriques du champion en mode weekly ;
- métrique `emissions_kg` lorsque disponible.

Le digest permet de relier un run à ses données et à sa configuration. Il ne
constitue pas à lui seul une sauvegarde : les datasets et snapshots restent
gérés par les mécanismes DVC prévus à cet effet.

## Démarrage et vérification

Démarrer MLflow avec la stack active :

```bash
make stack-up
```

Vérifier le healthcheck et l'interface :

```bash
curl -sS http://localhost:5001/health
docker compose --env-file .env \
  -f src/infra/mlflow/docker-compose.mlflow.yml ps
```

L'interface est disponible sur <http://localhost:5001>. Les APIs doivent
utiliser l'adresse interne `http://mlflow-server:5001`, pas `localhost`, depuis
les conteneurs.

## Procédure de validation

1. `mlflow-db` devient healthy avant `mlflow-server`.
2. `/health` retourne une réponse positive sur le port 5001.
3. Un entraînement initial crée un run dans l'expérience configurée.
4. Le run contient un modèle à l'URI `runs:/<run_id>/model` et les métriques
   attendues.
5. Le Registry contient une version candidate sous le nom configuré.
6. Sans champion, l'alias `champion` pointe vers le premier candidat promu.
7. Avec un champion, la décision weekly respecte le seuil de gain configuré.
8. Une promotion archive l'ancien champion et déplace l'alias vers le candidat.
9. `initial-train` et l'API de prédiction utilisent le même modèle sélectionné.
10. Un run ou un artefact MLflow indisponible produit une erreur exploitable sans
    exposer de mot de passe, token ou URL contenant des identifiants.

Les tests ciblés du service sont dans
[`tests/train_api/test_mlflow_service.py`](../../tests/train_api/test_mlflow_service.py).
Les règles de promotion sont également couvertes par les tests du domaine et
du service [train-api](train-api.md).

## Diagnostic et persistance

- `mlflow-server` unhealthy : vérifier `mlflow-db`, le port 5001, les identifiants
  PostgreSQL et les logs du serveur.
- Run absent : vérifier `MLFLOW_TRACKING_URI` et `MLFLOW_EXPERIMENT_NAME` côté
  appelant.
- Registry inaccessible : vérifier le nom `MLFLOW_REGISTERED_MODEL_NAME` et la
  connectivité au backend.
- Alias absent : aucun champion n'a encore été promu, ou l'URI cible n'est pas
  celle de la stack active.
- Artefact introuvable : vérifier le montage `data/mlflow/artifacts` et les
  permissions du conteneur.
- Ne pas supprimer `data/mlflow/postgres` ou `data/mlflow/artifacts` pour un
  simple diagnostic : ces chemins contiennent l'historique et les modèles
  persistants. Les cibles de reset du Makefile ont un effet destructif explicite.

Retour à l'[index du wiki opérationnel](README.md), à la fiche
[train-api](train-api.md) et à la fiche [initial-train](initial-training.md).
