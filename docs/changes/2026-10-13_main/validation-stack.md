# Bilan du nettoyage et validation finale — 13 octobre 2026

## Résultat et architecture

Le dépôt utilise un Makefile unique, les API `train_api` / `predict_api`, MLflow/PostgreSQL, BentoML, auth/collecte, Airflow/Celery/PostgreSQL/Redis, emergency-interface, la présentation pres-sl et le monitoring Prometheus/Grafana/Loki/Alloy/exporters. Deux DAGs gardent leurs identifiants et horaires, avec fonctions métier partagées. DVC et les classes Python nécessaires aux modèles enregistrés sont conservés.

Les étapes 1 à 6 ont été validées individuellement, puis la stack a été reconstruite dans une copie privée avec stockage vierge. Aucun commit ni push n’a été créé. Le dépôt initial n’a aucun fichier suivi : les comparaisons reposent sur des sauvegardes vérifiées, pas sur un diff Git vide.

## Environnement propre et protection des données

Copie : `/private/tmp/accidents-clean-validation-2026-10-13`. Projets Compose, réseau, conteneurs nommés et volumes distincts ; dataset de base copié, incoming et stockage MLflow/BentoML/état/Airflow initialement vierges. Secrets locaux copiés dans un fichier privé, jamais inclus dans les rapports. Docker dispose de 16 Go.

DVC utilise un remote local de validation. La publication Git du DAG est neutralisée uniquement dans cette copie pour respecter la consigne sans commits ; le code utilisateur reste inchangé. Slack est dirigé vers une adresse loopback : aucune notification distante envoyée. Ces publications distantes ne sont donc pas validées.

## Commandes et résultats

- `make install` : installation verrouillée réussie dans la copie.
- Quatre Compose validés, images construites via les recettes Make.
- `make init` : entraînement initial neuf, champion version 1 enregistré dans MLflow, publication BentoML et reload réussis. Run : `9bfe1d23bf77439b93150798021a7f4d` ; durée entraînement environ 125 secondes.
- `make stack-up` : réussite après correction du Makefile restauré, sans anciens noms de services ou appel à makefile2.mk. Interface obligatoire incluse.
- `make help`, simulation `make -n stack-up` et 8 tests locaux architecture/smoke : réussite. Aucun reset exécuté.
- Suite complète dans Linux, avec sources du dépôt montées : **261 passed, 1 skipped, 46 warnings**. Skip : Make absent de l’image runtime. Le test d’authentification est désormais indépendant du `.env`.
- Le test ML local macOS ne peut pas être collecté faute de bibliothèque OpenMP ; la suite Linux couvre ce composant.
- Validation HTTP et Docker : **23 services permanents stables, zéro redémarrage**, healthchecks satisfaits, zéro erreur d’import Airflow.
- Prédiction authentifiée API et emergency-interface : réussite ; source `remote_api`, probabilité et version du modèle vérifiées. Requêtes non authentifiées refusées.
- Présentation : endpoint Streamlit disponible ; tests AppTest des huit pages et assets réussis dans la suite complète.
- Six cibles Prometheus up, logs des quatre API réellement présents dans Loki ; API Grafana et six entrées de tableaux de bord/dossiers accessibles.
- Workflow `pull_weekly` exécuté par Celery : **success**, semaine 1 collectée, fichier Parquet versionné et objet DVC réellement poussé dans le remote local. Entraînement hebdomadaire réussi : run `e0e4a0aa003a4e3d8da8d0c098bc2b19`, environ 146 secondes. Branche `skip_deployment` réussie : champion initial conservé ; publication/reload réels déjà validés au bootstrap. Environ 157 secondes entre lancement et achèvement (la durée affichée par Airflow dags test inclut l’écart avec la date logique et n’est pas une mesure du temps réel).

Une première tentative du harnais avait une URL Slack vide : Grafana a refusé sa configuration. Le harnais a été corrigé et Grafana recréé stable ; ce défaut ne concernait pas la configuration du dépôt.

## Suppressions, déplacements et modifications

Liste détaillée par chemin, type et empreintes : [cleanup-files.json](cleanup-files.json). Comparaison complémentaire des sources initiales avec l’état final (incluant les corrections de référence) : [baseline-files.json](baseline-files.json). Les manifests `files-2.json`, `files-step3.json`, `files-step4.json`, `files-step4bis.json`, `files-step5.json`, `files-step6.json`, `files-step7bis.json` gardent les unités de travail.

- Supprimés : makefile2.mk ; anciennes applications Streamlit et assets exclusifs ; anciennes API et pipelines train/predict ; scripts de migration et monitoring remplacés ; modules partagés sans consommateur courant ; tests exclusifs ; requirements redondants ; anciennes archives documentaires et caches vérifiés.
- Déplacés : API actives et tests v2 vers les noms sans suffixe ; guide orchestration et dashboard prédiction renommés.
- Modifiés : Makefile/Compose/Dockerfiles, packaging verrouillé, configurations Alloy/Prometheus/Grafana, imports et URLs, DAGs, interface (retrait logs secrets), présentation et documentation. Les manifests distinguent les fichiers homonymes remplacés des anciens fichiers supprimés.
- Documentation actuelle : README, README_PIPELINE, README_monitoring, index docs et guides opérations/API/Airflow/DVC. Classification : [documentation-audit.json](documentation-audit.json).

## Éléments conservés et justification

- DVC/BentoML : utilisés réellement par les workflows et la publication du modèle.
- `projet_accidents_mlops.features/modeling` : compatibilité des objets sérialisés ; code ancien embarqué dans les artefacts MLflow validé avant le renommage.
- Volume physique `train_api_v2_state` et chemin `data/train-api-v2` : conservation de la persistance, aucune migration destructrice implicite.
- Datasets, modèles, rapports et backups utilisateurs : conservés ; état runtime séparé dans la validation.
- Ancien remote DVC local, script et CSV de roadmap, outillage personnel : usages externes non exclus, conservés par prudence.
- Journaux historiques docs/changes : traçabilité obligatoire ; leurs références anciennes ne sont pas des commandes opérationnelles.

Les sources supprimées sont récupérables depuis les sauvegardes privées dans `/private/tmp/accidents-cleanup-*` ; ces sauvegardes restent locales et ne constituent pas un archivage durable.

## Limites et travaux séparés

- cAdvisor : cible disponible, mais aucune série CPU/mémoire nommée par conteneur sur Docker Desktop 29.8.2 / overlayfs. Limite qualifiée dans [local-validation.md](../../operations/local-validation.md), pas présentée comme un succès de monitoring conteneur.
- Audit npm antérieur : 13 vulnérabilités, dont 3 de production ; traitement ciblé à prévoir. Bundle Vite volumineux, pas de changement opportuniste de dépendances.
- Aucun navigateur CUA disponible : contrôle visuel interactif, cartes et météo externes restent manuels. Rendu HTML/Streamlit et flux HTTP sont vérifiés.
- Push Git/DVC distant et livraison Slack non testés ; DVC local réel et contrats de publication couverts séparément.
- Avertissements de dépendances et dépréciation Streamlit conservés, sans échec des tests Linux.

## Messages de commit proposés

Chaque message correspond à l’entrée de même nom dans changes.md et plan.md ; aucun commit créé. Correction finale : `fix(validation): align restored orchestration and isolate auth test`. Rapport final : `docs(validation): record clean stack verification results`.

## Redémarrage et arrêt final

`make stack-down` puis `make stack-up` réussis dans la copie isolée ; prédictions API/interface, 23 services stables, six cibles Prometheus et logs Loki revalidés après redémarrage (`validation-7-restart.json`). Champion conservé sans nouvel entraînement. Arrêt final par Make et SIGINT de la présentation : aucun conteneur restant, aucun volume préexistant supprimé (`validation-shutdown.json`). Les données de validation sont conservées séparément pour inspection.

Le nettoyage et les contrôles applicatifs réalisables sont terminés. La validation n’est pas qualifiée de complète sur les volets distants, visuels et cAdvisor explicitement exclus ci-dessus.

## Complément environnement et exclusions (étape 8)

.env.example aligné sur les 50 variables et leur ordre dans .env, avec valeurs sûres. Deux anciens noms DNS présents dans le .env local corrigés ; secrets inchangés. Git/DVC et sept contextes Docker vérifiés effectivement ; aucun dataset nécessaire masqué. Quatre Compose valides avec l’exemple, 11 tests ciblés réussis et 23 services de nouveau validés après reconstruction. Détails : validation-ignore.json, validation-8.json et files-step8.json. Les limites déjà consignées restent applicables.
