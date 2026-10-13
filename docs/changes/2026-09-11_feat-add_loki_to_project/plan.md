# Plan d'implémentation

## Objectif

Ajouter une chaîne centralisée de journaux Docker `Grafana Alloy -> Loki -> Grafana` à la stack de monitoring existante. Les logs des API seront consultables dans Grafana, qui devra être démarré avec le reste de la stack via `make -f makefile2.mk`.

## État d'exécution

- Étape 1 : terminée.
- Étape 2 : terminée.
- Étape 3 : terminée.
- Étape 4 : terminée.

## API utilisées

Les API ci-dessous constituent les cibles applicatives de la collecte de logs. Leur sortie standard sera collectée par Alloy ; aucun contrat HTTP ne sera modifié.

| API | Service Compose | Endpoints utilisés par les flux actuels | Rôle |
| --- | --- | --- | --- |
| Authentification | `auth-api` | `POST /login` | Émet les jetons JWT nécessaires aux appels internes et aux interfaces. |
| Collecte de données | `pull-data-api` | `GET /pull_data`, `GET /health` | Extrait les données hebdomadaires pour le réentraînement. |
| Entraînement v2 | `train-api-v2` | `POST /train`, `GET /health` | API d'entraînement appelée par Airflow et par `initial-train`. |
| Prédiction v2 | `predict-api-v2` | `POST /predict`, `POST /reload`, `GET /metrics` | API utilisée par l'interface d'urgence et par Airflow après entraînement. |

Les services `train-api` et `predict-api` sont legacy et ne font pas partie des cibles de collecte ni du dashboard de ce plan. `initial-train` n'est pas une API : c'est un client ponctuel de bootstrap, déclenché par `make -f makefile2.mk init` pour créer le modèle initial ; il reste hors des cibles de collecte, limitées aux quatre API actives.

## Contexte

Le dépôt possède déjà une stack de monitoring indépendante dans `docker-compose.monitoring.yml` : Prometheus, Grafana et trois exporters. Grafana est déjà provisionné avec une source Prometheus, mais le fichier Makefile opérationnel est `makefile2.mk` ; le `Makefile` historique est explicitement hors périmètre. À ce jour, `makefile2.mk` démarre MLflow, les API actives et Airflow, sans démarrer la stack de monitoring.

Les API et les services associés écrivent aujourd'hui leurs logs vers `stdout`/`stderr` (logging Python, Uvicorn, BentoML ou Node). Grafana Alloy pourra lire les journaux des conteneurs Docker de l'hôte et les envoyer à Loki sans ajouter de client Loki, de secret ni de dépendance Python/Node dans chaque API. La source Loki sera provisionnée automatiquement dans Grafana afin que les logs soient exploitables dès le démarrage.

`makefile2.mk` transmet déjà `LOCAL_UID` et `LOCAL_GID` aux API qui écrivent dans des bind mounts du dépôt. Cette règle ne doit pas être appliquée aveuglément au monitoring : Grafana, Prometheus et Loki utilisent des utilisateurs internes propres à leurs images et des volumes Docker nommés. Le plan vérifiera les UID/GID réellement nécessaires par montage. Les données persistantes de Loki et l'état d'Alloy seront privilégiés en volumes nommés, afin d'éviter une écriture dans le dépôt avec un propriétaire inattendu. Alloy lira les logs via l'API Docker, au moyen du seul socket Docker monté en lecture seule ; si l'image officielle exige `root` pour cet accès, ce privilège sera limité au seul conteneur Alloy et documenté. Sur macOS, Docker Desktop doit exposer son socket par défaut `/var/run/docker.sock` avant le démarrage d'Alloy.

## Périmètre

### Inclus

- Ajouter Loki avec stockage persistant et configuration adaptée à un déploiement Docker local mono-instance.
- Ajouter Grafana Alloy pour découvrir les conteneurs Docker, lire leurs logs et les pousser vers Loki.
- Appliquer des labels sobres et stables pour filtrer les journaux par projet, service Compose et conteneur, sans indexer le contenu des requêtes ou des jetons.
- Provisionner Loki comme source de données Grafana et ajouter un dashboard de consultation des logs des API.
- Étendre exclusivement `makefile2.mk` et la documentation afin que Prometheus, Grafana, Loki et Alloy soient lancés, vérifiables et consultables dans la stack.
- Ajouter les tests de structure/configuration et les validations Docker pertinentes.
- Vérifier et documenter les UID/GID et droits requis par chaque montage de la chaîne de monitoring, sans dégrader l'exécution non-root des APIs.

### Hors périmètre

- Modifier les contrats HTTP, l'authentification JWT ou le comportement métier des API.
- Envoyer les logs vers un service hébergé externe ou ajouter des identifiants Grafana Cloud.
- Remplacer Prometheus ou les dashboards de métriques existants.
- Définir une politique centralisée de logs applicatifs structurés pour les services historiques ; Alloy collecte d'abord les flux `stdout`/`stderr` existants.
- Modifier la rétention ou le format des données métier, MLflow, DVC ou Airflow.
- Modifier le `Makefile` historique, les services legacy `train-api` et `predict-api`, ou l'application Streamlit OCS v1.

## Étape 1 — Définir la chaîne de collecte Loki et Alloy

### Objectif

Introduire les configurations versionnées de Loki et Alloy, avec une découverte Docker limitée au projet et des labels permettant de rechercher les logs par service sans exposer de données sensibles dans les labels.

### Modifications prévues

- Créer la configuration Loki avec répertoire de données persistant, stockage local et rétention explicitement documentée.
- Créer la configuration Alloy pour découvrir les conteneurs Docker, lire leurs flux de logs via l'API Docker et expédier les événements vers Loki.
- Limiter les cibles aux conteneurs du projet avec une règle de relabeling sur les labels Docker Compose (les filtres Docker répétés étant combinés avec un « et ») ; conserver les métadonnées de service et de conteneur utiles au diagnostic.
- Définir le répertoire de positions d'Alloy sur un volume persistant et confirmer l'utilisateur d'exécution requis par l'image pour les montages Docker en lecture seule.
- Ajouter, si nécessaire, un fichier d'exclusion Docker pour que les nouvelles configurations soient disponibles au build sans agrandir inutilement les images applicatives.

### Fichiers potentiellement concernés

- `monitoring/loki/loki.yml`
- `monitoring/alloy/config.alloy`
- `.dockerignore`

### Validation prévue

- Validation syntaxique de la configuration Loki avec l'image officielle.
- Validation de la configuration Alloy avec l'image officielle et vérification de sa découverte des conteneurs ciblés.
- Revue des labels produits pour confirmer l'absence de JWT, mots de passe, payloads ou données métier comme labels Loki.

### Message de commit proposé

`feat(monitoring): add Loki and Alloy log pipeline configuration`

## Étape 2 — Raccorder Loki et Alloy à la stack de monitoring

### Objectif

Démarrer Loki et Alloy de manière fiable avec la stack de monitoring, tout en conservant Prometheus, Grafana et les exporters existants inchangés dans leur rôle.

### Modifications prévues

- Ajouter les services `loki` et `alloy` à `docker-compose.monitoring.yml`, leurs volumes persistants, le montage contrôlé des logs Docker et leur accès au réseau partagé.
- Utiliser des volumes Docker nommés pour les données de Loki et l'état d'Alloy ; ne propager `LOCAL_UID`/`LOCAL_GID` aux services de monitoring que si un bind mount inscriptible le rend nécessaire et après vérification de l'utilisateur interne de l'image.
- Monter uniquement le socket Docker en lecture seule dans Alloy, puisque `loki.source.docker` lit les logs via l'API Docker ; documenter explicitement l'exception `root` si elle est indispensable à cette lecture, sans attribuer ce privilège aux autres services de monitoring.
- Documenter le prérequis Docker Desktop macOS : exposer le socket Docker par défaut `/var/run/docker.sock`, nécessaire à son montage dans Alloy. Ce chemin est également le standard sous Linux.
- Définir les dépendances et contrôles de santé nécessaires pour que Alloy n'expédie les logs qu'une fois Loki disponible.
- Ajouter dans `makefile2.mk` la commande Compose de monitoring et une cible dédiée pour démarrer Prometheus, Grafana, Loki et Alloy.
- Raccorder cette cible aux parcours `stack-up` et `init` afin que Grafana soit lancé avec le reste de la stack, y compris lors de la création initiale du modèle par `initial-train`.
- Adapter `reset` et `reset-full` si nécessaire pour arrêter proprement la stack de monitoring et traiter son volume Loki ; préserver le démarrage de Grafana sur son port actuel (`3000`).

### Fichiers potentiellement concernés

- `docker-compose.monitoring.yml`
- `makefile2.mk`
- `tests/test_docker_architecture.py`

### Validation prévue

- `docker compose --env-file .env -f docker-compose.monitoring.yml config`.
- `make -f makefile2.mk network` et démarrage de la cible de monitoring, puis contrôle que `prometheus`, `grafana`, `loki` et `alloy` sont en cours d'exécution.
- `make -f makefile2.mk stack-up`, puis confirmation que la stack applicative et Grafana démarrent ensemble.
- Vérification de santé de Loki et inspection des logs Alloy pour confirmer l'envoi sans boucle ni erreur de permission.
- Contrôle des propriétaires et permissions des volumes Loki/Alloy après démarrage, puis vérification qu'aucun fichier de runtime n'est créé dans le dépôt avec un UID/GID inattendu.
- Exécution ciblée de `pytest tests/test_docker_architecture.py`.

### Message de commit proposé

`feat(monitoring): run Loki and Alloy with the monitoring stack`

## Étape 3 — Provisionner Grafana pour l'exploration des logs API

### Objectif

Rendre Loki immédiatement utilisable dans l'instance Grafana démarrée par `makefile2.mk`, avec une vue dédiée aux APIs actives listées en tête de ce plan.

### Modifications prévues

- Ajouter une datasource Loki provisionnée, avec un UID stable et l'URL interne du service Loki.
- Créer un dashboard Grafana de logs avec variables de filtre (service/API et niveau lorsqu'il est présent), panneau Explore/Logs et requêtes LogQL compatibles avec les labels Alloy.
- Ajouter des liens ou consignes de navigation minimales pour passer des dashboards de métriques existants à l'exploration des logs.

### Fichiers potentiellement concernés

- `monitoring/grafana/provisioning/datasources/loki.yml`
- `monitoring/grafana/dashboards/api-logs-dashboard.json`
- `monitoring/grafana/provisioning/dashboards/dashboards.yml`

### Validation prévue

- Démarrage propre de Grafana avec la datasource Loki provisionnée.
- Vérification dans Grafana que la datasource répond et que le dashboard charge sans erreur de provisionnement.
- Émission d'un appel de santé et d'un appel contrôlé vers chaque API active, puis recherche des lignes correspondantes dans Grafana par label de service.

### Validation réalisée

- Grafana redémarré avec succès ; ses logs confirment l'insertion de la datasource `Loki` (`uid=loki`) et le provisionnement des dashboards sans erreur.
- L'endpoint `http://localhost:3000/api/health` répond avec une base de données Grafana saine.
- Loki retourne les journaux de `pull-data-api` pour la requête `{service="pull-data-api"}`.

### Message de commit proposé

`feat(grafana): provision API logs from Loki`

## Étape 4 — Documenter l'exploitation et valider le parcours complet

### Objectif

Documenter le démarrage, les points d'accès et le diagnostic de la chaîne de logs, puis valider de bout en bout que Grafana lancé dans la stack donne accès aux logs des API.

### Modifications prévues

- Créer une documentation dédiée sous `docs/loki/` décrivant l'architecture `Alloy -> Loki -> Grafana`, les ports, les commandes `make -f makefile2.mk`, le démarrage dans `stack-up` et `init`, ainsi que le diagnostic de la chaîne de logs.
- Décrire la persistance, la rétention choisie, les labels disponibles et les limites de confidentialité.
- Documenter les utilisateurs d'exécution, le recours aux volumes nommés et les permissions minimales d'Alloy pour la lecture des logs Docker.
- Ajouter ou ajuster des tests de régression de configuration pour les services, volumes, datasource et dashboard introduits.

### Fichiers potentiellement concernés

- `docs/loki/README.md`
- `tests/test_docker_architecture.py`
- `changes/2026-09-11_feat-add_loki_to_project/changes.md`

### Validation prévue

- Exécution des tests ciblés de configuration et des tests applicatifs concernés par les éventuelles adaptations.
- `docker compose --env-file .env -f docker-compose.monitoring.yml config`.
- Démarrage via `make -f makefile2.mk stack-up`, puis via `make -f makefile2.mk init` lorsque le scénario de bootstrap est validé ; confirmation que Grafana est lancé sur `http://localhost:3000` et que Loki reçoit les logs d'au moins une API active.
- Revue finale de `git diff` et `git status` pour vérifier l'absence de modification hors périmètre.

### Validation réalisée

- Documentation créée sous `docs/loki/`.
- Tests ciblés de Compose, du Makefile et du provisionnement Grafana exécutés.
- Les services Prometheus, Grafana, Loki, Alloy et les API actives sont en cours d'exécution après le parcours de démarrage de la stack.

### Message de commit proposé

`docs(monitoring): document Grafana Loki log operations`

## Critères de fin

- Loki et Grafana Alloy sont définis dans la stack de monitoring avec une configuration versionnée et validée.
- Les logs `stdout`/`stderr` des API actives utilisées sont consultables dans Loki, filtrables par labels stables et sans secrets dans les labels ; les services legacy ne constituent pas une cible fonctionnelle.
- Grafana est lancé par `make -f makefile2.mk stack-up` et `make -f makefile2.mk init`, possède une datasource Loki provisionnée et affiche un dashboard de logs API fonctionnel.
- Prometheus, les exporters et les dashboards existants continuent de démarrer et de fonctionner.
- La documentation `docs/loki/`, les tests concernés et le change log sont à jour après l'implémentation.
- Les montages inscriptibles du monitoring n'introduisent pas de conflit d'UID/GID avec les bind mounts gérés par `LOCAL_UID` et `LOCAL_GID` ; le montage de lecture du socket Docker d'Alloy respecte le moindre privilège possible.
