# Logs centralisés — Alloy et Loki

## Responsabilité opérationnelle

Grafana Alloy découvre les conteneurs Docker du projet, collecte leurs sorties
`stdout`/`stderr` et les envoie à Loki. Grafana interroge ensuite Loki pour
permettre la recherche et le diagnostic des services actifs.

Le flux est :

```text
auth-api / pull-data-api / train-api / predict-api
                         ↓
                 Grafana Alloy
                         ↓
                       Loki
                         ↓
                      Grafana
```

Le composant one-shot `initial-train` n'est pas collecté par Alloy. Les
variantes v1 ne font pas partie du périmètre de cette fiche.

## Sélection des conteneurs

La configuration [`monitoring/alloy/config.alloy`](../../monitoring/alloy/config.alloy)
conserve uniquement les API portant le label Docker explicite
`org.accidents.stack=api`, associé au nom de service Compose :

```text
api/(auth-api|pull-data-api|train-api|predict-api)
```

La sélection ne dépend pas du nom du dossier de clonage ou du projet Compose.
Le label de sélection est déclaré sur les quatre API dans `docker-compose.apis.yml`.

Les labels indexés sont volontairement limités :

| Label | Valeur | Usage |
| --- | --- | --- |
| `project` | `accidents-mlops` | Isoler les logs du projet. |
| `service` | Nom du service Compose | Filtrer une API. |
| `source` | `docker` | Identifier l'origine. |
| `detected_level` | Détecté lorsque disponible | Filtrer le niveau. |

Les payloads HTTP, JWT, identifiants de conteneur, secrets et chemins locaux ne
doivent pas être promus en labels. Les applications doivent également éviter
de les écrire dans le contenu des logs.

## Configuration Loki

Loki est défini dans
[`monitoring/loki/loki.yml`](../../monitoring/loki/loki.yml) :

- port HTTP interne `3100` ;
- authentification désactivée pour cette stack locale ;
- stockage filesystem sous `/loki` ;
- index TSDB v13 ;
- rétention de `720h`, soit 30 jours ;
- compaction toutes les 10 minutes ;
- réplication unique et ring en mémoire.

Le volume Docker nommé `loki-data` contient les chunks, l'index et les données
de rétention. Il est supprimé par les cibles `reset` et `reset-full` du Makefile.

## Configuration Alloy

Alloy utilise le socket Docker monté en lecture seule à
`/var/run/docker.sock` pour la découverte et la lecture des logs. Le conteneur
est exécuté en `0:0` car cet accès est privilégié.

Le volume `alloy-data` conserve la position de collecte. Il évite de relire tous
les logs après un redémarrage.

Le montage en lecture seule ne supprime pas le caractère sensible du socket
Docker : une entité pouvant l'utiliser peut appeler l'API Docker. Ne pas
réutiliser ce montage pour un autre service et ne pas exposer Alloy à des
entrées non fiables.

## Recherche dans Grafana

Dans Grafana Explore, sélectionner la source Loki et utiliser par exemple :

```logql
{project="accidents-mlops", service="pull-data-api"}
```

Pour tous les services actifs :

```logql
{project="accidents-mlops", service=~"auth-api|pull-data-api|train-api|predict-api"}
```

Le dashboard [Logs des API](grafana.md) fournit les filtres `API` et `Niveau`.

## Démarrage et diagnostic

```bash
make monitoring-up
docker compose --env-file .env -f docker-compose.monitoring.yml ps
docker logs accidents-alloy
docker logs accidents-loki
```

Vérifier également que Docker Desktop expose `/var/run/docker.sock` sur macOS.
Pour générer une ligne de test, appeler le endpoint `/health` d'une API active puis
rechercher son label `service` dans Grafana Explore.

## Procédure de validation

1. Loki devient healthy sur `/ready` avant le démarrage d'Alloy.
2. Alloy démarre avec le socket Docker monté et sans erreur de permission.
3. Un appel `/health` génère une ligne consultable dans Loki.
4. Les quatre services actifs sont visibles et les composants hors périmètre ne le
   sont pas.
5. Les labels `project`, `service` et `source` sont présents et de faible
   cardinalité.
6. Un redémarrage d'Alloy reprend sa position grâce à `alloy-data`.
7. La rétention et la suppression des volumes lors d'un reset sont comprises
   avant toute opération destructive.

Retour à l'[index du wiki opérationnel](README.md) et à la fiche
[Grafana](grafana.md).
