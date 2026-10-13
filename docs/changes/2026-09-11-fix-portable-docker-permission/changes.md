## Résumé du projet

**Problème**

Les builds Docker pouvaient échouer selon la machine hôte lorsque `makefile2.mk` transmettait directement les UID/GID locaux aux images. Ces identifiants peuvent varier d’un système à l’autre et entrer en collision avec des utilisateurs ou groupes déjà présents dans l’image de base.

Le problème avait déjà été observé sur Linux, puis reproduit sur macOS avec le GID `20`, déjà utilisé par le groupe `dialout` dans `python:3.12-slim`. Dans ce cas, `groupadd` échouait avec l’erreur `GID '20' already exists`.

Plus généralement, dériver automatiquement les UID/GID depuis la machine hôte rendait donc les builds dépendants de l’environnement local du développeur et pouvait provoquer des échecs différents selon le système, l’utilisateur ou l’image de base utilisée.

**Solution**

Faire en sorte que la création du groupe réutilise un GID existant lorsqu’il est déjà présent, ou crée le groupe applicatif lorsqu’il est disponible, tout en conservant des utilisateurs non-root et des opérations de propriété numérique compatibles avec les bind mounts. Utiliser des valeurs UID/GID reproductibles `1000:1000` par défaut dans `makefile2.mk`, avec des surcharges explicites pour les hôtes nécessitant une propriété différente sur les bind mounts.

**Décision opérationnelle actuelle**

* Conserver `1000:1000` comme valeur par défaut pour le moment.
* Si un hôte ou une image de base signale une collision d’UID/GID, relancer explicitement avec une autre paire libre, par exemple `1001:1001`. Commande : `make -f makefile2.mk init LOCAL_UID=1001 LOCAL_GID=1001`
* Conserver le même GID entre les services qui partagent des volumes en écriture.

**Métadonnées**

* **Branche :** `fix/portable-docker-user-permissions`
* **Date :** `2026-09-11`
* **Périmètre :** images Docker, arguments de build Compose, valeurs par défaut du Makefile, documentation opérationnelle et tests de validation
* **Services concernés :** train API v2, train API, MLflow, Streamlit, stack Airflow
* **Statut :** implémenté et validé

## 2026-09-11

### Inventaire de la gestion des UID/GID Docker

**Message de commit**

`chore(docker): inventory UID and GID handling`

**Ce qui a changé**

* Inventaire des arguments de build UID/GID et de la création des utilisateurs non-root pour les images train API v2, train API, MLflow et Streamlit.
* Confirmation que `makefile2.mk` dérive `LOCAL_UID` et `LOCAL_GID` de la machine hôte et les transmet à Docker Compose.
* Confirmation que les Dockerfiles concernés créent des groupes avec le GID fourni sans vérifier si ce GID existe déjà dans l’image de base.

**Pourquoi**

* Les UID/GID de la machine hôte peuvent entrer en collision avec des utilisateurs ou groupes déjà présents dans les images de base.
* Le problème n’est pas spécifique à macOS : il peut se produire sur différents environnements Linux ou macOS selon les identifiants utilisés localement.
* Cet inventaire permet d’identifier toutes les images dépendantes avant d’appliquer une stratégie portable de création des utilisateurs et groupes.

**Fichiers**

* `makefile2.mk`
* `docker-compose.apis.yml`
* `src/train_api_v2/Dockerfile`
* `src/train_api/Dockerfile`
* `src/infra/mlflow/Dockerfile`
* `app/sl_OCS_v1/Dockerfile`

**Validation**

* Vérification de la branche courante et de l’état du working tree avant modification.
* Recherche dans tous les Dockerfiles et arguments de build Compose de `LOCAL_UID`, `LOCAL_GID`, `APP_UID`, `APP_GID`, `groupadd` et `useradd`.

## 2026-09-11

### Reproduction d’une collision de GID

**Message de commit**

`test(docker): reproduce UID and GID collisions`

**Ce qui a changé**

* Vérification que `python:3.12-slim` contient déjà le groupe `dialout` avec le GID `20`.
* Reproduction de l’échec de build de `train_api_v2` avec `APP_UID=501` et `APP_GID=20`.
* Confirmation que le GID `1000` n’est pas présent dans l’image de base.

**Pourquoi**

* Cela confirme qu’un GID provenant de la machine hôte peut entrer en collision avec un groupe existant dans l’image avant même la création de l’utilisateur applicatif.
* Ce scénario illustre un problème plus général de portabilité des builds lorsque les UID/GID sont directement dérivés de l’hôte.

**Fichiers**

* `src/train_api_v2/Dockerfile`
* `makefile2.mk`

**Validation**

* `docker run --rm python:3.12-slim sh -c 'getent group 20; getent group 1000'`
* `docker build --build-arg APP_UID=501 --build-arg APP_GID=20 -f src/train_api_v2/Dockerfile .` (échoue comme prévu avec `GID '20' already exists`)

## 2026-09-11

### Rendre la création des groupes Docker tolérante aux GID existants

**Message de commit**

`fix(docker): tolerate existing application group IDs`

**Ce qui a changé**

* Réutilisation d’un groupe existant lorsque le GID demandé est déjà présent dans l’image de base.
* Application de cette création conditionnelle du groupe aux images train API v2, train API, MLflow et Streamlit.
* Utilisation de GID numériques pour les opérations de propriété qui doivent également fonctionner lorsque le groupe existant porte un autre nom.

**Pourquoi**

* Les builds restent désormais compatibles avec différents UID/GID provenant de l’hôte tout en conservant une exécution non-root et les permissions d’écriture sur les volumes.
* La création des utilisateurs et groupes devient moins dépendante des particularités de la machine de développement.

**Fichiers**

* `src/train_api_v2/Dockerfile`
* `src/train_api/Dockerfile`
* `src/infra/mlflow/Dockerfile`
* `app/sl_OCS_v1/Dockerfile`

**Validation**

* `docker build --build-arg APP_UID=501 --build-arg APP_GID=20 -f src/train_api_v2/Dockerfile .` (réussi)
* `uv run pytest tests/train_api_v2/test_dockerfile.py tests/train_api_v2/test_compose_service.py -q` (10 tests réussis)
* `git diff --check`

## 2026-09-11

### Validation du démarrage portable de la stack

**Message de commit**

`test(docker): validate portable stack startup`

**Ce qui a changé**

* Reconstruction des API concernées avec des arguments de type hôte `501:20` et portables `1000:1000`.
* Démarrage de la stack complète avec `make -f makefile2.mk stack-up` sans déclencher l’entraînement initial.
* Exécution séparée de l’entraînement initial une fois la stack déclarée saine.

**Pourquoi**

* Cela valide le chemin complet de démarrage et confirme que la gestion des UID/GID ne bloque plus le déploiement selon les identifiants utilisés par la machine hôte.

**Fichiers**

* `makefile2.mk`
* `src/train_api/Dockerfile`
* `docs/changes/fix-portable-docker-user-permissions.md`

**Validation**

* Les conteneurs des API et d’Airflow ont signalé un état sain.
* Le health check interne de la train API a renvoyé `{"status":"ok"}`.
* L’entraînement initial s’est terminé avec succès et a publié un nouveau champion BentoML.
* L’état SQLite a indiqué `initial-bootstrap | succeeded | retry_count=0`.

## 2026-09-11

### Utilisation de valeurs UID/GID reproductibles par défaut

**Message de commit**

`chore(docker): use stable UID and GID defaults`

**Ce qui a changé**

* Modification des valeurs par défaut de `makefile2.mk` vers `LOCAL_UID=1000` et `LOCAL_GID=1000`.
* Conservation des surcharges explicites en ligne de commande pour les hôtes dont les répertoires montés en bind nécessitent un autre propriétaire.
* Mise à jour du test Compose et de la documentation opérationnelle.

**Pourquoi**

* La détection automatique depuis l’hôte rendait les builds dépendants d’identifiants spécifiques à chaque environnement.
* Des valeurs par défaut stables rendent les builds locaux, CI et de déploiement plus déterministes tout en conservant la possibilité de surcharger explicitement les permissions.

**Fichiers**

* `makefile2.mk`
* `tests/train_api_v2/test_compose_service.py`
* `docs/refactor/train_api/operations.md`

**Validation**

* `uv run pytest tests/train_api_v2/test_compose_service.py -q`
* `git diff --check`
