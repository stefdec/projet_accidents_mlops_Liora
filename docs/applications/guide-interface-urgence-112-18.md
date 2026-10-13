# Interface emergency-interface

L’application React/Vite est servie par Express sur http://localhost:3001, dans la stack démarrée par `make stack-up`. Pour développer localement :

```bash
cd interface
npm ci
npm run build
npm start
```

Les API doivent être disponibles sur les URLs configurées. Le serveur Docker utilise auth-api:8000/login et predict-api:8000/predict. En local, les défauts pointent sur les ports hôte 8005 et 8009.

La connexion passe par POST /api/auth/token. Utiliser un compte présent dans USERS (le compte d’exemple est dans .env.example). Le frontend transforme les champs du formulaire en entrées numériques BAAC, puis appelle POST /api/predict avec le Bearer JWT. Express transmet le payload enveloppé dans input_data à BentoML.

Le résultat distant porte status=remote_api, prediction, probability et model_version. Une erreur HTTP distante est propagée ; une exception réseau peut basculer vers le secours heuristique. La disponibilité du frontend seule ne valide donc pas le modèle. `make predict-smoke` vérifie l’API directe ; la validation de stack vérifie aussi le proxy.

L’interface conserve deux onglets : caractéristiques/lieux et véhicules/usagers, carte Leaflet, modélisateurs Three.js, thèmes et remise à zéro du formulaire. Les services cartographiques externes et parcours visuels doivent être vérifiés sur navigateur ; ils ne sont pas prouvés par le smoke HTTP.

Ne pas diffuser les JWT/credentials ou journaux sensibles. Les dépendances npm restent verrouillées ; les vulnérabilités signalées par npm sont documentées dans le bilan de validation, sans upgrade majeur automatique.
