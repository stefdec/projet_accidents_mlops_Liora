## Connexion de l'interface aux APIs predict_api_v2 et auth_api

**Message de commit**

`feat(interface): connect web interface to predict_api_v2 and auth_api services`

**Ce qui a changé**

- Restructuration et mise en conformité de la fonction `formatNumericPayload` dans `predictionService.js` avec le schéma Pydantic `InputData` de `predict_api_v2`.
- Remplacement des libellés texte et clés anglaises par des alias Pydantic français (`jour_semaine`, `heure`, `periode_journee`, `age_conducteur`, `categorie_vehicule`, `type_choc`, `presence_obstacle_fixe`, `type_obstacle`, `type_collision`) et des entiers BAAC stricts.
- Suppression du champ superflus `month` pour respecter la contrainte `extra="forbid"`.
- Amélioration de la gestion d'erreur dans le proxy Express Node.js (`server.js`) lors du relais vers `auth_api` pour retourner fidèlement les statuts 401/403/400.
- Ajout d'un badge visuel dans `PredictionResult.jsx` indiquant la provenance de la prédiction (`remote_api` BentoML vs Moteur d'urgence local) ainsi que la version du modèle.

**Pourquoi**

- L'API `predict_api_v2` rejetait les requêtes frontend en HTTP 422 / 400 en raison de l'incompatibilité des types (strings au lieu d'int), des alias absents et du champ superflus `month`.
- L'interface devait assurer une communication directe et transparente avec les microservices d'arrière-plan `auth-api` (port 8005) et `predict_api_v2` (port 8009) sans déclencher intempestivement le mode dégradé local.

**Fichiers**

- `interface/src/services/predictionService.js`
- `interface/server.js`
- `interface/src/components/PredictionResult.jsx`

**Validation**

- Suite de tests unitaires backend validée via `pytest tests/test_auth_api.py tests/test_predict_api_v2_service.py` (26 tests réussis).
- Vérification du format du payload JSON généré par `formatNumericPayload` avec les 38 champs requis.
