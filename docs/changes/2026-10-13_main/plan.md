# Plan d'implémentation

## Objectif

Nettoyer progressivement le dépôt, faire de `Makefile` son point d'entrée principal et conserver une stack fonctionnelle après chaque étape. Aucune suppression ne sera fondée uniquement sur un nom ou une absence de référence directe.

## Contexte

Analyse initiale effectuée le 13 octobre 2026 sur la branche `main`, depuis `makefile2.mk` et ses Compose, Dockerfiles, DAGs, modules Python et configurations de packaging.

- `makefile2.mk` orchestre MLflow/PostgreSQL, les API auth/collecte/train v2/predict v2, Airflow et le monitoring. Il contient des appels récursifs à lui-même et démarre deux fois le monitoring.
- Le `Makefile` existant décrit une autre orchestration : anciennes API, application OCS et pipeline DVC. Il ne doit pas simplement être conservé tel quel.
- `app-pres.py` charge `app/pres-sl/app.py`, puis les composants, pages, templates, styles, images et polices de ce dossier. Son lancement n'est pas intégré à `makefile2.mk`.
- BentoML reste utilisé par la prédiction, l'initialisation et les DAGs. DVC reste utilisé par Airflow. Leur suppression globale serait incorrecte.
- `src/train_api/utils/projet_accidents_mlops` est le package déclaré dans `pyproject.toml`; le pipeline et des tests l'importent. L'ancienne API et ce package doivent être évalués séparément.
- `emergency-interface` est confirmé actif par l’utilisateur : il doit être conservé, lancé et testé avec la stack, y compris authentification et prédiction sur le port 3001. Il est actuellement absent du démarrage explicite de `makefile2.mk`.
- Les deux DAGs `pull_train.py` et `pull_weekly.py` doivent être comparés, y compris leurs identifiants, horaires et usages opérationnels.
- La documentation contient des descriptions de plusieurs architectures.
- `git ls-files` ne retourne aucun fichier et `git status` présente le dépôt comme non suivi. Git ne constitue donc pas actuellement une sauvegarde des fichiers à supprimer.

Cette première analyse sert à définir les étapes. L'inventaire exhaustif et les preuves de suppression sont le livrable de l'étape 1, avant tout nettoyage.

## Périmètre

### Inclus

- Dépendances directes et indirectes de la stack, application de référence, initialisation, entraînement, prédiction, monitoring, données, packaging et éventuelle CI.
- Nettoyage par lots cohérents, documentation et vérification réelle après chaque lot.
- Conservation des contrats API, ports, données et mécanismes de persistance actuels.

### Hors périmètre

- Refactorisation fonctionnelle, remplacement de BentoML/DVC ou redesign de l'interface.
- Suppression des datasets, modèles utiles, secrets locaux et états persistants existants.
- Commits et push automatiques, modification opportuniste de composants indépendants.

## Modalités confirmées par l’utilisateur

- `emergency-interface` appartient à la stack obligatoire, au même titre que les API et services d’infrastructure.
- Renommer les API actives : `src/predict_api_v2` → `src/predict_api` et `src/train_api_v2` → `src/train_api`, ainsi que les services Compose `predict-api-v2` → `predict-api` et `train-api-v2` → `train-api`. « preduct_api » est interprété comme une faute de frappe pour `predict_api`.
- Aucun commit ne sera créé avant la fin du nettoyage et des tests. Les messages ci-dessous servent uniquement à la traçabilité des unités logiques.
- Toutes les étapes restantes sont autorisées par l’utilisateur ; les exécuter séquentiellement avec leur validation, sans commit.

## Protocole de validation commun à chaque étape

1. Inspecter branche, état Git et diff; enregistrer précisément les fichiers modifiés/supprimés. Pour les fichiers non suivis, comparer avec une sauvegarde vérifiée : `git diff` seul est insuffisant.
2. Exécuter les tests du lot et les contrôles de format/lint réellement configurés; valider les quatre Compose avec `config --quiet` sans afficher de valeurs sensibles.
3. Construire les images affectées, puis démarrer toute la stack par le point d'entrée courant : `make -f makefile2.mk stack-up` avant migration, `make stack-up` après migration. Lancer aussi `app-pres.py` et obligatoirement `emergency-interface` (via le Compose API avant migration).
4. Vérifier les services attendus, healthchecks, stabilité après démarrage et logs expurgés. Les jobs d'initialisation peuvent terminer avec code 0; un service permanent arrêté ou en boucle de redémarrage est un échec.
5. Tester MLflow, authentification, API de collecte/train/predict selon leurs routes réelles, Streamlit, Airflow et absence d'erreurs d'import DAG, Prometheus, Grafana, Loki/Alloy et exporters. Une page HTTP disponible ne suffit pas à prouver une prédiction fonctionnelle.
6. Avec un champion disponible, effectuer une prédiction authentifiée et vérifier les métriques. Réserver les mutations coûteuses (entraînement complet, collecte distante) aux validations prévues ci-dessous; vérifier à chaque lot que leurs contrats et dépendances restent accessibles.
7. Arrêter proprement les services lancés pour la validation, sans supprimer leurs volumes. Ne pas arrêter une stack préexistante sans avoir déterminé son usage.
8. Consigner commandes, résultats, durée, limites et erreurs préexistantes dans `changes.md`. Ne pas passer au lot suivant tant qu'une régression du lot reste ouverte. Une dépendance externe indisponible doit être signalée comme validation incomplète, jamais comme réussite.

## Étape 1 — Inventaire et référence fonctionnelle

### Objectif

Établir les usages prouvés et vérifier la stack avant nettoyage.

### Modifications prévues

- Créer `audit.md` avec les cinq catégories demandées : définitivement utilisé, probablement utilisé, probablement inutilisé, définitivement inutilisé, historique/legacy. Associer chaque décision à des références et usages indirects.
- Suivre les imports, COPY, montages, commandes, appels HTTP, chemins runtime, modèles sérialisés, scripts de préparation des données, variables et références documentaires. Vérifier également les fichiers cachés et les usages hors Make.
- Inventorier les services réellement actifs, les ressources Docker et les prérequis disponibles sans exposer de secrets.
- Assurer une sauvegarde récupérable et vérifiée des candidats non suivis avant toute suppression; ne pas créer automatiquement de commit.
- Enregistrer les tests de référence et les anomalies existantes. Si la stack échoue déjà, définir une correction ciblée comme étape distincte et mettre à jour le plan avant nettoyage.

### Fichiers potentiellement concernés

- `docs/changes/2026-10-13_main/audit.md`
- `docs/changes/2026-10-13_main/changes.md`
- `docs/changes/2026-10-13_main/plan.md`

### Validation prévue

- Protocole commun avec l'orchestration actuelle, tests API v2/auth/collecte/initialisation/DAG et présentation.
- Vérifier un entraînement initial et sa publication MLflow → BentoML dans un environnement de validation; documenter toute limite de données, credentials ou ressources.
- Aucun fichier applicatif supprimé à cette étape.

### Message de commit proposé

`docs(audit): document active dependencies and stack baseline`

## État de l’étape 1 — Audit effectué avec limites

- Inventaire, sauvegarde des sources et contrôles réels documentés dans `audit.md`, `inventory.json` et `runtime-baseline.json`.
- Stack démarrée et prédiction réelle via `emergency-interface` validée après synchronisation du champion existant.
- Initialisation sur stockage vierge, nouvel entraînement complet et collecte distante restent à valider dans l’environnement isolé final.
- Aucun DAG mutateur lancé : le chemin DVC déclenche des commits/push. La consigne sans commits impose de l’isoler ou d’utiliser un chemin de test sans publication Git avant toute exécution de bout en bout.
- Des anomalies préexistantes justifient l’étape corrective ci-dessous avant les suppressions.

## Étape 1 bis — Fiabiliser la référence avant nettoyage

### Objectif

Rétablir les contrôles de référence et la collecte des logs avant de supprimer des composants.

### Modifications prévues

- Adapter le filtre projet Alloy aux labels Compose réels sans introduire de dépendance au nom du dossier de clonage.
- Corriger les fixtures et assertions des tests actifs réellement obsolètes, après vérification des contrats et en excluant les caches Python historiques.
- Documenter les prérequis Python locaux (extra monitoring, OpenMP ou tests Linux) et les différences de versions BentoML.
- Retirer les logs d’identifiants/jetons de l’interface; maintenir son contrat HTTP et les flux métier.
- Qualifier cAdvisor sur Docker Desktop : vérifier les métriques de conteneurs et corriger le raccordement si possible; documenter précisément les limitations de plateforme sinon.
- Ne pas modifier les horaires des DAGs ou le fallback métier de l’interface pour faire passer des tests.
- Les vulnérabilités npm identifiées restent un constat séparé à analyser; pas de mise à jour massive automatique.

### Fichiers potentiellement concernés

- `monitoring/alloy/config.alloy`, `docker-compose.apis.yml`, `docker-compose.monitoring.yml`
- Tests actifs affectés, `interface/server.js`, `interface/src/services/predictionService.js`
- Documentation des prérequis et `docs/changes/2026-10-13_main/*`

### Validation prévue

- Tests ciblés avec bytecodes neufs et dépendances runtime correspondantes.
- Protocole commun, authentification et prédiction réelle via l’interface.
- Vérifier dans Loki les logs API et dans Prometheus les métriques par conteneur; un simple endpoint disponible ne suffit pas.
- Revue ciblée des sorties d’authentification sans exposer de secrets.

### Message de commit proposé

`fix(stack): restore baseline checks and observability`

## État de l’étape 1 bis — Terminée avec limite de plateforme documentée

- Les 70 tests ciblés passent : fixtures JWT distinctes login/train, planning réel du DAG et texte actuel des slides vérifiés.
- Alloy collecte effectivement les quatre API grâce à un label explicite, indépendant du nom de projet Compose.
- Logs d’identifiants/jetons retirés de l’interface; authentification et prédiction distante validées, absence des secrets testés vérifiée dans les logs serveur.
- Build et démarrage complets réussis après correction d’un conflit de montage du socket cAdvisor; 23 services permanents sans redémarrage, aucun import-error Airflow.
- cAdvisor accède au daemon via `/docker.sock`, mais les métriques par conteneur restent absentes avec Docker Desktop 29.8.2 / `overlayfs`. L’exclusion disque testée n’a pas suffi et n’est pas conservée. Limite préexistante qualifiée et documentée conformément au périmètre de l’étape; validation sur Linux compatible ou évolution ciblée à effectuer avant de déclarer ce volet complet.
- Résultats détaillés : `validation-1bis.json`, `changes.md` et `docs/operations/local-validation.md`. Aucun commit créé; aucun nettoyage ou renommage anticipé.

## Étape 2 — Migrer l'orchestration vers Makefile

### Objectif

Remplacer les deux orchestrations par un point d'entrée cohérent avec la stack de référence.

### Modifications prévues

- Reprendre les commandes utiles de `makefile2.mk` dans `Makefile`, comparer les commandes encore utiles de l'ancien Makefile et éliminer les doublons prouvés.
- Ajouter une aide et des commandes cohérentes de démarrage, arrêt sans perte de données, état, logs et lancement de la présentation. Inclure les interfaces confirmées actives.
- Mettre à jour les appels récursifs, scripts et instructions opérationnelles de lancement dans le même lot.
- Préserver les ports, variables, UID/GID, ordre de démarrage et persistance; documenter explicitement toute adaptation nécessaire.
- Supprimer `makefile2.mk` seulement après validation du nouveau point d'entrée. Les mentions historiques dans les journaux d'audit ne sont pas des instructions actives.

### Fichiers potentiellement concernés

- `Makefile`, `makefile2.mk`
- `README.md`, `docs/operations/orchestration-makefile-v2.md`
- Scripts, tests et documentation référençant l'ancien point d'entrée.

### Validation prévue

- `make help`, inspection des recettes et simulations ciblées sans exécuter les resets.
- Protocole commun entièrement via `Makefile`, initialisation et prédiction réelle.
- Aucune référence opérationnelle restante à `make -f makefile2.mk`.

### Message de commit proposé

`refactor(make): unify active stack orchestration`

## État de l’étape 2 — Terminée

- `Makefile` est le point d’entrée unique ; `makefile2.mk` supprimé après sauvegarde vérifiée et validation réelle. Interface incluse, présentation au premier plan, monitoring lancé une seule fois.
- 78 tests ciblés réussis ; 9 tests Make/smoke rejoués après suppression. Quatre Compose valides, aide et simulations init/stack/reset vérifiées, aucun reset exécuté.
- `make stack-up`, `make init` et replay `make initial-train` réussis : training enregistré dans MLflow, champion existant conservé et synchronisé vers BentoML, reload et prédictions API/interface validés.
- Le premier bootstrap après la stack complète a subi un OOM sur Docker 8 Go. Après passage à 16 Go par l’utilisateur, init a réussi dans l’ordre prévu (training avant Airflow), sans nouveau redémarrage. Réservation SQLite récupérée et résultat idempotent vérifié. Prérequis documenté, aucun réglage Docker modifié par l’agent.
- Contrôles finaux : 23 services permanents stables, six cibles Prometheus up, logs des quatre API dans Loki, zéro import-error Airflow, présentation accessible. Limite cAdvisor de plateforme conservée et documentée.
- Arrêt par `make stack-down` et SIGINT Streamlit ; volumes conservés. Aucun commit. Les workflows hebdomadaires et le stockage entièrement vierge restent réservés à l’environnement isolé final.

## Étape 3 — Nettoyer les anciennes applications

### Objectif

Conserver les applications actives et leurs dépendances exactes.

### Modifications prévues

- Évaluer séparément `app_sl_legacy.py`, `app_sl_app.py`, `app_sl_OCS_v1.py`, `app_presentation.py`, `app_soutenance.py` et leurs dossiers/tests.
- Supprimer uniquement les applications sans usage confirmé, leurs tests et assets exclusifs; conserver les ressources partagées.
- Conserver `app-pres.py` comme référence. Un renommage reste facultatif et doit inclure toutes ses références dans ce lot.
- Mettre à jour les instructions et configurations liées aux applications retirées.

### Fichiers potentiellement concernés

- Entrées Streamlit racine et dossiers `app/` concernés.
- `interface/` : application active à conserver et tester, exclue des suppressions.
- Compose, Makefile, tests et guides applicatifs associés.

### Validation prévue

- Tests de `app/pres-sl/tests`, contrôle du rendu des huit pages, images et polices.
- Protocole commun et validation des interfaces actives; aucune référence à une application supprimée.

### Message de commit proposé

`chore(apps): remove verified obsolete applications`

## État de l’étape 3 — Terminée

- Anciennes applications retirées après vérification des dépendances et sauvegarde ; pres-sl et interface actives conservées.
- Lanceur Streamlit corrigé (SystemExit en contexte serveur), huit pages et ressources validées par AppTest et tests. Stack complète validée et arrêtée sans reset. Détail : changes.md, files-step3.json, validation-3.json.
- Aucun navigateur CUA disponible pour contrôle visuel ; validation du document HTML et du rendu Streamlit effectuée.

## Étape 4 — Nettoyer les anciens services et workflows

### Objectif

Retirer le backend obsolète sans casser les dépendances indirectes.

### Modifications prévues

- Évaluer anciennes API, DAGs doublonnés, scripts de migration, pipeline historique et configurations associées avec les preuves de l'inventaire.
- Préserver le package `projet_accidents_mlops` tant que des consommateurs ou artefacts sérialisés en dépendent; ne pas supprimer `src/train_api` en bloc.
- Retirer uniquement les implémentations remplacées et leurs tests exclusifs; adapter packaging et chemins seulement si nécessaire.
- Mutualiser les fonctions métier identiques des deux DAGs dans un module partagé, tout en conservant leurs identifiants, horaires et sélection de semaine. Supprimer la sortie du jeton de reload dans la simulation et tester les deux DAGs.
- Si plusieurs sous-lots indépendants émergent, scinder cette étape dans le plan, avec une unité logique et une validation complète par sous-lot, sans créer de commit intermédiaire.

### Fichiers potentiellement concernés

- `src/train_api/`, `src/predict_api/`, `src/airflow_dags/dags/`
- `pipeline/`, `scripts/`, `tests/`, `pyproject.toml`
- Compose et configurations DVC réellement concernées.

### Validation prévue

- Tests backend actifs et consommateurs du package conservé; imports des modèles MLflow/BentoML.
- Protocole commun et initialisation idempotente ; tests des contrats hebdomadaires et des fonctions partagées sur les deux DAGs.
- Exécution de bout en bout hebdomadaire reportée explicitement à l’étape 7, dans la copie isolée après renommage : éviter de modifier les datasets/champion existants et respecter la consigne sans commits. DVC local réel, chemin Git désactivé uniquement dans le harnais de validation, aucune publication distante.

### Message de commit proposé

`chore(backend): remove verified obsolete services and workflows`

## État de l’étape 4 — Nettoyage validé

- Anciennes API/pipelines/tests exclusifs supprimés ; DVC et classes nécessaires à la compatibilité conservés. Fonctions métier DAG mutualisées sans changement des schedules ou sélection de semaine.
- 115 tests locaux, 159 tests Linux et 1 skip justifié ; bootstrap, champion existant et stack complète validés, puis arrêtés sans reset. Voir files-step4.json et validation-4.json.
- L’intégration hebdomadaire de bout en bout sera exécutée dans la copie isolée finale ; aucune publication Git/DVC distante sur le dépôt utilisateur.

## Étape 4 bis — Renommer les API actives sans suffixe de version

### Objectif

Les implémentations actives deviennent `src/predict_api` et `src/train_api`, avec les services Compose `predict-api` et `train-api`, après retrait des anciennes implémentations à l’étape 4.

### Modifications prévues

- Vérifier que les anciennes implémentations occupant les noms cibles ont été retirées sans écraser le package partagé `src/train_api/utils/projet_accidents_mlops`, qui reste nécessaire tant que ses consommateurs existent.
- Déplacer les implémentations v2 vers les noms cibles et mettre à jour imports, commandes Uvicorn/BentoML, COPY Docker, contextes de build, chemins de configuration et tests.
- Renommer les services Compose; adapter Makefile, dépendances et URLs internes d’Airflow, initialisation, interface, exemples d’environnement, scripts, métriques/logs et dashboards.
- Mettre à jour la documentation opérationnelle et la présentation dans ce même lot pour éviter des procédures transitoires incorrectes. Les journaux historiques restent des preuves de l’état antérieur.
- Préserver les endpoints publics, ports, authentification et données. Conserver les identifiants physiques des volumes et chemins persistants existants lorsqu’ils garantissent la continuité des données; tout renommage de persistance exige une migration explicite, validée et réversible.
- Examiner les modèles MLflow/BentoML déjà enregistrés : ils peuvent importer `src.train_api_v2` depuis leur code embarqué. Tester leur chargement avant de supprimer toute compatibilité; prévoir si nécessaire une compatibilité limitée et documentée plutôt qu’un nouvel entraînement imposé ou un reset.
- Traiter ce renommage comme un lot autonome après le nettoyage backend; ne pas supprimer un ancien chemin encore nécessaire au chargement du champion.

### Fichiers potentiellement concernés

- `src/predict_api_v2/` → `src/predict_api/`
- `src/train_api_v2/` → `src/train_api/`, `tests/train_api_v2/` et autres tests concernés
- `docker-compose.apis.yml`, `src/airflow_dags/docker-compose.yaml`, `Makefile`
- DAGs, déclencheur initial, interface, configurations monitoring, `.env.example`
- Documentation et présentation référençant les anciens noms

### Validation prévue

- Recherche des références restantes : chaque mention v2 doit être justifiée par l’historique, la compatibilité des modèles ou la conservation de la persistance.
- Tests ciblés des API et consommateurs, validation Compose et reconstruction des images.
- Protocole commun avec les nouveaux noms, vérification DNS/URLs entre services et ingestion des logs avec les nouveaux labels.
- Chargement du champion existant, rechargement BentoML et prédiction réelle via `emergency-interface`; aucun volume ni artefact perdu.
- Validation du workflow de training dans l’environnement isolé, sans commit ni push dans le dépôt utilisateur.

### Message de commit proposé

`refactor(api): rename active training and prediction services`

## État de l’étape 4 bis — Renommage validé

- Nouveaux modules, services/DNS, conteneur train et monitoring en place ; persistance physique conservée. Imports des anciens modèles résolus depuis leur code embarqué MLflow, bootstrap et prédiction existante vérifiés.
- 115 tests locaux et 159 tests Linux réussis (1 skip Make). Stack complète et nouvelles étiquettes vérifiées, arrêt non destructif. Détail : files-step4bis.json et validation-4bis.json.
- Entraînement d’un modèle neuf avec les nouveaux imports réservé à l’étape 7 isolée.

## Étape 5 — Réduire les configurations et artefacts inutiles

### Objectif

Conserver les dépendances et fichiers nécessaires au développement et à l'exécution.

### Modifications prévues

- Auditer Dockerfile racine, requirements, lockfile, contextes Docker, volumes déclarés sans consommateurs et configurations dupliquées.
- Retirer les dépendances seulement après contrôle des imports, CLI, build et consommateurs indirects; régénérer le lockfile si nécessaire.
- Nettoyer les caches, backups et artefacts prouvés inutiles au code courant; préserver les données et états utilisateurs et vérifier les règles d'exclusion.
- Ne pas supprimer les configurations personnelles d'outils au seul motif qu'elles ne participent pas au runtime.

### Fichiers potentiellement concernés

- `Dockerfile`, `.dockerignore`, `.gitignore`, `requirements.txt`, `pyproject.toml`, `uv.lock`
- Requirements des services et Compose concernés.
- Artefacts identifiés dans l'audit, sans suppression globale de `data/`, `models/` ou `reports/`.

### Validation prévue

- Installation reproductible, résolution des dépendances et reconstruction des images affectées.
- Protocole commun; vérifier droits de montage et persistance après redémarrage.

### Message de commit proposé

`chore(config): remove unused configuration and build artifacts`

## État de l’étape 5 — Terminée

- Exporters construits depuis un groupe minimal dans le lockfile unique ; code copié sélectivement, aucun sync runtime. Configs/deps inutiles retirées, dépendances indirectes DVC/httpx2 préservées, BentoML local aligné.
- Installation verrouillée, 115 tests locaux, quatre Compose, builds et stack complète validés puis arrêtés sans reset. Image runtime exporters : 20 distributions, 410 MB. Voir files-step5.json et validation-5.json.
- Données, backups locaux, modèles, volumes physiques et outillage personnel conservés.

## Étape 6 — Consolider la documentation actuelle

### Objectif

Documenter fidèlement l'architecture nettoyée et supprimer les guides devenus inutiles.

### Modifications prévues

- Réécrire le README : objectif, architecture, prérequis, environnement, démarrage/arrêt, initialisation, entraînement, workflow hebdomadaire, API, présentation, monitoring, données et commandes Make.
- Classer chaque document pertinent comme actuel, partiel, obsolète, redondant ou historique; corriger ou supprimer avec justification.
- Consolider les index et procédures; corriger services, ports, endpoints, liens et schémas.
- Conserver la traçabilité obligatoire dans `docs/changes`; distinguer ces journaux des archives d'implémentations supprimables.
- Expliquer les opérations de remise à zéro destructives sans les exécuter sur l'état existant.

### Fichiers potentiellement concernés

- `README.md`, `README_PIPELINE.md`, `README_monitoring.md`
- `docs/`, README locaux et contenu explicatif de la présentation.

### Validation prévue

- Vérifier les liens et exécuter les commandes documentées applicables.
- Protocole commun via les instructions du README; vérifier cohérence des descriptions avec la stack.

### Message de commit proposé

`docs(project): align documentation with the active stack`

## État de l’étape 6 — Terminée

- README et guides cohérents avec les noms/contrats actuels, archives et doublons retirés, classification documentaire enregistrée. Références historiques limitées aux journaux obligatoires et identifiants de persistance conservés.
- Liens locaux valides, 69 tests, builds et stack complète via procédures documentées validés puis arrêtés sans reset ; aucun commit. Voir documentation-audit.json, files-step6.json et validation-6.json.

## Étape 7 — Vérifier la stack depuis un environnement propre

### Objectif

Prouver qu'un nouveau développeur peut construire, initialiser et utiliser le dépôt nettoyé.

### Modifications prévues

- Réaliser une nouvelle analyse des imports, chemins, COPY, volumes, scripts et références supprimées.
- Tester dans une copie isolée avec données nécessaires et stockage de validation, en tenant compte des noms fixes de volumes/réseaux/conteneurs avant tout démarrage. Ne pas lancer `reset`/`reset-full` sur l'état existant.
- Produire `validation-stack.md` et le bilan demandé : architecture, suppressions, déplacements, modifications, éléments suspects conservés, commandes, documentation et limites.
- En cas de défaut révélé, créer une étape corrective ciblée dans le plan et la valider avant de clôturer.

### Fichiers potentiellement concernés

- `docs/changes/2026-10-13_main/validation-stack.md`
- `docs/changes/2026-10-13_main/audit.md`, `changes.md`, `plan.md`

### Validation prévue

- Build réel de toutes les images et démarrage depuis le nouveau Makefile.
- Initialisation, entraînement initial, champion MLflow/BentoML, prédiction authentifiée, DAG hebdomadaire, collecte et monitoring quand les prérequis sont disponibles.
- Contrôle de stabilité, logs, healthchecks, bases/volumes et arrêt propre sans destruction de l'état utilisateur.
- Tests pertinents du dépôt et contrôles configurés. Une indisponibilité externe reste explicitement une limite de validation.

### Message de commit proposé

`docs(validation): record clean stack verification results`

## État de l’étape 7 — Terminée avec limites explicites

- Installation, builds et initialisation sur stockage vierge réussis ; entraînements initial/hebdomadaire, collecte distante, DVC local, publication initiale BentoML et prédiction réelle validés.
- 261 tests Linux réussis, 1 skip ; 23 services stables avant/après redémarrage. Arrêt final sans suppression de volumes et sans commit.
- Bilan et listes : validation-stack.md, cleanup-files.json, baseline-files.json ; résultats runtime, hebdomadaire et arrêt en JSON.
- Validation distante Git/DVC/Slack, contrôle visuel navigateur et métriques cAdvisor par conteneur restent limités ; la validation exhaustive de ces volets n’est pas déclarée acquise.

## Étape 7 bis — Corriger les écarts de validation

### Objectif

Aligner le Makefile restauré sur les services actuels et isoler le test d’authentification de la configuration locale.

### Modifications prévues

- Corriger appels récursifs, noms API et lancement de l’interface ; restaurer les commandes documentées.
- Créer incoming avant le réglage des droits ; conserver les volumes.
- Remplacer le service réel par un stub dans le seul test du jeton valide.

### Fichiers potentiellement concernés

- `Makefile`
- `tests/train_api/test_auth.py`

### Validation prévue

- Aide, simulations et tests ; démarrage réel dans la copie isolée.
- Suite complète Linux ; aucun reset exécuté.

### Message de commit proposé

`fix(validation): align restored orchestration and isolate auth test`

## État de l’étape 7 bis — Terminée

- Makefile réconcilié et création incoming corrigée ; test d’authentification indépendant du .env.
- 261 tests Linux réussis, 1 skip ; 8 tests locaux Make/smoke et démarrage réel réussis. Aucun commit.

## Étape 8 — Aligner l’exemple d’environnement et les exclusions

### Objectif

Reproduire la structure du .env local avec valeurs sûres et vérifier les frontières Git/Docker/DVC.

### Modifications prévues

- Reprendre les variables et leur ordre sans copier les secrets ; documenter les variables locales obsolètes.
- Corriger uniquement les deux anciens noms DNS dans le .env local, pour les services renommés ; préserver toutes les autres valeurs.
- Compléter les exclusions des secrets, caches et états runtime dans chaque contexte Docker actif, Git et DVC.
- Préserver les entrées Docker et données réellement suivies par le pipeline DVC.

### Fichiers potentiellement concernés

- `.env.example`, `.dockerignore`, `.gitignore`, `.dvcignore`
- `.dockerignore` des contextes sous src et interface.

### Validation prévue

- Comparaison des clés .env/exemple sans afficher les valeurs ; quatre Compose avec l’exemple.
- Contrôles réels Git/DVC et des contextes Docker ; reconstruction et validation dans la copie isolée.
- Revue du diff, arrêt sans perte de données et journal français.

### Message de commit proposé

`chore(config): align environment template and ignore rules`

## État de l’étape 8 — Terminée

- Exemple aligné sur les 50 variables locales avec valeurs sûres ; deux noms DNS locaux obsolètes corrigés sans autre changement de valeur.
- Exclusions Git/DVC et sept contextes Docker vérifiés ; quatre Compose avec exemple, 11 tests ciblés et stack complète isolée validés.
- Datasets et sorties DVC conservés, arrêt final sans suppression de volumes, aucune publication Git. Détails : validation-ignore.json, validation-8.json et files-step8.json.

## Étape 9 — Actualiser le README après les derniers changements

### Objectif

Donner une procédure cohérente avec Make, l’environnement et les exclusions actuels, et distinguer vérifications réalisées et limites.

### Modifications prévues

- Compléter la configuration initiale, les URLs internes, surcharges Make, règles Git/Docker/DVC et résultats de validation.
- Relier le README et l’index docs aux guides actuels et au bilan daté.
- Corriger les formulations ambiguës sur activation des DAGs et métriques DVC.

### Fichiers potentiellement concernés

- `README.md`
- `docs/README.md`

### Validation prévue

- Vérifier liens, chemins, cibles Make et paramètres cités contre leurs sources.
- Exécuter make help et simulations non mutatrices des commandes locales.
- Revue du diff documentaire ; pas de nouveau démarrage nécessaire pour ce lot sans modification runtime (résultats étape 8 référencés).

### Message de commit proposé

`docs(readme): reflect current setup and validation results`

## État de l’étape 9 — Terminée

- README et index docs actualisés sur environnement, Make, exclusions et résultats finaux.
- Liens et cibles valides ; aide et trois simulations exécutées, diff documentaire revu. Aucun changement runtime ni commit.

## Critères de fin

- Chaque suppression possède une preuve d'inutilité et une possibilité de récupération.
- Chaque étape a sa validation réelle, sa revue et son entrée française dans `changes.md`, avec le même message de commit anglais que dans ce plan.
- `Makefile` est l'unique point d'entrée principal; aucune procédure active n'utilise `makefile2.mk`.
- Les API actives utilisent les noms `predict_api` / `train_api` et les services `predict-api` / `train-api`; toute compatibilité v2 restante est justifiée et documentée.
- La présentation et les services nécessaires fonctionnent; aucun import ou chemin actif ne pointe vers un fichier supprimé.
- Le README et les guides conservés correspondent au système réel.
- La stack complète est construite et démarrée depuis un environnement propre, puis arrêtée proprement. Toute vérification non réalisée est identifiée; la validation complète n'est pas déclarée acquise tant que ses dépendances restent bloquantes.
- Après chaque étape, rapport dans le chat et enregistrement du message correspondant pour la traçabilité. Aucun commit intermédiaire : les commits seront envisagés uniquement après la fin du nettoyage et des tests. Aucun passage à l’étape suivante avec une régression non résolue.

## Publication de la base propre — Autorisée par l’utilisateur

Le nettoyage et les validations étant terminés, l’utilisateur demande un commit unique de la base avec le message exact `chore: establish clean repository baseline`, puis un push sur main. Cette demande remplace la consigne précédente sans commits ; les messages des étapes restent la trace de leurs unités logiques, sans commits intermédiaires. Contrôle de l’index, absence de secrets locaux/signatures de credentials et fichiers trop lourds, puis commit et push normal sans réécriture d’historique.
