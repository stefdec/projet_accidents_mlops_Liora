import { API_CONFIG } from '../config/api';

/**
 * Service d'orchestration en 2 étapes conformément au cahier des charges :
 * 1. Appel à l'API hôte pour obtenir un token JWT
 * 2. Appel à l'API predict_api avec le token et la charge utile numérique
 */

export async function authenticateWithHost(username, password) {
  const response = await fetch(API_CONFIG.authUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username,
      password,
      token_type: 'login',
    }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || errData.error || `Erreur d'authentification (${response.status})`);
  }

  const data = await response.json();
  return data.access_token;
}

// Tables de correspondance BAAC vers index entiers stricts pour InputData (predict_api)
const DAY_OF_WEEK_MAP = {
  "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7,
  "Lundi": 1, "Mardi": 2, "Mercredi": 3, "Jeudi": 4, "Vendredi": 5, "Samedi": 6, "Dimanche": 7
};

const DAY_PERIOD_MAP = {
  "matin": 1, "apres_midi": 2, "soir": 3, "nuit": 4
};

const CATV_GROUP_MAP = {
  "Véhicules légers": 0,
  "Deux-roues motorisés": 1,
  "Mobilités douces / individuelles": 2,
  "Utilitaires": 3,
  "Poids lourds / marchandises": 4,
  "Transport collectif": 5,
  "Autres / indéterminés": 6,
  "Véhicules spéciaux / agricoles": 7,
  "Rail / tramway": 8
};

const MACRO_CHOC_MAP = {
  "Aucun": 0,
  "Frontal": 1,
  "Arriere": 2,
  "Lateral": 3,
  "Multiple": 4,
  "Inconnu": 5
};

const MACRO_OBSM_MAP = {
  "Aucun": 0,
  "Vehicule": 1,
  "Pieton": 2,
  "Animal": 3,
  "Autre/Inconnu": 4
};

const TYPE_CRASH_MAP = {
  "Vehicule_vs_Vehicule": 0,
  "Vehicule_vs_Pieton": 1,
  "Seul_contre_Obstacle_Fixe": 2,
  "Autre/Multiple": 3
};

const VMA_SPEED_MAP = {
  1: 10, 2: 20, 3: 30, 4: 50, 5: 70, 6: 80, 7: 90, 8: 110, 9: 130
};

export function formatNumericPayload(formValues) {
  // 1. Détermination du jour de la semaine (1..7)
  let jourSemaineVal = 1;
  if (typeof formValues.day_of_week === 'number') {
    jourSemaineVal = Math.min(7, Math.max(1, formValues.day_of_week));
  } else if (DAY_OF_WEEK_MAP[formValues.day_of_week]) {
    jourSemaineVal = DAY_OF_WEEK_MAP[formValues.day_of_week];
  }

  // 2. Détermination de la période de la journée (1..4)
  let periodeJourneeVal = 2; // apres_midi par défaut
  if (typeof formValues.day_period === 'number') {
    periodeJourneeVal = Math.min(4, Math.max(1, formValues.day_period));
  } else if (DAY_PERIOD_MAP[formValues.day_period]) {
    periodeJourneeVal = DAY_PERIOD_MAP[formValues.day_period];
  }

  // 3. Catégorie de véhicule (0..8)
  let catvGroupVal = 0;
  if (typeof formValues.catv_group_code === 'number' && formValues.catv_group_code >= 0 && formValues.catv_group_code <= 8) {
    catvGroupVal = formValues.catv_group_code;
  } else if (typeof formValues.catv_group === 'number') {
    catvGroupVal = formValues.catv_group;
  } else if (CATV_GROUP_MAP[formValues.catv_group] !== undefined) {
    catvGroupVal = CATV_GROUP_MAP[formValues.catv_group];
  }

  // 4. Type de choc (0..5)
  let typeChocVal = 1; // Frontal par défaut
  if (typeof formValues.macro_choc === 'number') {
    typeChocVal = formValues.macro_choc;
  } else if (MACRO_CHOC_MAP[formValues.macro_choc] !== undefined) {
    typeChocVal = MACRO_CHOC_MAP[formValues.macro_choc];
  }

  // 5. Obstacle fixe (0..1)
  let presenceObstacleFixeVal = 0;
  if (formValues.presence_obstacle_fixe === 'Oui' || Number(formValues.presence_obstacle_fixe) === 1) {
    presenceObstacleFixeVal = 1;
  }

  // 6. Obstacle mobile (0..4)
  let typeObstacleVal = 1; // Vehicule par défaut
  if (typeof formValues.macro_obsm === 'number') {
    typeObstacleVal = formValues.macro_obsm;
  } else if (MACRO_OBSM_MAP[formValues.macro_obsm] !== undefined) {
    typeObstacleVal = MACRO_OBSM_MAP[formValues.macro_obsm];
  }

  // 7. Type de collision (0..3)
  let typeCollisionVal = 0; // Vehicule_vs_Vehicule par défaut
  if (typeof formValues.type_crash === 'number') {
    typeCollisionVal = formValues.type_crash;
  } else if (TYPE_CRASH_MAP[formValues.type_crash] !== undefined) {
    typeCollisionVal = TYPE_CRASH_MAP[formValues.type_crash];
  }

  // 8. Vitesse VMA (en km/h, float 0..130)
  let vmaVal = Number(formValues.vma) || 50;
  if (VMA_SPEED_MAP[vmaVal]) {
    vmaVal = VMA_SPEED_MAP[vmaVal];
  }
  vmaVal = Math.min(130, Math.max(0, vmaVal));

  // Transformation des 38 champs requis par InputData dans predict_api
  return {
    Num_Acc: Number(formValues.Num_Acc) || 2026001,
    place: Number(formValues.place) !== undefined ? Number(formValues.place) : 1,
    catu: Number(formValues.catu) || 1,
    sexe: Number(formValues.sexe) || 1,
    trajet: -1, //Number(formValues.trajet) == undefined ? Number(formValues.trajet) : -1,
    locp: Number(formValues.locp) !== undefined ? Number(formValues.locp) : 0,
    actp: Number(formValues.actp) !== undefined ? Number(formValues.actp) : 0,
    etatp: Number(formValues.etatp) !== undefined ? Number(formValues.etatp) : 0,
    manv: Number(formValues.manv) !== undefined ? Number(formValues.manv) : 1,
    catr: Number(formValues.catr) || 1,
    circ: Number(formValues.circ) !== undefined ? Number(formValues.circ) : 1,
    vosp: Number(formValues.vosp) !== undefined ? Number(formValues.vosp) : 0,
    prof: Number(formValues.prof) !== undefined ? Number(formValues.prof) : 1,
    surf: Number(formValues.surf) !== undefined ? Number(formValues.surf) : 1,
    infra: Number(formValues.infra) !== undefined ? Number(formValues.infra) : 0,
    situ: Number(formValues.situ) !== undefined ? Number(formValues.situ) : 1,
    mois: Number(formValues.mois) || (new Date().getMonth() + 1),
    lum: Number(formValues.lum) || 1,
    agg: Number(formValues.agg) || 1,
    atm: Number(formValues.atm) || 1,
    col: Number(formValues.col) || 1,
    lat: Number(formValues.lat) || 48.8566,
    long: Number(formValues.long) || 2.3522,
    year: Number(formValues.year) || new Date().getFullYear(),
    secu1: Number(formValues.secu1) !== undefined ? Number(formValues.secu1) : 1,
    secu2: Number(formValues.secu2) !== undefined ? Number(formValues.secu2) : 0,
    secu3: Number(formValues.secu3) !== undefined ? Number(formValues.secu3) : 0,
    motor: Number(formValues.motor) !== undefined ? Number(formValues.motor) : 1,
    vma: vmaVal,
    jour_semaine: jourSemaineVal,
    heure: Number(formValues.hour) !== undefined ? Number(formValues.hour) : new Date().getHours(),
    periode_journee: periodeJourneeVal,
    age_conducteur: Number(formValues.age) || 35,
    categorie_vehicule: catvGroupVal,
    type_choc: typeChocVal,
    presence_obstacle_fixe: presenceObstacleFixeVal,
    type_obstacle: typeObstacleVal,
    type_collision: typeCollisionVal,
  };
}

export async function sendPredictionRequest(formValues, credentials) {
  console.log('Sending prediction request with form values:', formValues);
  const startTime = Date.now();

  // ÉTAPE 1 : Appel à l'API hôte pour obtenir le token JWT
  let token;
  try {
    token = await authenticateWithHost(credentials.username, credentials.password);
  } catch (authErr) {
    console.warn("Échec token direct, utilisation du proxy ou jeton session:", authErr.message);
    token = credentials.token || "session-token";
  }

  // ÉTAPE 2 : Appel à l'API predict avec le token et les données numériques
  const numericPayload = formatNumericPayload(formValues);

  const response = await fetch(API_CONFIG.predictUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(numericPayload),
  });

  const latency = Date.now() - startTime;

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.error || `Erreur prédiction (${response.status})`);
  }

  const result = await response.json();
  return {
    ...result,
    latency,
  };
}
