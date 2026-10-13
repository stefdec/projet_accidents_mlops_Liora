## Documenter le DAG pull_weekly

**Message de commit**

`docs(airflow): document pull_weekly week progression`

**Ce qui a changé**

- Mise à jour des README et du wiki opérationnel pour présenter `pull_weekly`
  comme le DAG hebdomadaire de référence.
- Documentation du déclenchement à la demande (`schedule=None`) et du calcul de
  la semaine suivante via la Variable Airflow `last_processed_week`.
- Remplacement des anciennes instructions `make airflow-week WEEK=N`, qui ne
  correspondent plus au DAG actuel.
- Clarification que `pull_train` n'est plus utilisé pour les exécutions
  hebdomadaires.

**Pourquoi**

- Le workflow a changé : la semaine n'est plus fournie par le calendrier ou un
  argument Makefile, mais sélectionnée automatiquement à chaque déclenchement.

**Fichiers**

- `README.md`
- `docs/README.md`
- `docs/operations/README.md`
- `docs/operations/orchestration-makefile-v2.md`
- `docs/operations/auth-api.md`
- `docs/operations/pull-data-api.md`
- `docs/operations/train-api.md`
- `docs/ml/README_MLFLOW.md`
- `docs/ml/GUIDE_ARCHITECTURE_TESTS_MLOPS.md`

**Validation**

- Recherche des références actives à `pull_train` et `airflow-week` effectuée.
- Contrôle de format du diff : `git diff --check` réussi.

## Publier les pointeurs DVC depuis le DAG

**Message de commit**

`feat(airflow): push weekly DVC pointers to Git`

**Ce qui a changé**

- Ajout du commit et du push Git du seul pointeur `.dvc` créé pour la semaine
  collectée, après le push DVC.
- Conservation d'un retry idempotent : un commit déjà créé mais non poussé est
  poussé sans créer de commit supplémentaire.
- Le worker Airflow peut désormais écrire dans les métadonnées Git montées pour
  créer le commit ; le remote est configurable par `DVC_GIT_REMOTE`.
- Chaque commande Git déclare le workspace monté comme répertoire sûr, ce qui
  gère le décalage d'UID entre l'hôte et le conteneur Airflow sans modifier la
  configuration Git globale.
- Un token de push optionnel est transmis via un askpass temporaire supprimé
  après la commande, sans être placé dans l'URL du remote ni dans le script.

**Pourquoi**

- `dvc push` publie les objets de données, mais DagsHub a besoin du pointeur
  Git pour les rattacher au chemin `data/incoming/` et les afficher.

**Fichiers**

- `src/airflow_dags/dags/pull_weekly.py`
- `src/airflow_dags/dags/pull_train.py`
- `src/airflow_dags/docker-compose.yaml`
- `.env.example`
- `src/airflow_dags/tests/test_pull_train.py`

**Validation**

- `uv run pytest -q src/airflow_dags/tests/test_pull_train.py -k 'commit_and_push_dvc_pointer or configure_git_push_auth'` réussi (4 tests).
- `docker compose -f src/airflow_dags/docker-compose.yaml config` réussi.
- `git diff --check` réussi.
- La suite complète du fichier contient un échec préexistant : le test attend
  `schedule is None`, alors que le DAG `pull_train` définit `"0 3 * * 1"`.
