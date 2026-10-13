## Configurer la collecte Loki et Alloy

**Message de commit**

`feat(monitoring): add Loki and Alloy log pipeline configuration`

**Ce qui a changé**

- Ajout d'une configuration Loki mono-instance avec stockage TSDB local, volume de données prévu sous `/loki` et rétention de 30 jours.
- Ajout d'une configuration Grafana Alloy qui découvre exclusivement les quatre API actives via leurs labels Docker Compose et envoie leurs logs vers Loki.
- Conservation de labels Loki à faible cardinalité (`project`, `source`, `service`) sans données de requête, secrets, identifiants de conteneur ou digests d'image.

**Pourquoi**

- Préparer la collecte centralisée des journaux sans modifier les contrats HTTP ni ajouter de client Loki dans les applications.
- Éviter la collecte des services legacy et des journaux de l'hôte hors périmètre.

**Fichiers**

- `monitoring/loki/loki.yml`
- `monitoring/alloy/config.alloy`

**Validation**

- `docker run --rm -v "$PWD/monitoring/loki/loki.yml:/etc/loki/config.yml:ro" grafana/loki:3.5.3 -config.file=/etc/loki/config.yml -verify-config` : réussi.
- `docker run --rm -v "$PWD/monitoring/alloy/config.alloy:/etc/alloy/config.alloy:ro" --entrypoint alloy grafana/alloy:v1.9.2 validate /etc/alloy/config.alloy` : réussi.
- `git diff --check` : réussi.

## Lancer Loki et Alloy avec la stack de monitoring

**Message de commit**

`feat(monitoring): run Loki and Alloy with the monitoring stack`

**Ce qui a changé**

- Ajout des services Loki et Alloy, de leurs volumes Docker nommés et de la dépendance d'Alloy à la disponibilité de Loki.
- Ajout de la cible `monitoring-up` dans `makefile2.mk`, appelée par `stack-up` et `init` avant le démarrage des API afin de collecter leurs logs dès leur création.
- Ajout des cibles et nettoyages nécessaires pour arrêter la stack de monitoring et supprimer ses volumes lors d'une réinitialisation complète.
- Ajout de tests de structure pour les services, les montages en lecture seule, les volumes et les commandes Makefile.
- Correction de la sélection Alloy : une règle de relabeling unique conserve les quatre API actives du projet, car les filtres Docker `label` répétés sont combinés avec un « et ».

**Pourquoi**

- Démarrer Prometheus, Grafana, Loki et Alloy avec le reste de la stack sans modifier le `Makefile` historique.
- Conserver les données Loki et les offsets Alloy hors des bind mounts du dépôt, tout en limitant l'accès privilégié au seul Alloy pour la lecture du socket Docker.

**Fichiers**

- `docker-compose.monitoring.yml`
- `makefile2.mk`
- `tests/test_docker_architecture.py`
- `tests/train_api_v2/test_compose_service.py`
- `docs/changes/2026-09-11_feat-add_loki_to_project/plan.md`

**Validation**

- `docker compose --env-file .env -f docker-compose.monitoring.yml config --quiet` : réussi.
- `make -f makefile2.mk monitoring-up` : réussi ; Prometheus, Grafana, Loki, Alloy et les exporters sont démarrés.
- `make -f makefile2.mk stack-up` : réussi ; MLflow, monitoring, API actives et Airflow sont démarrés sans entraînement initial.
- `pytest tests/test_docker_architecture.py::test_monitoring_has_an_independent_compose_project tests/train_api_v2/test_compose_service.py::test_make_starts_monitoring_with_stack_and_bootstrap` : 2 réussis.
- Sur Docker Desktop macOS (`desktop-linux`), un conteneur exécuté en `0:0` accède à l'API Docker via `/var/run/docker.sock:ro` ; ce chemin est également le standard sous Linux.
- Après recréation d'Alloy et appels `GET /health`, Loki retourne les journaux de `pull-data-api` avec les labels `project=accidents-mlops`, `service=pull-data-api` et `source=docker`.

## Provisionner Loki dans Grafana et le dashboard de logs API

**Message de commit**

`feat(grafana): provision API logs from Loki`

**Ce qui a changé**

- Ajout de la datasource Loki provisionnée avec l'UID stable `loki` et l'URL interne du service.
- Ajout du dashboard Grafana `Logs des API`, avec filtres sur les quatre services actifs et le niveau de log détecté.
- Ajout d'un test de régression sur la datasource et la requête LogQL du dashboard.

**Pourquoi**

- Rendre les journaux collectés par Alloy consultables immédiatement dans Grafana, sans configuration manuelle après le démarrage de la stack.

**Fichiers**

- `monitoring/grafana/provisioning/datasources/loki.yml`
- `monitoring/grafana/dashboards/api-logs-dashboard.json`
- `tests/test_docker_architecture.py`

**Validation**

- `uv run python -m json.tool monitoring/grafana/dashboards/api-logs-dashboard.json` : réussi.
- `docker compose --env-file .env -f docker-compose.monitoring.yml config --quiet` : réussi.
- Grafana redémarré ; `GET http://localhost:3000/api/health` retourne une base de données saine.
- Les logs Grafana confirment l'insertion de la datasource `Loki` (`uid=loki`) et le provisionnement des dashboards sans erreur.
- `pytest tests/test_docker_architecture.py::test_monitoring_has_an_independent_compose_project tests/test_docker_architecture.py::test_grafana_provisions_loki_and_the_active_api_logs_dashboard tests/train_api_v2/test_compose_service.py::test_make_starts_monitoring_with_stack_and_bootstrap` : 3 réussis.

## Documenter l'exploitation Loki et Grafana

**Message de commit**

`docs(monitoring): document Grafana Loki log operations`

**Ce qui a changé**

- Ajout de la documentation de démarrage, de recherche LogQL, de persistance, des UID/GID et du diagnostic sous `docs/loki/`.
- Documentation explicite de la portée de sécurité du socket Docker et de sa compatibilité macOS Docker Desktop / Linux.

**Pourquoi**

- Permettre l'exploitation et le diagnostic de la chaîne Alloy, Loki et Grafana sans dépendre du Makefile historique.

**Fichiers**

- `docs/loki/README.md`
- `changes/2026-09-11_feat-add_loki_to_project/changes.md`

**Validation**

- `make -f makefile2.mk stack-up` et `make -f makefile2.mk init` lancent le monitoring dans les parcours complets ; l'état final confirme que Prometheus, Grafana, Loki, Alloy et les API actives sont en cours d'exécution.
- Une requête Loki filtrée par `{service="pull-data-api"}` retourne les logs collectés.
- `git diff --check` et revue de l'état Git : réalisés en validation finale.
