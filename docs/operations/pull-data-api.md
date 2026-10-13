# `pull-data-api` — collecte hebdomadaire

## Responsabilité métier

`pull-data-api` télécharge le dataset de référence depuis DagsHub, extrait les
accidents d'une semaine de 2024 et écrit le lot au format Parquet dans le
répertoire partagé avec `train-api`.

Le DAG Airflow `pull_weekly` consomme la réponse de cette API pour poursuivre le
versionnement et l'entraînement.

## Prérequis

| Élément | Valeur / rôle |
| --- | --- |
| `DAGSHUB_USERNAME` | Identifiant de téléchargement du dataset. |
| `DAGSHUB_TOKEN` | Jeton DagsHub de téléchargement. |
| `DAGSHUB_DATASET_URL` | URL optionnelle du CSV ; une URL DagsHub est utilisée par défaut. |
| `JWT_SECRET_PULL` | Secret utilisé pour vérifier le JWT pull. |
| `JWT_ALGORITHM` | Algorithme JWT, fourni par la configuration de la stack. |
| `SHARED_DATA_DIRECTORY` | Répertoire de sortie ; `/shared-data` dans Docker. |

Dans `docker-compose.apis.yml`, le répertoire `/shared-data` est partagé avec
`train-api` via `./data/incoming`. Le dataset distant est chargé au démarrage
du service ; une absence d'identifiants, une erreur HTTP ou un CSV illisible
empêche donc le démarrage normal de l'API.

## Règles métier

- La période supportée est l'année 2024, découpée en semaines numérotées de 1
  à 52.
- Une semaine est définie par une fenêtre semi-ouverte `[début, fin[`. La date
  de début est incluse et la borne finale est exclue.
- La semaine 1 couvre du `2024-01-01` au `2024-01-07` inclus ; sa borne finale
  exclusive est `2024-01-08`.
- Le filtre utilise `accident_date` normalisée au jour.
- Le dataset doit contenir les colonnes `Num_Acc` et `accident_date`.
- Toute date invalide est rejetée.
- Une semaine sans ligne est rejetée.
- Un même `Num_Acc` ne peut pas apparaître avec plusieurs dates dans le lot
  extrait.
- Le résultat est trié par `accident_date`, puis `Num_Acc`, avec un ordre stable.
- Le fichier est nommé `accidents_2024_wNN.parquet`, où `NN` est la semaine sur
  deux chiffres, par exemple `accidents_2024_w05.parquet`.
- Le fichier est écrit sans index pandas.
- Une nouvelle collecte de la même semaine réécrit le même chemin : le nom de
  fichier est déterministe.

## Endpoints

### `GET /health`

Endpoint public de disponibilité.

```json
{"status": "ok"}
```

### `GET /pull_data?week=N`

L'endpoint exige un en-tête `Authorization` au format Bearer :

```text
Authorization: Bearer <jwt-pull>
```

Réponse nominale :

```json
{
  "week": 5,
  "start_date": "2024-01-29",
  "end_date_exclusive": "2024-02-05",
  "file_path": "/shared-data/accidents_2024_w05.parquet",
  "record_count": 123
}
```

| Situation | Statut attendu / observé | Conséquence |
| --- | ---: | --- |
| Requête avec JWT vérifiable et semaine disponible | `200` | Parquet écrit et contrat retourné. |
| En-tête absent ou schéma différent de `Bearer` | `403` | Requête refusée par `HTTPBearer`. |
| JWT invalide ou expiré | `403` | Requête refusée. |
| `week` absent, non entier ou hors de 1 à 52 | `422` | Validation de la query FastAPI échouée. |
| Dataset sans colonne requise, date invalide ou semaine vide | `500` observé | Erreur métier levée sans mapping HTTP dédié. |

### Vérification du JWT

Le middleware vérifie la signature, l'algorithme configuré et les contrôles
standards de validité du JWT, dont l'expiration lorsqu'elle est présente. Il ne
vérifie pas explicitement les claims `token_type`, `role` ou `username` dans
`pull-data-api` : l'autorisation d'obtenir un jeton pull relève de
`auth-api`. Ce comportement doit rester visible pendant la validation de la
logique de sécurité.

## Contrat de sortie et stockage

| Champ | Type | Signification |
| --- | --- | --- |
| `week` | entier | Numéro de semaine demandé. |
| `start_date` | chaîne ISO | Début inclusif de la fenêtre. |
| `end_date_exclusive` | chaîne ISO | Fin exclusive de la fenêtre. |
| `file_path` | chaîne | Chemin du Parquet écrit par le service. |
| `record_count` | entier | Nombre de lignes extraites. |

Le chemin retourné correspond au chemin vu par le conteneur de collecte. Le DAG
valide ensuite le nom de fichier et résout le chemin équivalent dans son propre
montage `data/incoming` avant de lancer DVC et le training.

## Procédure de validation

Avec la stack active démarrée et un JWT pull obtenu auprès de `auth-api` :

```bash
curl -sS http://localhost:8006/health
curl -sS -G http://localhost:8006/pull_data \
  -H 'Authorization: Bearer <jwt-pull>' \
  --data-urlencode 'week=1'
```

Valider les scénarios suivants :

1. `/health` retourne `200` et `{"status":"ok"}`.
2. La semaine 1 retourne les bornes `2024-01-01` et `2024-01-08`.
3. La semaine 5 ne contient pas la date `2024-01-28` et contient la date
   `2024-01-29`, afin de vérifier le passage de mois.
4. Le fichier `accidents_2024_w01.parquet` est créé dans `data/incoming` et
   contient le nombre de lignes annoncé.
5. Les semaines 0 et 53 sont rejetées avec `422`.
6. Un appel sans JWT, avec un JWT invalide ou avec un schéma non Bearer est
   rejeté avec `403`.
7. Un dataset sans colonne obligatoire, avec date invalide ou sans donnée pour
   la semaine demandée est refusé.
8. Une seconde collecte de la même semaine réutilise le même nom de fichier.

Les tests de référence sont dans
[`tests/test_pull_data_api.py`](../../tests/test_pull_data_api.py). Le contrat
de collecte est ensuite consommé par le
[DAG `pull_weekly`](orchestration.md).

## Diagnostic

- Vérifier `DAGSHUB_USERNAME`, `DAGSHUB_TOKEN` et l'URL du dataset si le service
  ne démarre pas.
- Vérifier que le volume `./data/incoming:/shared-data` existe et est accessible
  en écriture.
- Vérifier que le fichier produit est visible par `train-api` au même moment.
- Contrôler `record_count`, les bornes de dates et le nom du fichier avant de
  poursuivre le training.
- Ne jamais afficher les identifiants DagsHub ni les JWT dans les logs ou les
  tickets d'incident.

Retour à l'[index du wiki opérationnel](README.md).
