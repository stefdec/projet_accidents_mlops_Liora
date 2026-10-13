# Audit — étape 1

Date : 13 octobre 2026. Branche : `main`. Aucun code applicatif modifié ou supprimé, aucun commit créé.

## Résultat de référence

La stack démarre via `make -f makefile2.mk stack-up`. `emergency-interface`, explicitement confirmée active, a été construite et lancée séparément via le Compose API. La présentation a été lancée séparément avec Streamlit.

Les 23 conteneurs permanents observés sont restés démarrés, sans redémarrage automatique. Les jobs `airflow-init` et `bentoml-init` sont terminés avec code 0. Les services possédant un healthcheck sont sains; les autres ont été contrôlés par HTTP quand applicable. Cela ne prouve pas encore tous les workflows : la collecte distante, un nouvel entraînement initial complet et les notifications Slack ne sont pas validés.

Un champion existe déjà dans les données MLflow locales. Le nouveau volume BentoML était vide : les premières prédictions répondaient 503. La publication de ce champion par les fonctions de `src/inital_train/main.py`, suivie de `/reload`, a permis une prédiction HTTP 200 via l'API et via l'interface (`status=remote_api`). Aucun entraînement ni changement d'alias MLflow n'a été effectué.

Deux anomalies opérationnelles empêchent de déclarer le monitoring totalement fonctionnel : absence d'ingestion des logs API par Alloy et absence de connexion Docker utilisable par cAdvisor, malgré une cible Prometheus disponible.

## Inventaire et méthode

`inventory.json` contient 393 entrées de code, configuration, assets, tests et documentation, avec imports Python extraits par AST et empreintes SHA-256. Les catégories au niveau des dossiers sont une première classification; elles ne constituent pas une autorisation de supprimer tous leurs fichiers. Les README, tests et ressources non référencées d'un composant actif restent à examiner au moment du lot correspondant.

Les fichiers de données, états PostgreSQL/MLflow, caches, dépendances installées, logs et configurations personnelles d'agents sont traités séparément. Ils ne sont pas assimilés à du code mort. Aucune configuration CI de type `.github/workflows` n'a été trouvée; les fichiers `.github/skills`, agents et hooks appartiennent à l'outillage local et sont conservés.

Les preuves examinées comprennent les recettes Make, les quatre Compose, les Dockerfiles et leurs COPY/commandes, les imports Python, le packaging, les DAGs, les endpoints HTTP, le serveur et client React, les producteurs/consommateurs des fichiers de monitoring, DVC et les références documentaires. Les usages externes au dépôt ne peuvent pas être exclus par cette analyse.

## Graphe actif

| Racine / producteur | Dépendance prouvée | Conséquence |
| --- | --- | --- |
| `makefile2.mk` | Compose MLflow, API, Airflow et monitoring | Source de l'orchestration à migrer, y compris appels Make récursifs |
| Compose MLflow | Dockerfile MLflow, PostgreSQL, `data/mlflow/postgres`, `data/mlflow/artifacts` | Conserver les données; port hôte configurable, serveur interne 5001 |
| Compose API | `src/auth_api`, `src/pull_data_api`, `src/train_api_v2`, `src/predict_api_v2`, `src/inital_train`, `interface` | Quatre API, déclencheur manuel et interface active |
| Authentification | variables utilisateurs/JWT, `/login` | Jetons distincts login/pull/train; ne pas modifier les contrats |
| Collecte | DagsHub, `/pull_data`, bind mount `data/incoming` | Données externes nécessaires au workflow hebdomadaire |
| Entraînement v2 | CSV `data/features/data_final_binaire.csv`, Parquet entrants, configuration YAML, SQLite, MLflow | Dataset présent (184 773 111 octets), artefacts et état à préserver |
| Entraînement v2 | exports `monitoring/drift/drift_results.json`, `monitoring/ml/model_performance.json`, `reports/carbon` | Ces fichiers runtime sont consommés par les exporters; ils ne sont pas des archives inutiles |
| MLflow v2 | code embarqué via `code_paths` dans le modèle | Vérifier les imports des modèles sérialisés avant tout déplacement de modules |
| Initialisation / Airflow | import du modèle MLflow dans BentoML, volume `bentoml_store`, `current_model.txt`, `/reload` | BentoML demeure nécessaire au fonctionnement actuel |
| Airflow worker | `.dvc/config`, `.dvc/config.local`, `.git`, données entrantes et cache dédié | DVC demeure actif; montages et credentials locaux nécessaires au chemin distant |
| `pull_train.py` | DAG `pull_train`, lundi à 03:00, collecte → DVC/Git → train → publication/reload | Workflow courant à conserver; tests du planning incohérents |
| `pull_weekly.py` | DAG distinct `pull_weekly`, toutes les cinq minutes, compteur/arrêt de simulation | Pas un simple doublon interchangeable; usage de simulation à décider, conserver provisoirement |
| `interface` | npm lockfile, Vite/React, serveur Express, proxy auth/predict | Obligatoire; port 3001, dépendances `auth-api` et `predict-api-v2` |
| `app-pres.py` | `app/pres-sl/app.py`, navigation, huit pages, templates et renderer | Référence Streamlit confirmée; ne dépend pas des anciennes applications |
| Renderer présentation | lecture des templates/CSS, embarquement d'images et polices en URI data | Document généré avec huit pages, dix images et quatre polices |
| Monitoring | Dockerfile racine, package Python, exporters, Prometheus, dashboards/provisioning, Loki/Alloy | Le Dockerfile racine est utilisé même si son CMD par défaut semble obsolète : Compose remplace la commande |
| `pyproject.toml` | package dans `src/train_api/utils/projet_accidents_mlops`, `uv.lock` | Impossible de supprimer `src/train_api` en bloc sans casser le build actuel |
| `dvc.yaml` | préparation `pipeline/01_clean.py` → `02_prepare.py` → `03_features.py`, snapshot `04_snapshot.py` | La préparation du dataset actif reste utile même hors démarrage Docker |
| Pipeline / scripts monitoring historiques | imports du package `projet_accidents_mlops` | Examiner les consommateurs individuellement avant suppression ou déplacement |

## Classification des candidats

### Définitivement utilisés

Stack décrite ci-dessus, `interface/`, `app-pres.py` et dépendances de `app/pres-sl`, package déclaré dans `pyproject.toml`, préparation des données, fichiers de build/configuration et tests effectivement exécutés. Les journaux `docs/changes` relèvent de la traçabilité obligatoire.

### Probablement utilisés — conserver jusqu'à vérification du lot

- `pipeline/run_pipeline.py`, `04_train.py`, `05_predict.py`, outils de drift/performance et scripts smoke : usages développeur/historiques possibles; absents des commandes de référence mais consommateurs explicites du package partagé.
- `payload.json` : utilisé avec succès pour le smoke de prédiction de cet audit.
- `pull_weekly.py` : importé par Airflow, DAG réellement listé et pausé; usage de simulation distinct du DAG hebdomadaire.
- Documents d'exploitation v2 : pertinents, mais commandes Make et certains détails à corriger.

### Probablement inutilisés — aucune suppression à ce stade

- `scripts/migrate_mlflow_storage.sh` et `scripts/migrate_legacy_backups.sh` : migrations ponctuelles appelées uniquement par l'ancien Makefile; aucune preuve qu'elles soient encore nécessaires à un autre poste.
- `create_github_issues_generales.sh` et CSV de roadmap : outillage de gestion, aucun appel depuis la stack; ne pas exécuter le script pendant l'audit.
- `requirements.txt` racine : contient uniquement un commentaire de squelette, aucun rôle dans les builds actifs qui utilisent leurs requirements propres ou `uv.lock`.
- Volume déclaré `shared-api-data` : aucun montage consommateur dans le Compose actuel; la collecte utilise un bind mount. Examiner le retrait de la déclaration, sans supprimer un éventuel volume utilisateur.

### Définitivement inutiles au code source courant

Les `.DS_Store` et bytecodes/caches Python sont générés, régénérables et ne définissent aucune fonctionnalité. Le recensement a trouvé neuf `.DS_Store` et 74 fichiers de cache sous les racines examinées, après tests; les quantités peuvent évoluer. Ils ne sont pas encore supprimés. Les caches installés ne doivent pas être confondus avec les archives applicatives.

### Historique / legacy — candidats à retirer après vérification

- `src/train_api/main.py`, son Dockerfile et ses requirements : remplacés dans le Compose actif par `train-api-v2`; conserver séparément le sous-package `utils` toujours utilisé.
- `src/predict_api/` : ancienne implémentation et exemple, remplacés par `src/predict_api_v2`; consommateurs restants dans anciens tests/Makefile à traiter ensemble.
- Applications `app/sl_legacy`, `app/sl_app`, `app/sl_OCS_v1`, `app/presentation`, `app/soutenance` et leurs entrées racine : références explicites dans anciennes documentations/Makefile, absentes de l'orchestration actuelle; conserver jusqu'à vérification des imports/assets partagés du lot applicatif.
- Ancien `Makefile` : commandes d'API et d'application incohérentes avec les services du Compose actuel; consolidation nécessaire.
- `docs/refactor`, brouillon Airflow et audit de machine : historiques à comparer aux guides actuels avant consolidation/suppression.
- Neuf sauvegardes sous `data/backups` : copies historiques de modèles, données de configuration et rapports; état local ignoré. Ne pas les supprimer dans un nettoyage de code sans décision explicite sur ces données.

## Documentation

| Documents | État observé | Traitement prévu |
| --- | --- | --- |
| `README.md`, `docs/README.md`, index API/ML/applications | Ancienne architecture, commandes/OCS/API historiques | Réécrire selon la stack confirmée |
| `README_PIPELINE.md` | Préparation utile mêlée à entraînement historique | Conserver la procédure de fabrication des données; consolider le reste |
| `README_monitoring.md` | Contient v2 et historique, procédures datées | Confronter aux configs, retirer doublons |
| `docs/operations/*`, `docs/loki/README.md` | Parcours v2, références Makefile ancien; filtre Alloy inadapté | Conserver/corriger les procédures actives |
| `docs/api/train-api.md`, `docs/ml/*`, `docs/airflow/*` | Mélange de contrats/workflows historiques | Consolider avec guides d'exploitation actuels |
| Guide emergency-interface | Interface active | Conserver, vérifier flux et fallback |
| Guide OCS et README anciennes applications | Historique des applications candidates | Retirer avec les applications si usages exclusifs confirmés |
| `app/pres-sl/README.md` | Entrée actuelle; commande de tests avec chemin suspect | Corriger et documenter lancement depuis la racine |
| `docs/refactor/*`, `docs/audit-yann.md` | Plans/rapports anciens ou propres à une machine | Extraire uniquement les informations encore utiles |
| `docs/changes/*` | Traçabilité | Conserver; les références historiques ne sont pas des commandes actives |

## Tests et commandes réellement exécutés

| Vérification | Résultat |
| --- | --- |
| Quatre `docker compose ... config --quiet` | Réussi |
| `uv sync --frozen` | Réussi; environnement `.venv` créé, avertissement version uv/build backend |
| `make -f makefile2.mk stack-up` | Réussi, build et démarrage réels MLflow/API/Airflow/monitoring |
| Build API, initial-train, Airflow et emergency-interface | Réussi |
| `docker compose ... up -d --no-deps emergency-interface` | Réussi |
| Streamlit sur 8501, endpoint `/_stcore/health` | HTTP 200 |
| Génération de `components.navigation.document()` | Huit pages et assets locaux chargés avec succès |
| AppTest Streamlit | Timeout après 30 secondes : validation du rendu navigateur non acquise par cet outil |
| Tests actifs sur macOS, suite complète demandée | Interrompue : 14 erreurs de collecte, principalement `libomp.dylib` manquante et Evidently absent de l'installation par défaut |
| Sous-ensemble auth/collecte/initialisation/predict/DAG/présentation | 65 réussis, 3 échoués, 27 avertissements; confirmé avec cache Python neuf |
| `tests/train_api_v2` dans l'image Linux active, dépôt en lecture seule | 146 réussis, 23 avertissements; confirmé avec cache Python neuf |
| Health HTTP MLflow, quatre API, Grafana, Prometheus, trois exporters | HTTP 200 |
| Auth directe et via proxy de l'interface | HTTP 200, jeton exploitable, jamais affiché |
| Train/collecte/proxy predict sans jeton | HTTP 401 |
| Première prédiction avec volume BentoML vide | HTTP 503 attendu jusqu'à publication d'un modèle |
| Synchronisation du champion existant et rechargement | Réussi; prédiction directe et proxy HTTP 200, source `remote_api` |
| Prometheus `/api/v1/targets` | Six cibles `up` : exporters drift/carbon/ML, predict, node-exporter, cAdvisor |
| Airflow UI, liste des DAGs et import-errors | HTTP 200; aucun import-error; deux DAGs projet présents et pausés |
| Loki `/ready` depuis son conteneur | Réussi; port 3100 non publié sur l'hôte, donc test local direct indisponible par conception |
| `alloy validate` | Réussi syntaxiquement; labels Loki vides, filtre projet incorrect |
| Statuts et logs, échantillon des 300 dernières lignes par service | Aucun redémarrage; anomalies et avertissements ci-dessous |

Les tests Linux ont installé pytest/httpx uniquement dans un conteneur éphémère. Aucun dependency manifest du dépôt modifié.

## Anomalies préexistantes et limites

1. **Alloy** : filtre `projet_accidents_mlops/...` alors que les labels Compose réels utilisent `projet_accidents_mlops_liora`. La syntaxe passe mais les API ne sont pas sélectionnées. Loki est prêt sans labels collectés.
2. **cAdvisor** : cible HTTP accessible, mais logs d'échec de connexion Docker et de détection des runtimes. Une cible `up` ne garantit pas les métriques par conteneur sur Docker Desktop. À corriger ou documenter selon la plateforme, puis contrôler la présence réelle de métriques.
3. **Tests existants** : test JWT expiré utilise une clé absente; test DAG attend `schedule=None` alors que le DAG est planifié le lundi; test slide attend un texte remplacé. Ne pas changer la fonctionnalité pour satisfaire des assertions obsolètes.
4. **Environnement Python** : OpenMP absent sur macOS; Evidently est un extra absent de `uv sync` par défaut; BentoML local 1.3.22 diffère des images actives 1.4.39. Les 146 tests Linux permettent de vérifier le backend avec ses dépendances runtime.
5. **Interface** : logs serveur/client contenant payload d'auth et réponse avec jeton; aucune copie de ces logs sensibles dans la documentation. Prévoir leur retrait ciblé. En cas d'exception réseau, auth peut rester sans réponse et predict peut basculer sur un score heuristique : vérifier explicitement `remote_api` pour le smoke.
6. **npm** : build réussi, mais npm signale 13 vulnérabilités (dont une critique) pour l'ensemble, et trois (dont une critique) pour les dépendances de production. Pas de mise à jour automatique ou `audit fix --force` durant l'inventaire. Bundle Vite supérieur à 500 kB.
7. **Avertissements runtime** : cAdvisor Docker Desktop, ring Loki temporairement vide au démarrage, contention SQLite Grafana transitoire, configuration Celery visibility timeout par défaut et dépréciations Python/Streamlit. Aucun crash de service observé.
8. **Persistance** : le Docker était vide, mais les bind mounts MLflow contenaient déjà un champion. Ce test n'est pas une initialisation sur stockage entièrement vierge. La recette existante `runtime-dirs` a créé les répertoires et adapté les droits, comportement actuel non modifié.
9. **Workflows mutateurs** : aucun nouvel entraînement complet, collecte distante ou run hebdomadaire déclenché. Le DAG appelle réellement `git commit` et `git push` après DVC : incompatible avec la consigne sans commits sur ce checkout. La validation finale devra utiliser un checkout/remote de test isolé ou un chemin de test sans publication Git; ne pas activer les DAGs sur le dépôt utilisateur.
10. **Sauvegarde** : 393 fichiers de source/configuration/docs sauvegardés et vérifiés par SHA-256 dans `/private/tmp/accidents-cleanup-baseline-2026-10-13/source.tar.gz`, avec `manifest.json`. Secrets locaux, datasets et état persistant exclus. Sauvegarde temporaire : revérifier sa disponibilité avant suppression; sauvegarder séparément tout candidat non inclus. Les outils personnels d'agents sont conservés.

## Suite

L'inventaire et les tests de référence sont effectués, avec limites explicites. Ajouter une étape corrective avant les suppressions pour rétablir la collecte des logs, fiabiliser les vérifications préexistantes et qualifier les métriques cAdvisor. Ne pas considérer le nettoyage terminé tant que l'initialisation vierge et les workflows complets n'ont pas été validés dans un environnement isolé.

## Bilan après nettoyage

Les décisions initiales ont été exécutées par lots sauvegardés et validés. Les anciens noms de modules/services sont retirés des chemins actifs ; noms physiques de persistance conservés volontairement. Liste détaillée : cleanup-files.json et manifests par étape. Documentation classée dans documentation-audit.json. Validation finale sur stockage vierge, entraînements initial/hebdomadaire, DVC local et prédiction réelle : validation-stack.md, validation-weekly.json et validation-7.json. Git/DVC distant, Slack et monitoring cAdvisor par conteneur restent explicitement limités ; aucun commit automatique.
