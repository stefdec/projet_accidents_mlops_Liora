/**
 * Configuration des connexions d'APIs pour l'interface de régulation
 */
export const API_CONFIG = {
  // L'API hôte pour l'authentification
  authUrl: import.meta.env.VITE_AUTH_API_URL || '/api/auth/token',
  // L'API de prédiction v2
  predictUrl: import.meta.env.VITE_PREDICT_API_URL || '/api/predict',
  // Mode direct sans passer par le proxy Node.js (si configuré)
  directAuthUrl: 'http://localhost:8005/login',
  directPredictUrl: 'http://localhost:8009/predict',
};
