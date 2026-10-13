## Correction de la référence token dans le proxy de prédiction server.js

**Message de commit**

`fix(interface): fix missing token variable in predict proxy server`

**Ce qui a changé**

- Déclaration et extraction de la variable `token` depuis l'en-tête `Authorization` dans l'endpoint `app.post('/api/predict')` de `interface/server.js`.
- Rétablissement de l'authentification fallback hôte dans `interface/server.js`.
- Transmission de la propriété `model_version` lors du succès de l'appel proxy vers BentoML.

**Pourquoi**

- En l'absence de la variable `token` (référence indéfinie), Node.js levait une exception `ReferenceError: token is not defined` à l'exécution de la requête vers BentoML (`predict_api_v2`).
- Cette exception forçait le proxy à basculer systématiquement en mode dégradé local (`mlops_emergency_engine`), provoquant l'affichage permanent du message `"Moteur d'Urgence Fallback"` sur l'interface React dans `PredictionResult.jsx`, y compris quand le modèle BentoML fonctionnait et était correctement chargé.

**Fichiers**

- `interface/server.js`

**Validation**

- Vérification de la syntaxe du fichier via `node -c interface/server.js` (succès).
