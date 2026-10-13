# Plan d'implémentation — Connexion de l'Interface aux APIs (predict_v2 et auth_api)

## Objectif

Connecter l'interface de régulation d'urgence (React + Proxy Node.js Express) aux deux microservices backend conformément aux fiches opérationnelles d'architecture :
1. **`auth-api`** (`docs/operations/auth-api.md`, port 8005 / conteneur `auth-api`).
2. **`predict_api_v2`** (`docs/operations/predict-api-v2.md`, port 8009 / conteneur `predict-api-v2`).

---

## Contexte & Alignement Architecture

L'analyse croisée des fiches opérationnelles (`docs/operations/predict-api-v2.md` et `docs/operations/auth-api.md`), du code source backend (`src/predict_api_v2/service.py` et `src/auth_api/main.py`) et du frontend React montre les constats d'incompatibilité suivants :

### 1. API de prédiction (`predict_api_v2`)
- **Contrat strict Pydantic (`extra="forbid"`)** : Le modèle `InputData` interdit tout champ supplémentaire. Or, `predictionService.js` envoyait un champ superflus `month` (car copié manuellement), ce qui déclenche un rejet immédiat HTTP 422.
- **Noms de champs aliasés en français** : Le schéma Pydantic v2 de `predict_api_v2` définit des alias pour les clés publiques :
  - `jour_semaine` (au lieu de `day_of_week`)
  - `heure` (au lieu de `hour`)
  - `periode_journee` (au lieu de `day_period`)
  - `age_conducteur` (au lieu de `age`)
  - `categorie_vehicule` (au lieu de `catv_group`)
  - `type_choc` (au lieu de `macro_choc`)
  - `presence_obstacle_fixe` (int 0 ou 1)
  - `type_obstacle` (au lieu de `macro_obsm`)
  - `type_collision` (au lieu de `type_crash`)
- **Types entiers vs Chaînes texte** : `predict_api_v2` attend des entiers codés selon les tranches et bornes BAAC (ex: `jour_semaine`: 1..7, `periode_journee`: 1..4, `categorie_vehicule`: 0..8, `type_choc`: 0..5, `type_obstacle`: 0..4, `type_collision`: 0..3). L'interface envoyait jusqu'ici des libellés texte (`"Monday"`, `"Véhicules légers"`, `"Frontal"`), provoquant l'échec de validation Pydantic et le basculement automatique vers le moteur d'urgence en fallback (`mlops_emergency_engine`).

### 2. API d'Authentification (`auth-api`)
- Conforme à `docs/operations/auth-api.md`, `POST /login` exige la charge utile JSON `{ "username": "...", "password": "...", "token_type": "login" }`. Si `token_type` est omis ou invalide, l'API renvoie HTTP 400.
- Le jeton JWT généré par `auth-api` avec `JWT_SECRET_LOGIN` est vérifié par `predict_api_v2` qui utilise `JWT_SECRET_KEY` (`JWT_SECRET_KEY` = `JWT_SECRET_LOGIN`).

### 3. Statut du fichier `modalite_variable.md`
- Le fichier `docs/changes/2026-09-15_interface-connexion/modalite_variable.md` récapitule la description des modalités BAAC.
- **Évaluation de nécessité** : Il n'est **pas nécessaire** pour le code de l'application, car le contrat officiel et complet est déjà porté par `src/predict_api_v2/service.py` (`InputData` et `CATEGORY_LABELS`) et documenté dans `docs/operations/predict-api-v2.md`.
- **Recommandation** : Supprimer `modalite_variable.md` avant toute publication (push/PR) afin d'éviter tout conflit Git ou fichier inutile sur la branche `main`.

---

## Périmètre

### Inclus
- Reprise de la fonction `formatNumericPayload` dans `interface/src/services/predictionService.js` pour construire exactement les 38 champs requis avec leurs alias français et leurs types numériques entiers/flottants stricts.
- Suppression du champ superflus `month` de la charge utile envoyée.
- Validation de la transmission de `token_type: "login"` dans les requêtes vers `auth_api`.
- Vérification et alignement du serveur Proxy Express (`interface/server.js`) pour le transfert des headers d'authentification Bearer.
- Suppression propre du fichier temporaire `modalite_variable.md`.
- Validation d'intégration E2E de la chaîne complète avec `docker-compose.apis.yml`.

### Hors périmètre
- Modification des modèles ML ou de `src/predict_api_v2/service.py`.
- Modification de la structure des composants UI React.

---

## Étape 1 — Suppression du fichier temporaire local `modalite_variable.md`

### Objectif
Nettoyer le répertoire de la branche `interface/connexion` pour garantir l'absence de conflit Git lors de la fusion finale avec `main`.

### Modifications prévues
- Supprimer `docs/changes/2026-09-15_interface-connexion/modalite_variable.md`.

### Fichiers potentiellement concernés
- `docs/changes/2026-09-15_interface-connexion/modalite_variable.md` [DELETE]

### Validation prévue
- Vérification par `git status` que le fichier est supprimé de la copie de travail.

### Message de commit proposé
`chore(interface): remove temporary modalite_variable doc before branch merge`

---

## Étape 2 — Restructuration du Payload dans `predictionService.js` selon `predict-api-v2.md`

### Objectif
Transformer les données de formulaire React en un objet JSON de 38 champs respectant strictement le schéma Pydantic `InputData` (alias français, types entiers/flottants et absence de champs superflus).

### Modifications prévues
- Dans `interface/src/services/predictionService.js` :
  - Créer des tables de conversion d'index entiers :
    - `jour_semaine` (1 = Monday ... 7 = Sunday)
    - `heure` (0..23)
    - `periode_journee` (1 = matin, 2 = apres_midi, 3 = soir, 4 = nuit)
    - `categorie_vehicule` (0 = Véhicules légers ... 8 = Rail / tramway)
    - `type_choc` (0 = Aucun, 1 = Frontal, 2 = Arriere, 3 = Lateral, 4 = Multiple, 5 = Inconnu)
    - `presence_obstacle_fixe` (0 = Non/Inconnu, 1 = Oui)
    - `type_obstacle` (0 = Aucun, 1 = Vehicule, 2 = Pieton, 3 = Animal, 4 = Autre/Inconnu)
    - `type_collision` (0 = Vehicule_vs_Vehicule, 1 = Vehicule_vs_Pieton, 2 = Seul_contre_Obstacle_Fixe, 3 = Autre/Multiple)
    - `age_conducteur` (float, ex: 35.0)
    - `vma` (float, ex: 50.0)
  - Retirer la clé `month` (car `predict_api_v2` dérive en interne `month` à partir de `mois`).
  - S'assurer que le JSON final ne contient **aucun champ supplémentaire** pour respecter `extra="forbid"`.

### Fichiers potentiellement concernés
- `interface/src/services/predictionService.js`

### Validation prévue
- Test d'appel cURL / Fetch vers `http://localhost:8009/predict` et obtention d'un statut HTTP `200 OK` avec la réponse `{"prediction": X, "probability": Y, "model_version": "..."}`.

### Message de commit proposé
`fix(interface): format prediction payload with exact pydantic aliases and integer codes`

---

## Étape 3 — Validation du Flux Authentification `auth_api` et Proxy JWT

### Objectif
Garantir que la chaîne d'authentification respecte la fiche `docs/operations/auth-api.md` et propage le jeton JWT valide vers `predict_api_v2`.

### Modifications prévues
- Dans `interface/src/services/predictionService.js` et `interface/server.js` :
  - S'assurer du format JSON de la requête `/login` : `{"username": "...", "password": "...", "token_type": "login"}`.
  - S'assurer que l'en-tête `Authorization: Bearer <token>` est correctement injecté dans la requête transmise à `predict_api_v2`.
  - Harmoniser le comportement en cas de réponse 401 de `auth_api` (retour de l'erreur au client React).

### Fichiers potentiellement concernés
- `interface/server.js`
- `interface/src/services/predictionService.js`

### Validation prévue
- Exécution de la commande de validation de la doc opérationnelle :
  ```bash
  curl -sS -X POST http://localhost:8005/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"alice","password":"wonderland","token_type":"login"}'
  ```
- Vérification que le jeton retourné permet d'interroger `http://localhost:8009/predict` avec un statut HTTP 200.

### Message de commit proposé
`feat(interface): enforce auth_api login schema and jwt bearer propagation`

---

## Étape 4 — Test d'Intégration Global E2E (Interface + Stack APIs v2)

### Objectif
Valider l'ensemble du parcours utilisateur sur l'interface graphique connectée à la stack DockerCompose `docker-compose.apis.yml`.

### Modifications prévues
- Dans `interface/src/components/PredictionResult.jsx` :
  - S'assurer de l'affichage de la version du modèle (`model_version`) et du statut de la prédiction (`remote_api` vs `mlops_emergency_engine`).

### Fichiers potentiellement concernés
- `interface/src/components/PredictionResult.jsx`
- `interface/src/App.jsx`

### Validation prévue
- Démarrage de la stack avec `docker compose -f docker-compose.apis.yml up -d auth-api predict-api-v2 emergency-interface`.
- Connexion dans l'interface React, saisie d'un cas d'accident, soumission et vérification de la réception de la prédiction depuis BentoML sans basculement sur le moteur d'urgence.

### Message de commit proposé
`test(interface): validate end-to-end integration between interface, auth-api and predict-api-v2`

---

## Critères de fin
- Le fichier `modalite_variable.md` est supprimé du dépôt pour éviter tout conflit lors du merge sur `main`.
- La charge utile de prédiction est 100% conforme au contrat `docs/operations/predict-api-v2.md` (38 champs, alias français, types entiers/flottants, 0 champ superflu).
- `auth_api` délivre le token `login` sans erreur 400.
- `predict_api_v2` retourne HTTP 200 avec la prédiction et la version du modèle BentoML.
- Le test E2E depuis l'interface web est validé avec succès.
