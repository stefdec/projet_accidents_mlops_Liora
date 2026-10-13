# Interface React/Express

Le guide maintenu est [emergency-interface](../docs/applications/guide-interface-urgence-112-18.md). Le backend est server.js, le frontend src/, le build Vite est généré dans dist/ et ignoré par Git.

Docker reconstruit le frontend avec npm ci, puis sert son build sur le port 3001. Les dépendances Leaflet et Three.js sont utilisées par la carte et les véhicules ; les appels externes carte/météo sont distincts de la prédiction MLOps.
