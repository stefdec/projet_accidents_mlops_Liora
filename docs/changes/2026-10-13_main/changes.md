## Inventaire et vérification de la stack avant nettoyage

**Message de commit**

`docs(audit): document active dependencies and stack baseline`

Message enregistré pour la traçabilité uniquement. Aucun commit avant la fin du nettoyage et des tests, conformément à la consigne utilisateur.

**Ce qui a changé**

- Plan mis à jour : `emergency-interface` obligatoire au démarrage et aux validations, aucun commit intermédiaire, étape corrective 1 bis avant les suppressions.
- Ajout d'un audit des dépendances directes/indirectes, d'un inventaire de 393 fichiers avec imports et empreintes, et d'un état runtime sans contenu sensible des logs.
- Sauvegarde temporaire des 393 fichiers de source/configuration/documentation vérifiée par SHA-256. Aucun fichier applicatif modifié ou supprimé.

**Pourquoi**

- Établir une référence réelle avant nettoyage, distinguer les composants actifs des candidats historiques et préserver les fichiers non suivis par Git.
- BentoML, DVC et le package sous `src/train_api/utils` restent nécessaires; leur suppression globale casserait le fonctionnement ou les builds.
- Les défauts préexistants doivent être distingués des régressions introduites par les prochains lots.

**Fichiers**

- `docs/changes/2026-10-13_main/plan.md`
- `docs/changes/2026-10-13_main/audit.md`
- `docs/changes/2026-10-13_main/inventory.json`
- `docs/changes/2026-10-13_main/runtime-baseline.json`
- `docs/changes/2026-10-13_main/changes.md`

**Validation**

- Quatre Compose validés avec `config --quiet`; `uv sync --frozen` réussi. Aucun outil de lint/format configuré trouvé dans `pyproject.toml`.
- Build et démarrage réels de la stack via `make -f makefile2.mk stack-up`; build et lancement séparés d'`emergency-interface`. 23 conteneurs permanents sans redémarrage observé; jobs d'initialisation sortis avec code 0.
- Tests `train-api-v2` dans son image Linux : 146 réussis, y compris répétition avec cache Python neuf.
- Tests auth/collecte/initialisation/predict/DAG/présentation sur macOS : 65 réussis et 3 échecs préexistants, confirmés avec cache neuf. Suite train locale bloquée à la collecte par OpenMP absent et Evidently non installé par défaut.
- Auth, API health, MLflow, Airflow, Grafana, Prometheus, exporters et Streamlit contrôlés par HTTP. Aucun import-error Airflow; DAGs laissés pausés.
- Champion MLflow existant publié vers le nouveau volume BentoML puis rechargé : prédiction directe et via interface HTTP 200, source `remote_api`. Premier 503 lié au volume BentoML vide, sans crash de service.
- Six cibles Prometheus disponibles, mais métriques cAdvisor par conteneur non validées (connexion Docker en erreur). Loki prêt et configuration Alloy syntaxiquement valide, mais collecte API absente à cause du filtre projet incorrect.
- Présentation : génération des huit pages avec dix images et quatre polices; AppTest en timeout, vérification navigateur complète restant à effectuer.
- Audit des sorties npm : vulnérabilités signalées et avertissement de taille du bundle, consignés sans mise à jour des dépendances.
- Comparaison avec la sauvegarde : seul le plan préexistant a changé; les autres fichiers de ce lot sont nouveaux. Arrêt propre de la stack de test sans suppression des volumes/données.
- Limites : pas de nouvel entraînement initial complet, de collecte distante, de notification Slack ou de DAG hebdomadaire déclenché. Le DAG crée/pousse des commits : sa validation complète devra être isolée du dépôt utilisateur. Données MLflow préexistantes conservées; ce test ne remplace pas une initialisation vierge.

## Planifier le renommage des API actives

**Message de commit**

`docs(plan): add active API rename migration`

**Ce qui a changé**

- Ajout de l’étape 4 bis : `predict_api_v2` devient `predict_api` et `train_api_v2` devient `train_api`, avec renommage des services Compose et mise à jour des références actives.
- Prévision du retrait préalable des anciennes implémentations occupant les noms cibles, conservation du package partagé et contrôle des modèles sérialisés et de la persistance.
- Rappel qu’aucun commit intermédiaire ne sera créé; « preduct_api » interprété comme `predict_api`.

**Pourquoi**

- Appliquer la nomenclature finale demandée sans écraser les fichiers existants ni perdre les modèles, données ou contrats API.

**Fichiers**

- `docs/changes/2026-10-13_main/plan.md`
- `docs/changes/2026-10-13_main/changes.md`

**Validation**

- Branche et état Git inspectés; chemins cibles, imports, packaging, Compose, URLs et stockage examinés.
- Plan relu pour l’ordre nettoyage → renommage → vérification de la stack. Aucun code renommé à ce stade, aucun test runtime nécessaire pour cette modification documentaire.

## Fiabiliser les contrôles de référence et la collecte des logs

**Message de commit**

`fix(stack): restore baseline checks and observability`

Message enregistré uniquement; aucun commit intermédiaire créé.

**Ce qui a changé**

- Les API portent le label `org.accidents.stack=api`; Alloy sélectionne ce label et le service Compose, indépendamment du nom du dossier ou du projet.
- Les logs d’authentification contenant identifiants, mot de passe et jeton ont été retirés du serveur et du client de l’interface, sans changer leurs réponses HTTP.
- Fixtures JWT adaptées aux clés distinctes login/train, avec contrôle que le jeton login ne peut pas recharger le modèle. Tests du DAG et des slides alignés sur l’horaire et le contenu actuels, en normalisant les espaces du texte HTML.
- Socket cAdvisor monté en lecture seule sur `/docker.sock` avec endpoint explicite, hors du montage `/var/run` en lecture seule.
- Guides Loki corrigés, guide de validation locale ajouté et référencé dans l’index; plan actualisé avec les résultats et limites.

**Pourquoi**

- Le filtre Alloy précédent excluait les API sur ce clone. Les tests comportaient des attentes obsolètes et les logs de l’interface exposaient des données d’authentification.
- Le montage du répertoire `/var/run` ne raccordait pas le socket Docker Desktop. Le montage explicite corrige cette connexion sans modifier ports, volumes persistants, interfaces publiques ou authentification.
- Le backend de stockage `overlayfs` présente une autre incompatibilité cAdvisor : ne pas confondre la disponibilité HTTP avec une collecte complète des conteneurs.

**Fichiers**

- `docker-compose.apis.yml`
- `docker-compose.monitoring.yml`
- `monitoring/alloy/config.alloy`
- `interface/server.js`
- `interface/src/services/predictionService.js`
- `tests/test_predict_api_v2_service.py`
- `src/airflow_dags/tests/test_pull_train.py`
- `app/pres-sl/tests/test_slides_05_08.py`
- `docs/loki/README.md`
- `docs/operations/logs-loki-alloy.md`
- `docs/operations/local-validation.md`
- `docs/operations/README.md`
- `docs/changes/2026-10-13_main/plan.md`
- `docs/changes/2026-10-13_main/validation-1bis.json`
- `docs/changes/2026-10-13_main/changes.md`

**Validation**

- Tests ciblés auth/collecte/initialisation/predict/DAG/présentation et configuration monitoring : 70 réussis, 27 avertissements, cache Python neuf. Les trois échecs de référence sont résolus.
- Quatre Compose validés avec `config --quiet`; `alloy validate` réussi. Aucun outil de lint/format configuré trouvé pour les composants modifiés.
- Images de la stack et de l’interface reconstruites; `make -f makefile2.mk stack-up` réussi. Un premier essai de montage imbriqué du socket cAdvisor a échoué; le montage final `/docker.sock` évite ce conflit.
- 23 conteneurs permanents démarrés, aucun redémarrage observé. Endpoints MLflow, API, Airflow, Grafana, Prometheus, exporters, interface et Streamlit HTTP 200; aucun import-error Airflow.
- Authentification via interface et prédictions directe/proxy HTTP 200, proxy `status=remote_api`; appels sans jeton refusés avec HTTP 401.
- Loki contient des logs récents des quatre API. Six cibles Prometheus `up`. Mot de passe et jeton employés au smoke absents des logs serveur de l’interface; aucune valeur sensible sauvegardée dans les résultats.
- cAdvisor connecté au daemon, mais requêtes CPU/mémoire de conteneurs nommés retournant zéro série. L’essai d’exclusion disque n’a pas résolu ce défaut sur ce Docker Desktop/overlayfs; option expérimentale retirée. Limite documentée, pas de changement du daemon ni suppression de son stockage.
- Diff des fichiers couverts par la sauvegarde revu; modifications du test predict relues séparément (les tests racine ne figuraient pas dans cette sauvegarde). Aucun fichier applicatif supprimé, aucun renommage.
- Arrêt propre des services de validation sans suppression des volumes. Les limites initialisation vierge, entraînement complet, collecte distante, notifications et DAG avec commits/push restent celles de l’audit initial.

## Migration du point d’entrée Make

**Message de commit**

`refactor(make): unify active stack orchestration`

**Ce qui a changé**

- Makefile reprend la stack de référence, inclut emergency-interface et propose présentation, état, logs, arrêt sans destruction et smoke de prédiction actif.
- Monitoring démarré une seule fois ; bootstrap construit avant exécution ; ordre MLflow → monitoring → API/interface → bootstrap → Airflow conservé pour init.
- Procédures actives et tests adaptés. Archives identifiées, sorties historiques conservées. Ancien makefile supprimé après sauvegarde vérifiée et validation.

**Pourquoi**

- Remplacer les deux orchestrations contradictoires par une commande cohérente ; permettre une vérification complète à chaque nettoyage.

**Fichiers**

- `Makefile`, `makefile2.mk` (supprimé), `scripts/predict_api_smoke_test.py`, `tests/train_api_v2/test_compose_service.py`
- `README.md`, `README_monitoring.md`, procédures dans `docs/operations`, `docs/loki` et `docs/refactor/train_api` ; commandes dans deux anciennes présentations.
- `docs/changes/2026-10-13_main/plan.md`, `validation-2.json`, `files-2.json`

**Validation**

- 78 tests ciblés réussis (27 avertissements existants) ; 9 tests Make/smoke rejoués avec succès après ajustements.
- Quatre Compose config --quiet valides ; help, simulations stack-up/init/reset-full, état et logs vérifiés. Aucun reset exécuté.
- Build et stack-up réels réussis : 23 services stables, prédiction API/interface remote_api, présentation, six cibles Prometheus up, logs Loki des quatre API, zéro erreur d’import DAG. make predict-smoke réussi. Aucune valeur sensible configurée détectée dans les logs inspectés.
- Premier bootstrap après stack complète : OOM sur Docker 8 Go, sortie 137 et deux redémarrages ; essai avant Airflow interrompu pendant training. Après passage à 16 Go par l’utilisateur : make init réussi, run MLflow enregistré, champion existant conservé, synchronisation BentoML et reload réussis. Replay initial-train idempotent : même run, sans nouvel entraînement. État SQLite succeeded (trois retries après interruptions), zéro redémarrage durant la validation finale.
- Tests Make/smoke rejoués après suppression de makefile2.mk : 9 réussis. Contrôle final et predict-smoke après reload réussis. Arrêt non destructif par make stack-down et SIGINT de la présentation ; conservation des volumes vérifiée. Aucun DAG mutateur lancé.
- Limite cAdvisor Docker Desktop toujours présente (pas de métriques de conteneurs nommés). Stockage vierge et workflow DVC/Git réservés à la validation isolée finale ; DAGs laissés pausés.
- Sauvegarde vérifiée du lot : `/private/tmp/accidents-cleanup-step2-2026-10-13`. Pas de commit ; étape 2 terminée. Aucun lint/format configuré pour ce lot. Le stockage MLflow contient un candidat supplémentaire issu du test ; champion et datasets conservés.

## Retrait des applications remplacées

**Message de commit**

`chore(apps): remove verified obsolete applications`

**Ce qui a changé**

- Retrait des cinq anciennes apps Streamlit, lanceurs, tests et assets exclusifs ; présentation pres-sl et emergency-interface conservées. Guides OCS, script smoke OCS et contexte produit de l’ancienne présentation retirés.
- Correction du lanceur app-pres.py : ne plus interrompre Streamlit avec SystemExit ; sortie du processus autonome conservée. Test de régression du rendu des huit pages ajouté.

**Pourquoi**

- Aucun import, COPY ou montage des apps supprimées dans la stack active ; assets actifs tous locaux à pres-sl. SystemExit empêchait la fin du run de présentation (AppTest échouait à 3 puis 20 s avant correction).

**Fichiers**

- `app-pres.py`, `app/pres-sl/tests/test_entrypoint.py`, `README.md`, `docs/applications/README.md`, `tests/test_docker_architecture.py`.
- Liste exhaustive des suppressions et empreintes : `files-step3.json` ; sauvegarde vérifiée `/private/tmp/accidents-cleanup-step3`.

**Validation**

- 14 tests présentation/bootstrap/smoke réussis ; après correction, 3 tests présentation réussis, huit pages et ressources embarquées rendues sans exception. Avertissement Streamlit iframe déprécié conservé.
- Quatre Compose valides ; build et stack-up réussis ; 23 services stables, interface remote_api, endpoints, six cibles Prometheus, logs Loki, aucun import-error Airflow (`validation-3.json`).
- Stack et présentation arrêtées sans suppression de volumes. Aucun commit. Browser CUA indisponible : pas de contrôle visuel par navigateur ; AppTest et document HTML vérifiés.

## Retrait du backend remplacé et mutualisation des DAGs

**Message de commit**

`chore(backend): remove verified obsolete services and workflows`

**Ce qui a changé**

- Anciennes API train/predict, training CLI/pipeline, monitoring historique, migrations ponctuelles et tests exclusifs retirés. Préparation DVC conservée.
- Package partagé limité aux snapshots hebdomadaires et aux classes features/modeling conservées pour compatibilité des artefacts ; nom Python et packaging inchangés.
- Fonctions métier des DAGs mutualisées dans accidents_workflow.py ; identifiants, horaires, compteur de simulation et contrats inchangés. Suppression du print du JWT dans le DAG de simulation.
- Tests des deux DAGs et assertions du dashboard Grafana adaptées au schéma v2 réellement présent (défaut d’assertion préexistant).

**Pourquoi**

- API actives autonomes remplacent les sous-processus et ancienne stack. Les deux DAGs restent utiles mais leur code métier était dupliqué. DVC et les artefacts sérialisés restent des dépendances indirectes réelles.

**Fichiers**

- `src/train_api`, `src/predict_api` (ancienne API retirée), `pipeline`, `monitoring`, `scripts`, `tests`, `README_PIPELINE.md`, `src/airflow_dags/dags`, tests Airflow.
- Liste exhaustive : `files-step4.json` ; sauvegarde vérifiée `/private/tmp/accidents-cleanup-step4`.

**Validation**

- 115 tests locaux réussis ; Linux : 159 tests backend/compatibilité/snapshot réussis, 1 skip (GNU Make absent de l’image runtime), 23 avertissements existants.
- Build et stack-up réussis ; bootstrap idempotent et champion existant rechargé ; 23 services sans redémarrage, prédiction API/interface remote_api, monitoring et DAGs vérifiés (`validation-4.json`).
- Intégration hebdomadaire réelle déplacée explicitement à l’étape 7 dans la copie isolée : pas de modification du champion/datasets utilisateur ni de commits/push. Contrats des deux DAGs testés ici avec opérations Git simulées.
- Stack et présentation arrêtées sans reset, aucun commit. Limites cAdvisor et dépréciations conservées.

## Renommage des API actives

**Message de commit**

`refactor(api): rename active training and prediction services`

**Ce qui a changé**

- Modules actifs déplacés vers src/train_api et src/predict_api ; package utils conservé. Services Compose, nom du conteneur train, DNS, imports, config, DAGs, interface, monitoring, tests et guides actifs mis à jour. Dashboard de prédiction et guide opérationnel renommés.
- Ports, endpoints, contrats, JWT et paramètres ML inchangés. Volume physique train_api_v2_state et bind data/train-api-v2 conservés : aucun reset/migration de données.

**Pourquoi**

- Noms demandés par l’utilisateur après retrait des anciennes implémentations, sans casser les dépendances ou l’état existant.

**Fichiers**

- `src/train_api`, `src/predict_api`, `tests/train_api`, `tests/test_predict_api_service.py`, Makefile, Compose, interface, monitoring, documentation.
- Déplacements et empreintes détaillés : `files-step4bis.json` ; sauvegarde vérifiée `/private/tmp/accidents-cleanup-step4bis`.

**Validation**

- 115 tests locaux réussis ; 159 tests Linux réussis, 1 skip (Make absent), 23 avertissements. Assertions interdisant l’ancien nom désormais actif adaptées sans enlever les contrôles d’isolement des outils legacy.
- Quatre Compose valides ; build/démarrage des nouvelles images ; initial-train idempotent, état SQLite et champion existant compatibles, import MLflow → BentoML et reload réussis. Les anciens modèles embarquent leur code src.train_api_v2 : aucun module de compatibilité supplémentaire nécessaire après test réel.
- 23 services stables, nouvelles étiquettes Loki train-api/predict-api, nouvelle cible Prometheus predict_api, prédiction API/interface remote_api, présentation, zéro import-error Airflow (`validation-4bis.json`). Les anciens labels Loki restent dans les données historiques conservées.
- Arrêt non destructif, aucun commit ; nouveau modèle depuis les nouveaux imports à vérifier dans la copie isolée finale.

## Réduction des configurations et de l’image des exporters

**Message de commit**

`chore(config): remove unused configuration and build artifacts`

**Ce qui a changé**

- Image racine limitée au code exporters et au groupe verrouillé exporters ; lancement uvicorn direct, plus de copie globale ni de synchronisation/installation de toute la stack au runtime. Ports, commandes métier et montages conservés.
- BentoML local aligné sur 1.4.39 ; category-encoders, shim dotenv et st-tailwind sans consommateurs retirés ; dvc-s3 conservé transitivement via dvc[s3]. httpx2 conservé après vérification de l’usage indirect Starlette TestClient. Lockfile régénéré.
- Requirements racine vide et doublon Streamlit retirés ; paramètres train/registry historiques et exemples d’environnement sans consommateurs retirés ; déclaration shared-api-data non montée supprimée, volume physique non détruit.
- Contextes Docker/règles Git précisés, CSV carbone et configuration Airflow locale potentiellement sensible ignorés (fichiers existants conservés) ; 40 racines de caches/DS_Store régénérables retirées, sans toucher aux données ni aux outils personnels.

**Pourquoi**

- Les trois exporters n’utilisent que FastAPI, uvicorn, pandas et prometheus-client ; la copie complète embarquait code et dépendances inutiles. Une seule source verrouillée reste utilisée par les développeurs et ces images.

**Fichiers**

- `Dockerfile`, `docker-compose.monitoring.yml`, `docker-compose.apis.yml`, `pyproject.toml`, `uv.lock`, `params.yaml`, `.env.example`, `.dockerignore`, `.gitignore`.
- Requirements retirés, détails et empreintes : `files-step5.json` ; sauvegarde `/private/tmp/accidents-cleanup-step5`.

**Validation**

- uv lock et uv sync --frozen --extra monitoring réussis ; 115 tests locaux réussis (25 avertissements).
- Quatre Compose valides ; builds, démarrage et rebuild du monitoring avec le lock final réussis. Image exporters 410 048 944 octets, 20 distributions runtime, absence vérifiée de MLflow/BentoML/DVC/Streamlit/LightGBM.
- Stack : 23 services stables, endpoints et interface remote_api, six cibles Prometheus, Loki et DAGs (`validation-5.json`). Arrêt propre, volumes conservés, aucun commit.
- Avertissement uv sur version du build backend conservé (build néanmoins réussi), dépréciations Python/Streamlit et limite cAdvisor connues.

## Consolidation de la documentation actuelle

**Message de commit**

`docs(project): align documentation with the active stack`

**Ce qui a changé**

- README réécrit : architecture réelle, prérequis/16 Go, installation, init/arrêt, API/JWT, deux DAGs, préparation DVC, persistance, monitoring, resets et structure utile.
- Guides training/predict/bootstrap/Airflow/monitoring et index consolidés ; documentation DVC extraite, guide orchestration renommé, liens et libellés de présentation actualisés. Titres/log de bootstrap corrigés pour refléter le jeton train du reload.
- Archives de refactor, audit propre à une machine, brouillon Airflow et guides legacy redondants retirés après sauvegarde. Journaux docs/changes conservés. Classification complète dans documentation-audit.json.
- Configuration Airflow générée contenant des clés runtime désormais ignorée par Git (fichier local conservé, rattachement au lot configuration), sauvegardes privées protégées sans divulgation des valeurs.

**Pourquoi**

- Une source d’exploitation cohérente avec le code actif ; supprimer les instructions de composants retirés et préserver les prérequis DVC/persistance utiles.

**Fichiers**

- `README.md`, `README_monitoring.md`, index et guides docs, `app/pres-sl/README.md`, template démonstration, README MLflow, `interface/rapport.md`, titre train-api/log initial-train.
- Liste complète : files-step6.json ; audit documentaire et sauvegarde `/private/tmp/accidents-cleanup-step6`.

**Validation**

- Aucun lien local manquant dans les guides actuels (journaux historiques exclus), help et procédures actives cohérents. 69 tests ciblés réussis, 23 avertissements existants.
- Quatre Compose valides ; builds/stack-up et présentation depuis les commandes du README ; prédiction réelle API/interface, 23 services stables, six cibles, logs Loki, aucun import-error Airflow (`validation-6.json`). Smoke final réussi, arrêt sans reset.
- Consigne sans commits respectée ; calendrier simulation, Git/DVC mutateurs, captures illustratives, cAdvisor et limites de validation explicités.

## Réconcilier le Makefile restauré et isoler le test d’authentification

**Message de commit**

`fix(validation): align restored orchestration and isolate auth test`

**Ce qui a changé**

- Recettes réconciliées avec le point d’entrée validé : noms train/predict actuels, aucun appel à makefile2.mk, emergency-interface et commandes documentées incluses.
- Création de data/incoming avant le réglage des droits sur installation vierge ; volumes physiques conservés.
- Test du jeton valide isolé par un stub de service, vérifiant explicitement que la requête atteint l’entraînement.

**Pourquoi**

- Le Makefile remis contenait les noms et appels antérieurs au nettoyage. Le test d’authentification dépendait du .env ambiant et attendait une erreur différente selon les données disponibles.

**Fichiers**

- `Makefile`
- `tests/train_api/test_auth.py`
- `docs/changes/2026-10-13_main/plan.md`

**Validation**

- make help et simulation stack-up ; 8 tests locaux architecture/smoke réussis.
- Suite Linux : 261 passed, 1 skipped (Make absent de l’image), 46 warnings.
- make stack-up réel dans la copie isolée : 23 services stables, prédiction API/interface et logs validés. Diff comparé à la sauvegarde étape 7 et Makefile utilisateur sauvegardé séparément.
- Collecte ML locale macOS bloquée par OpenMP ; tests ML effectués sous Linux. Aucun reset, commit ou push.

## Vérification finale sur stockage vierge et bilan du nettoyage

**Message de commit**

`docs(validation): record clean stack verification results`

**Ce qui a changé**

- Bilan architecture, suppressions/déplacements/modifications, éléments conservés et limites ; manifests consolidés et comparaison des sources initiales.
- Plan et audit clôturés avec résultats mesurés et limites explicites.

**Pourquoi**

- Prouver la reconstruction et l’utilisation de la base nettoyée sans toucher aux données existantes, et rendre les décisions reviewables malgré un dépôt non suivi.

**Fichiers**

- `docs/changes/2026-10-13_main/validation-stack.md`
- `docs/changes/2026-10-13_main/cleanup-files.json`
- `docs/changes/2026-10-13_main/baseline-files.json`
- `docs/changes/2026-10-13_main/validation-7.json`
- `docs/changes/2026-10-13_main/validation-7-restart.json`
- `docs/changes/2026-10-13_main/validation-weekly.json`
- `docs/changes/2026-10-13_main/validation-tests.json`
- `docs/changes/2026-10-13_main/validation-shutdown.json`
- `docs/changes/2026-10-13_main/audit.md`
- `docs/changes/2026-10-13_main/plan.md`

**Validation**

- make install/init/stack-up réussis dans copie isolée, stockage vierge ; modèle neuf enregistré, publié dans BentoML et rechargé.
- DAG pull_weekly success : collecte distante, DVC local réel, entraînement hebdomadaire ; champion initial conservé via skip_deployment.
- 261 tests Linux réussis, 1 skip, 46 warnings ; 8 tests locaux architecture/smoke réussis. ML local macOS limité par OpenMP.
- 23 services stables avant/après arrêt-redémarrage, prédictions API/interface réelles, six cibles Prometheus up, quatre services dans Loki, zéro import-error Airflow ; présentation testée.
- Arrêt final réussi : aucun conteneur restant, tous les volumes préexistants conservés. Aucun reset, commit ou push.
- Limites : cAdvisor Docker Desktop sans métriques par conteneur, contrôle visuel navigateur indisponible, Git/DVC distant et Slack non testés. Vulnérabilités npm connues inchangées, consignées séparément.

## Aligner le modèle d’environnement et protéger les contextes locaux

**Message de commit**

`chore(config): align environment template and ignore rules`

**Ce qui a changé**

- .env.example reproduit les 50 variables du .env et leur ordre, avec valeurs publiques ou placeholders ; identités Git, comptes des jobs et clé d’idempotence ajoutés. Variables historiques non lues explicitement signalées.
- Deux anciens noms DNS corrigés uniquement dans le .env local ignoré : train-api et predict-api. Toutes les autres valeurs, dont les secrets, préservées.
- Exclusions Docker complétées pour .env.*, caches, logs et configuration Airflow sensible ; quatre contextes de services auparavant sans .dockerignore protégés. .dvc entier exclu du contexte racine, sans changer les montages runtime DVC.
- Git exclut caches Ruff/Mypy et configuration AWS locale. DVC exclut secrets, dépendances, caches et états applicatifs, tout en conservant datasets et sorties déclarés dans dvc.yaml.

**Pourquoi**

- L’exemple incomplet ne reflétait pas le fichier local ; certains contextes, notamment le COPY global de l’interface, pouvaient embarquer des .env locaux. Les anciennes URLs locales auraient cassé les appels des DAGs après renommage.

**Fichiers**

- `.env.example`, `.env` (local ignoré, deux URLs uniquement)
- `.dockerignore`, `.gitignore`, `.dvcignore`
- `interface/.dockerignore`
- `src/train_api/.dockerignore`, `src/inital_train/.dockerignore`
- `src/auth_api/.dockerignore`, `src/pull_data_api/.dockerignore`
- `src/predict_api/.dockerignore`, `src/airflow_dags/.dockerignore`
- `docs/changes/2026-10-13_main/plan.md`

**Validation**

- 50 clés dans le même ordre ; placeholders vérifiés sans exposer les secrets. Quatre Compose valides avec .env.example ; Airflow Compose valide avec les URLs locales corrigées.
- git check-ignore et dvc check-ignore : secrets/états exclus, exemple et fichiers utiles conservés. Datasets raw/features/incoming et reports/snapshot_manifest.json accessibles à DVC.
- Sept builds de contrôle avec sentinelle non sensible .env.* : sentinelle exclue et fichiers requis présents ; sources nécessaires COPY conservées.
- 11 tests ciblés réussis ; reconstruction et make stack-up dans la copie isolée réussis. 23 services stables, zéro redémarrage, prédiction réelle API/interface, logs Loki et zéro erreur d’import Airflow.
- Diff complet revu avec sauvegarde des configurations publiques, manifests et résultats dans files-step8.json, validation-ignore.json, validation-8.json. Aucun commit.

- Arrêt final confirmé : aucun conteneur restant, tous les volumes présents avant cette validation conservés.

## Mettre le README en phase avec la configuration finale

**Message de commit**

`docs(readme): reflect current setup and validation results`

**Ce qui a changé**

- README complété : variables de l’exemple, DNS interne actuel, surcharges Make, configuration DVC séparée et exclusions Git/Docker/DVC.
- Activation volontaire des DAGs et portée de make metrics clarifiées ; résultats mesurés et limites reliés au bilan daté.
- Index docs relié à l’exemple et à la validation finale.

**Pourquoi**

- Les derniers changements d’environnement/exclusions et la fin des validations n’étaient pas intégrés à la documentation de démarrage. Les valeurs Make exportées pouvaient être confondues avec celles du .env.

**Fichiers**

- `README.md`
- `docs/README.md`
- `docs/changes/2026-10-13_main/plan.md`

**Validation**

- Liens locaux et cibles Make valides ; make help exécuté, simulations install/presentation/predict-smoke réussies.
- Commandes, paramètres, noms, pauses DAG, persistance et exclusions confrontés aux sources actuelles ; diff documentaire revu.
- Aucun code/config runtime modifié : aucun nouveau test ML ni démarrage pour ce lot ; résultats de l’étape 8 explicitement référencés, pas présentés comme rejoués.
- Résultats/manifests : validation-readme.json et files-step9.json. Aucun commit.

## Établir et publier la base propre du dépôt

**Message de commit**

`chore: establish clean repository baseline`

**Ce qui a changé**

- Base nettoyée rassemblée dans un commit unique initial, explicitement demandé par l’utilisateur après les validations ; publication sur main sans force.
- Les messages proposés par étape restent des repères de travail, remplacés pour ce commit global par le message demandé.

**Pourquoi**

- Établir un état de référence versionné, cohérent et validé du dépôt ; aucun commit intermédiaire n’avait été créé.

**Fichiers**

- Sources, interfaces, configuration, tests, documentation et métadonnées DVC déjà indexés.
- `docs/changes/2026-10-13_main/plan.md`
- `docs/changes/2026-10-13_main/changes.md`

**Validation**

- Branche locale main, sans commit initial ; aucune branche main distante présente lors du contrôle.
- 420 fichiers indexés contrôlés : aucun secret local détecté, aucune signature de credential dans les textes, aucun fichier supérieur à 50 Mo. .env/config.local/configuration Airflow sensibles exclus.
- Validations applicatives antérieures : 261 tests Linux réussis, 1 skip ; 11 tests de configuration réussis, reconstruction et 23 services stables, prédiction réelle et workflow hebdomadaire. Limites conservées dans validation-stack.md.
- Diff documentaire et index inspectés ; pas de nouveau changement runtime dans cette opération de publication.
