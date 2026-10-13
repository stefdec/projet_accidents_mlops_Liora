# `auth-api` — authentification et JWT

## Responsabilité métier

`auth-api` vérifie les identifiants configurés et délivre des JWT limités à un
usage : connexion applicative (`login`), collecte (`pull`) ou entraînement
(`train`). Les API actives consomment ensuite le jeton correspondant à leur rôle.

Cette fiche documente l'API utilisée par le parcours actif. Elle ne contient aucun
secret réel ; les valeurs de `.env` doivent rester privées.

## Prérequis

Le service doit disposer des variables suivantes au démarrage :

| Variable | Rôle |
| --- | --- |
| `USERS` | Objet JSON associant chaque utilisateur à son mot de passe. |
| `ADMIN_USERS` | Liste des utilisateurs autorisés à consulter `/users`. |
| `PULL_USERS` | Liste des utilisateurs autorisés à obtenir un jeton `pull`. |
| `TRAIN_USERS` | Liste des utilisateurs autorisés à obtenir un jeton `train`. |
| `JWT_SECRET_LOGIN` | Secret de signature des jetons `login`. |
| `JWT_SECRET_PULL` | Secret de signature des jetons `pull`. |
| `JWT_SECRET_TRAIN` | Secret de signature des jetons `train`. |
| `JWT_ALGORITHM` | Algorithme JWT, `HS256` par défaut dans le code. |

Les trois secrets sont distincts afin qu'un jeton destiné à une opération ne
puisse pas être vérifié avec le secret d'une autre opération.

## Règles métier

- Un utilisateur doit exister dans `USERS` et fournir le mot de passe exact.
- `username` doit comporter au moins 3 caractères et `password` au moins 5.
- Les types de jeton acceptés sont exactement `login`, `pull` et `train`.
- Un jeton `pull` exige que l'utilisateur soit présent dans `PULL_USERS`.
- Un jeton `train` exige que l'utilisateur soit présent dans `TRAIN_USERS`.
- Un jeton `login` est délivré à tout utilisateur authentifié ; il ne dépend pas
  de `ADMIN_USERS`, `PULL_USERS` ou `TRAIN_USERS`.
- Chaque jeton contient `username`, `token_type`, `role` et `exp`.
- `role` reprend la valeur de `token_type` et l'expiration est fixée à 60 minutes.
- `/health` est public et permet de vérifier que le processus HTTP répond.
- `/users` est réservé à un administrateur authentifié et ne renvoie que les
  noms d'utilisateurs, jamais les mots de passe.

## Endpoints

### `GET /health`

Réponse nominale :

```json
{"status": "ok"}
```

### `POST /login`

Requête :

```json
{
  "username": "<username>",
  "password": "<password>",
  "token_type": "pull"
}
```

Réponse nominale :

```json
{"access_token": "<jwt>"}
```

Le champ `token_type` doit être fourni explicitement par les clients du
parcours actif. S'il est omis, sa valeur est `null` et la demande est rejetée car
elle ne correspond à aucun type supporté.

| Situation | Statut attendu | Règle |
| --- | ---: | --- |
| Identifiants corrects, type autorisé | `200` | JWT retourné. |
| Identifiants incorrects | `401` | Authentification refusée. |
| Type absent, inconnu ou invalide | `400` | Type de jeton refusé après authentification. |
| Utilisateur non autorisé pour `pull` ou `train` | `403` | Identifiants valides mais rôle non accordé. |
| Corps absent ou champs trop courts | `422` | Validation Pydantic échouée. |

### `GET /users`

L'implémentation attend un corps correspondant au schéma de connexion :

```json
{
  "username": "<admin-username>",
  "password": "<password>"
}
```

La demande réussit uniquement si les identifiants sont valides et si
`username` appartient à `ADMIN_USERS`.

| Situation | Statut attendu |
| --- | ---: |
| Administrateur authentifié | `200` |
| Identifiants incorrects ou utilisateur non administrateur | `401` |
| Corps absent ou champs invalides | `422` |

## Consommation par les services actifs

| Consommateur | Type demandé | Vérification effectuée |
| --- | --- | --- |
| `initial-train` | `train` puis `login` si nécessaire | `train-api`, puis rechargement de la prédiction. |
| DAG `pull_weekly` | `pull`, puis `train` | `pull-data-api`, puis `train-api`. |
| Client de prédiction | `login` | Authentification de l'accès de prédiction selon le client. |

Les URLs internes et les variables d'environnement sont centralisées dans
[`docker-compose.apis.yml`](../../docker-compose.apis.yml) et dans le
[`Makefile`](../../Makefile).

## Procédure de validation

Depuis la racine du dépôt, avec la stack active démarrée et des valeurs de test
chargées dans `.env` :

```bash
curl -sS http://localhost:8005/health
curl -sS -X POST http://localhost:8005/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"<user>","password":"<password>","token_type":"pull"}'
```

Valider ensuite les scénarios suivants :

1. `health` retourne `200` et `{"status":"ok"}`.
2. Un utilisateur configuré obtient un jeton `login`.
3. Un utilisateur de `PULL_USERS` obtient un jeton `pull`.
4. Un utilisateur de `TRAIN_USERS` obtient un jeton `train`.
5. Le décodage de chaque jeton avec le secret correspondant confirme
   `username`, `token_type`, `role` et une expiration future.
6. Un mauvais mot de passe retourne `401`.
7. Un utilisateur absent de `PULL_USERS` ou `TRAIN_USERS` retourne `403` pour le
   type concerné.
8. Un type inconnu ou omis retourne `400` après authentification.
9. Un compte non administrateur ne peut pas utiliser `/users`.

Les tests automatisés de référence sont dans
[`tests/test_auth_api.py`](../../tests/test_auth_api.py). La validation de la
stack complète se poursuit avec les fiches [pull-data-api](pull-data-api.md),
[train-api](train-api.md) et [predict-api](predict-api.md).

## Diagnostic

- Si le service ne démarre pas, vérifier la présence et le format JSON de
  `USERS`, `ADMIN_USERS`, `PULL_USERS` et `TRAIN_USERS`.
- Si les services aval rejettent un jeton, vérifier le type demandé, le secret
  utilisé par le service consommateur et `JWT_ALGORITHM`.
- Ne jamais afficher un mot de passe, un secret ou un JWT dans les logs, les
  tickets d'incident ou la documentation.

Retour à l'[index du wiki opérationnel](README.md).
