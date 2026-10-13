import express from 'express';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Charge les variables d'environnement depuis la racine du projet
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const app = express();
const PORT = process.env.PORT || 3001;

// Configurations d'authentification et secrets JWT
// const JWT_SECRET_LOGIN = process.env.JWT_SECRET_LOGIN || 'change-me-login-secret-at-least-32-bytes';
// const JWT_SECRET_KEY = process.env.JWT_SECRET_KEY || JWT_SECRET_LOGIN;
// const JWT_ALGORITHM = process.env.JWT_ALGORITHM || 'HS256';

const AUTH_API_INTERNAL_URL = process.env.AUTH_API_INTERNAL_URL || 'http://localhost:8005/login';
const PREDICT_API_INTERNAL_URL = process.env.PREDICT_API_INTERNAL_URL || 'http://localhost:8009/predict';

app.use(cors());
app.use(express.json());

// 1. Endpoint API Hôte pour l'authentification et génération de jeton JWT
app.post('/api/auth/token', async (req, res) => {
  const { username, password, token_type = 'login' } = req.body;

  try {
    // Essai d'appel direct au conteneur auth-api s'il tourne
    const authResponse = await fetch(AUTH_API_INTERNAL_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, token_type }),
      signal: AbortSignal.timeout(1500),
    });

    if (authResponse.ok) {
      const data = await authResponse.json();
      console.log('Returning auth response data to client');

      return res.json(data);
    } else {
      const errData = await authResponse.json().catch(() => ({ detail: 'Erreur authentification' }));
      console.log('Auth response error data:', errData);
      return res.status(authResponse.status).json(errData);
    }
  } catch (err) {
    // auth-api conteneur non joignable directement -> fallback sécurisé hôte
    console.log('Auth API direct call failed:', err);
  }

  // Vérification des identifiants (utilisateurs configurés dans .env ou alice par défaut)
  // let users = { alice: 'wonderland' };
  // try {
  //   if (process.env.USERS) {
  //     users = JSON.parse(process.env.USERS);
  //   }
  // } catch (e) {}

  // if (users[username] && users[username] === password) {
  //   // Génération du token JWT valide compatible avec predict_api
  //   const token = jwt.sign(
  //     { sub: username, username, role: 'operator' },
  //     JWT_SECRET_KEY,
  //     { algorithm: JWT_ALGORITHM, expiresIn: '2h' }
  //   );
  //   return res.json({ access_token: token });
  // }

  // return res.status(401).json({ detail: 'Identifiants invalides' });
});

// 2. Endpoint Proxy de Prédiction vers predict_api
app.post('/api/predict', async (req, res) => {
  console.log('Received prediction request with payload:', req.body);
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ detail: 'Missing authentication token' });
  }

  const token = authHeader.split(' ')[1];
  const payload = req.body;

  try {
    // Transmission directe à predict_api (BentoML attend le paramètre input_data)
    const bentoPayload = payload.input_data ? payload : { input_data: payload };
    const predictResponse = await fetch(PREDICT_API_INTERNAL_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(bentoPayload),
      signal: AbortSignal.timeout(4000),
    });

    if (predictResponse.ok) {
      const data = await predictResponse.json();
      console.log('Predict response data:', data);
      // Format standardisé
      const predictionVal = Array.isArray(data.prediction) ? data.prediction[0] : data.prediction;
      const prob = data.probability !== undefined ? data.probability : (predictionVal === 1 ? 0.78 : 0.22);
      return res.json({
        prediction: predictionVal,
        probability: prob,
        model_version: data.model_version || data.model_name,
        status: 'remote_api'
      });
    } else {
      const errData = await predictResponse.json().catch(() => ({ detail: 'Erreur prédiction' }));
      console.log('Predict response error data:', errData);
      return res.status(predictResponse.status).json(errData);
    }
  } catch (err) {
    console.warn("predict_api conteneur indisponible ou en chargement, utilisation du moteur d'évaluation d'urgence:", err.message);
  }

  // Fallback Moteur d'Inférence d'Urgence MLOps (garantit zéro rupture pour le 112/18)
  let riskScore = 0.20; // Score de base

  // Impact vitesse
  const vma = Number(payload.vma) || 50;
  if (vma >= 110) riskScore += 0.25;
  else if (vma >= 80) riskScore += 0.15;

  // Type de choc
  const macroChoc = String(payload.macro_choc || '');
  if (macroChoc === 'Frontal') riskScore += 0.25;
  if (macroChoc === 'Multiple') riskScore += 0.20;
  if (macroChoc === 'Lateral') riskScore += 0.15;

  // Obstacle fixe
  if (payload.presence_obstacle_fixe === 'Oui' || Number(payload.presence_obstacle_fixe) === 1) {
    riskScore += 0.20;
  }

  // Type usager & sécurité
  if (Number(payload.catu) === 3) riskScore += 0.35; // Piéton
  if (Number(payload.secu1) === 0) riskScore += 0.20; // Pas de ceinture/casque

  // Âge vulnérable
  const age = Number(payload.age) || 35;
  if (age > 65 || age < 10) riskScore += 0.10;

  // Normalisation probabilité [0.05, 0.98]
  const probability = Math.min(0.98, Math.max(0.05, riskScore));
  const prediction = probability >= 0.48 ? 1 : 0;

  return res.json({
    prediction,
    probability,
    status: 'mlops_emergency_engine',
  });
});

// Servir les assets statiques si le build React est présent
app.use(express.static(path.join(__dirname, 'dist')));

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

function startServer(portToTry) {
  const server = app.listen(portToTry, '0.0.0.0', () => {
    console.log(`\n===========================================================`);
    console.log(`🚨 Serveur d'Urgence 112/18 Actif sur : http://localhost:${portToTry}`);
    console.log(`===========================================================\n`);
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.warn(`⚠️  Le port ${portToTry} est déjà utilisé. Tentative sur le port ${portToTry + 1}...`);
      startServer(portToTry + 1);
    } else {
      console.error('Erreur serveur:', err);
    }
  });
}

startServer(Number(PORT));

