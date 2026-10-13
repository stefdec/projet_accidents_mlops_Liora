# Validation locale de la stack

Le point d’entrée unique est `Makefile` : `make stack-up`, puis `make presentation` dans un second terminal. `emergency-interface` est inclus dans le démarrage de la stack.

## Dépendances Python

Depuis la racine, installer les dépendances verrouillées avec l'extra utilisé par les tests du monitoring :

```bash
uv sync --frozen --extra monitoring
```

Sur macOS, LightGBM nécessite OpenMP. Si `libomp.dylib` manque, installer `libomp` avec le gestionnaire de paquets du poste, par exemple `brew install libomp` avec Homebrew. Les images Linux du projet installent déjà `libgomp1`; exécuter les tests dans l'image du composant permet de vérifier ses dépendances runtime sans modifier le poste.

BentoML local et les services de prédiction/bootstrap/Airflow utilisent 1.4.39. Les tests locaux qui remplacent des services par des doubles ne dispensent pas du smoke réel dans Docker.

Les copies du dépôt peuvent contenir d'anciens bytecodes Python. Pour les contrôles de référence, utiliser un cache neuf et désactiver le cache pytest :

```bash
.venv/bin/python -X pycache_prefix=/tmp/accidents-validation-pycache -m pytest \
  tests/train_api tests/test_auth_api.py tests/test_pull_data_api.py \
  tests/test_initial_train_trigger.py tests/test_predict_api_service.py \
  src/airflow_dags/tests/test_pull_train.py app/pres-sl/tests \
  -p no:cacheprovider
```

## Ressources Docker vérifiées

Le bootstrap complet a provoqué un OOM (sortie 137) avec une VM Docker de
8 Go et la stack complète active. Avec 16 Go et l’ordre de `make init`
(entraînement avant Airflow), l’entraînement, l’enregistrement MLflow,
la synchronisation BentoML et le reload ont réussi. Ce résultat ne constitue
pas une mesure du minimum nécessaire sur tous les postes.

## Contrôles runtime

Valider les quatre Compose avec `config --quiet` pour éviter d'afficher les secrets interpolés. Construire et démarrer la stack avec `make stack-up`, puis lancer la présentation avec `make presentation`.

La validation de prédiction exige un modèle publié dans BentoML et une réponse de l'interface portant `status=remote_api`. Une réponse de `/health` ou du moteur heuristique ne prouve pas que le champion est utilisable.

Les API portent le label Docker `org.accidents.stack=api`, utilisé par Alloy. Vérifier dans Loki que les quatre valeurs du label `service` sont présentes et que des logs récents existent. La configuration valide syntaxiquement et le endpoint `/ready` ne suffisent pas à prouver l'ingestion.

Pour cAdvisor, vérifier les séries CPU et mémoire avec un nom de conteneur, par exemple `container_memory_usage_bytes{name!=""}`. Une cible Prometheus `up` avec seulement des séries de l'hôte ne prouve pas la collecte des conteneurs. Docker Desktop utilise une machine virtuelle Linux; les montages de cgroups et du stockage Docker peuvent différer d'un serveur Linux. Ne pas affaiblir la configuration du daemon pour satisfaire un ancien client de monitoring.

Les DAGs du projet peuvent créer et pousser des commits Git après versionnement DVC. Pendant le nettoyage sans commits, les laisser pausés et réserver les tests de bout en bout à un environnement isolé sans publication dans le dépôt utilisateur.

Arrêter les services de validation sans `--volumes` et conserver les données. `reset` et `reset-full` ne sont pas des commandes de vérification.

## Limite cAdvisor avec le snapshotter overlayfs

Le socket Docker est monté sur `/docker.sock`, hors du montage `/var/run` en lecture seule, et cAdvisor reçoit `--docker=unix:///docker.sock`. Le [paramètre Docker de cAdvisor](https://github.com/google/cadvisor/blob/master/docs/runtime_options.md) permet ce choix explicite.

Sur le Docker Desktop testé (Docker 29.8.2, stockage `overlayfs`), cAdvisor 0.49.1 accède maintenant au daemon mais cherche un ancien chemin `layerdb/mounts` qui n’existe plus. Un problème similaire est décrit dans le [ticket du projet cAdvisor](https://github.com/google/cadvisor/issues/3860).

L’exclusion des métriques disque proposée dans ce ticket a été testée dans un conteneur de validation, mais n’a pas restauré les séries CPU/mémoire de conteneurs nommés sur ce poste. Elle n’est donc pas intégrée à la configuration finale. La cible cAdvisor répond, mais les panneaux de métriques par conteneur restent incomplets sur cette plateforme. Les métriques des API, exporters et de node-exporter restent accessibles.

Ne pas déclarer le monitoring des conteneurs pleinement validé sur ce poste. Une vérification sur un hôte Linux compatible, ou une évolution ciblée de cAdvisor/du raccordement au runtime, reste nécessaire. Ne pas changer le storage driver ni effacer le stockage Docker pour contourner cette limite durant le nettoyage.

La configuration générée/personnalisée `src/airflow_dags/config/airflow.cfg` reste locale et ignorée par Git : elle peut contenir des clés sensibles. Une copie isolée neuve la régénère, sans copier l’état secret de l’instance existante.
