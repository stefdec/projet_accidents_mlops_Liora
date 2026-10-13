## Harmonisation des permissions du store BentoML

**Message de commit**

`fix(bentoml): align shared store ownership`

**Ce qui a changé**

- Alignement de l'UID/GID de `initial-train` sur les valeurs `LOCAL_UID` et
  `LOCAL_GID` utilisées par la stack.
- Ajout du service Airflow one-shot `bentoml-init`, exécuté avant le worker,
  pour migrer le propriétaire du volume existant sans supprimer les modèles.
- Reconstruction explicite de l'image `initial-train` pendant `make init` et
  ajout des tests de configuration associés.
- Documentation du diagnostic et de la procédure de récupération.

**Pourquoi**

- Les modèles créés par `initial-train` appartenaient à l'UID 999 avec un
  répertoire en mode `0700`. Le worker Airflow exécuté avec l'UID 1000 échouait
  donc dans `bento_models.list()` avant de pouvoir publier le champion weekly.

**Fichiers**

- `docker-compose.apis.yml`
- `makefile2.mk`
- `src/inital_train/Dockerfile`
- `src/inital_train/entrypoint.sh`
- `src/airflow_dags/docker-compose.yaml`
- `tests/train_api_v2/test_compose_service.py`
- `tests/test_docker_architecture.py`
- `docs/operations/initial-training.md`

**Validation**

- Tests strictement ciblés : 22 succès.
- Passe élargie : 46 succès et 3 échecs préexistants sans lien avec cette
  correction.
- Validation des deux configurations avec `docker compose config --quiet` :
  succès.
- Migration réelle de `bentoml_store` vers `1000:0` : succès.
- Liste BentoML depuis le worker Airflow : `accidents:3m2k5fvqdogineuy` lisible.
- Build complet de `initial-train` interrompu pendant le téléchargement lent de
  PyArrow ; l'étape Docker modifiée de création de l'utilisateur avait réussi.
