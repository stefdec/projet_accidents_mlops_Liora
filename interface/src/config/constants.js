/**
 * Dictionnaire officiel des données BAAC et variables InputData
 * Chaque modalité comporte strictement une valeur numérique (value) et son libellé explicite (text).
 */

// --- CATÉGORIE 1 : CARACTÉRISTIQUES (ROUGE) ---

export const LUM_OPTIONS = [
  { value: 1, text: "Plein jour", icon: "☀️", short: "Plein jour" },
  { value: 2, text: "Crépuscule ou aube", icon: "🌅", short: "Crépuscule/Aube" },
  { value: 3, text: "Nuit sans éclairage public", icon: "🌑", short: "Nuit s/ éclairage" },
  { value: 4, text: "Nuit avec éclairage public non allumé", icon: "💡🚫", short: "Écl. non allumé" },
  { value: 5, text: "Nuit avec éclairage public allumé", icon: "💡✨", short: "Écl. allumé" },
];

export const ATM_OPTIONS = [
  { value: 1, text: "Normale" },
  { value: 2, text: "Pluie légère" },
  { value: 3, text: "Pluie forte" },
  { value: 4, text: "Neige / Grêle" },
  { value: 5, text: "Brouillard / Fumée" },
  { value: 6, text: "Vent fort / Tempête" },
  { value: 7, text: "Temps éblouissant" },
  { value: 8, text: "Temps couvert" },
  { value: 9, text: "Autre" },
];

export const COL_OPTIONS = [
  { value: 1, text: "Deux véhicules - Frontale" },
  { value: 2, text: "Deux véhicules - Par l'arrière" },
  { value: 3, text: "Deux véhicules - Par le côté" },
  { value: 4, text: "Trois véhicules et plus - En chaîne" },
  { value: 5, text: "Trois véhicules et plus - Collisions multiples" },
  { value: 6, text: "Autre collision" },
  { value: 7, text: "Sans collision" },
];

export const TYPE_CRASH_OPTIONS = [
  { value: 1, text: "Véhicule vs Véhicule", key: "Vehicule_vs_Vehicule" },
  { value: 2, text: "Véhicule vs Piéton", key: "Vehicule_vs_Pieton" },
  { value: 3, text: "Seul contre Obstacle Fixe", key: "Seul_contre_Obstacle_Fixe" },
  { value: 4, text: "Autre / Multiple", key: "Autre/Multiple" },
];

export const DAY_PERIOD_OPTIONS = [
  { value: 1, text: "Nuit (00h-06h)", key: "nuit" },
  { value: 2, text: "Matin (06h-12h)", key: "matin" },
  { value: 3, text: "Après-midi (12h-18h)", key: "apres_midi" },
  { value: 4, text: "Soir (18h-00h)", key: "soir" },
];

export const DAYS_OF_WEEK = [
  { value: 1, text: "Lundi", key: "Monday" },
  { value: 2, text: "Mardi", key: "Tuesday" },
  { value: 3, text: "Mercredi", key: "Wednesday" },
  { value: 4, text: "Jeudi", key: "Thursday" },
  { value: 5, text: "Vendredi", key: "Friday" },
  { value: 6, text: "Samedi", key: "Saturday" },
  { value: 7, text: "Dimanche", key: "Sunday" },
];

// --- CATÉGORIE 2 : LIEUX (JAUNE) ---

export const CATR_OPTIONS = [
  { value: 1, text: "Autoroute" },
  { value: 2, text: "Route nationale" },
  { value: 3, text: "Route départementale" },
  { value: 4, text: "Voie communale" },
  { value: 5, text: "Hors réseau public" },
  { value: 6, text: "Parc de stationnement" },
  { value: 7, text: "Routes métropolitaines" },
  { value: 9, text: "Autre route" },
];

export const AGG_OPTIONS = [
  { value: 1, text: "Hors agglomération" },
  { value: 2, text: "En agglomération" },
];

export const VMA_OPTIONS = [
  { value: 1, speed: 10, text: "10 km/h (Zone apaisée/piétonne)" },
  { value: 2, speed: 20, text: "20 km/h (Zone de rencontre)" },
  { value: 3, speed: 30, text: "30 km/h (Zone 30)" },
  { value: 4, speed: 50, text: "50 km/h (Agglomération standard)" },
  { value: 5, speed: 70, text: "70 km/h (Voie rapide urbaine)" },
  { value: 6, speed: 80, text: "80 km/h (Route secondaire)" },
  { value: 7, speed: 90, text: "90 km/h (Chaussée séparée / dérog.)" },
  { value: 8, speed: 110, text: "110 km/h (Voie express 2x2)" },
  { value: 9, speed: 130, text: "130 km/h (Autoroute)" },
];

export const CIRC_OPTIONS = [
  { value: 0, text: "Non renseigné / Autre" },
  { value: 1, text: "À sens unique" },
  { value: 2, text: "Bidirectionnelle" },
  { value: 3, text: "À chaussées séparées" },
  { value: 4, text: "Voies d'affectation variable" },
];

export const PROF_OPTIONS = [
  { value: 1, text: "Plat" },
  { value: 2, text: "Pente" },
  { value: 3, text: "Sommet de côte" },
  { value: 4, text: "Bas de côte" },
];

export const SURF_OPTIONS = [
  { value: 1, text: "Normale (sèche)" },
  { value: 2, text: "Mouillée" },
  { value: 3, text: "Flaques" },
  { value: 4, text: "Inondée" },
  { value: 5, text: "Enneigée" },
  { value: 6, text: "Boue" },
  { value: 7, text: "Verglacée" },
  { value: 8, text: "Corps gras / Huile" },
  { value: 9, text: "Autre" },
];

export const INFRA_OPTIONS = [
  { value: 0, text: "Aucun aménagement particulier" },
  { value: 1, text: "Souterrain / Tunnel" },
  { value: 2, text: "Pont / Viaduc" },
  { value: 3, text: "Bretelle d'échangeur" },
  { value: 4, text: "Voie ferrée" },
  { value: 5, text: "Carrefour aménagé / Giratoire" },
  { value: 6, text: "Zone piétonne" },
  { value: 7, text: "Péage" },
  { value: 8, text: "Chantier" },
  { value: 9, text: "Autres" },
];

export const SITU_OPTIONS = [
  { value: 1, text: "Sur chaussée" },
  { value: 2, text: "Sur bande d'arrêt d'urgence" },
  { value: 3, text: "Sur accotement" },
  { value: 4, text: "Sur trottoir" },
  { value: 5, text: "Sur piste cyclable" },
  { value: 6, text: "Sur aménagement particulier" },
  { value: 8, text: "Autre situation" },
];

export const VOSP_OPTIONS = [
  { value: 0, text: "Aucune voie réservée" },
  { value: 1, text: "Piste cyclable" },
  { value: 2, text: "Bande cyclable" },
  { value: 3, text: "Voie réservée bus / taxi" },
];

// --- CATÉGORIE 3 : VÉHICULES (BLEU) ---

export const CATV_GROUP_OPTIONS = [
  { value: 1, text: "Véhicules légers (Voitures / SUV)", key: "Véhicules légers", model: "car" },
  { value: 2, text: "Deux-roues motorisés (Motos)", key: "Deux-roues motorisés", model: "moto" },
  { value: 3, text: "Vélo / VAE (Mobilité douce)", key: "Mobilités douces / individuelles", model: "velo" },
  { value: 10, text: "Trottinette / EDPM (Mobilité douce)", key: "Mobilités douces / individuelles", model: "trottinette" },
  { value: 4, text: "Utilitaires (VUL)", key: "Utilitaires", model: "truck" },
  { value: 5, text: "Poids lourds / Marchandises", key: "Poids lourds / marchandises", model: "truck" },
  { value: 6, text: "Transport collectif (Bus / Autocar)", key: "Transport collectif", model: "bus" },
  { value: 7, text: "Rail / Tramway", key: "Rail / tramway", model: "bus" },
  { value: 8, text: "Véhicules spéciaux / agricoles", key: "Véhicules spéciaux / agricoles", model: "truck" },
  { value: 9, text: "Autres / indéterminés", key: "Autres / indéterminés", model: "car" },
];

export const MOTOR_OPTIONS = [
  { value: 0, text: "Inconnu / Autre" },
  { value: 1, text: "Hydrocarbure (Essence / Diesel)" },
  { value: 2, text: "Hybride électrique" },
  { value: 3, text: "Électrique" },
  { value: 4, text: "Hydrogène" },
  { value: 5, text: "Humaine (Vélo)" },
  { value: 6, text: "Autre motorisation" },
];

export const MANV_OPTIONS = [
  { value: 0, text: "Inconnue / Sans précision" },
  { value: 1, text: "Sans changement de direction" },
  { value: 2, text: "Même sens, même file" },
  { value: 3, text: "Entre 2 files" },
  { value: 4, text: "En marche arrière" },
  { value: 5, text: "À contresens" },
  { value: 6, text: "En franchissant le terre-plein" },
  { value: 7, text: "Dans le couloir bus" },
  { value: 8, text: "En s'insérant dans la circulation" },
  { value: 9, text: "En faisant demi-tour sur la chaussée" },
  { value: 10, text: "En s'arrêtant" },
  { value: 11, text: "En stationnant" },
  { value: 12, text: "En ouvrant une portière" },
  { value: 13, text: "En bifurquant à gauche" },
  { value: 14, text: "En bifurquant à droite" },
  { value: 15, text: "En tournant à gauche" },
  { value: 16, text: "En tournant à droite" },
  { value: 17, text: "En dépassant à gauche" },
  { value: 18, text: "En dépassant à droite" },
  { value: 19, text: "En traversant la chaussée" },
  { value: 20, text: "Déport à gauche" },
  { value: 21, text: "Déport à droite" },
  { value: 22, text: "En évitant un obstacle" },
  { value: 23, text: "En changement de file" },
  { value: 24, text: "Autre manœuvre" },
  { value: 25, text: "Sur le trottoir" },
  { value: 26, text: "En faisant la course" },
];

export const MACRO_CHOC_OPTIONS = [
  { value: 1, text: "Choc frontal", key: "Frontal", code: 1 },
  { value: 2, text: "Choc arrière", key: "Arriere", code: 4 },
  { value: 3, text: "Choc latéral", key: "Lateral", code: 7 },
  { value: 4, text: "Chocs multiples / Carambolage", key: "Multiple", code: 9 },
  { value: 5, text: "Aucun choc direct / Tonneau", key: "Aucun", code: 0 },
  { value: 6, text: "Localisation inconnue", key: "Inconnu", code: -1 },
];

export const PREST_OBSTACLE_OPTIONS = [
  { value: 0, text: "Non / Inconnu", key: "Non/Inconnu" },
  { value: 1, text: "Oui (Arbre, Poteau, Glissière...)", key: "Oui" },
];

export const MACRO_OBSM_OPTIONS = [
  { value: 0, text: "Aucun obstacle mobile", key: "Aucun" },
  { value: 1, text: "Véhicule en mouvement", key: "Vehicule" },
  { value: 2, text: "Piéton", key: "Pieton" },
  { value: 3, text: "Animal", key: "Animal" },
  { value: 4, text: "Autre / Inconnu", key: "Autre/Inconnu" },
];

// --- CATÉGORIE 4 : USAGERS (VERT) ---

export const CATU_OPTIONS = [
  { value: 1, text: "Conducteur" },
  { value: 2, text: "Passager" },
  { value: 3, text: "Piéton" },
];

export const SEXE_OPTIONS = [
  { value: 1, text: "Masculin" },
  { value: 2, text: "Féminin" },
];

export const PLACE_OPTIONS = [
  { value: 1, text: "1 - Conducteur" },
  { value: 2, text: "2 - Passager avant droit" },
  { value: 3, text: "3 - Passager arrière droit" },
  { value: 4, text: "4 - Passager arrière gauche" },
  { value: 5, text: "5 - Passager arrière milieu" },
  { value: 6, text: "6 - Passager avant milieu" },
  { value: 7, text: "7 - Passager arrière gauche centre" },
  { value: 8, text: "8 - Passager arrière droit centre" },
  { value: 9, text: "9 - Autre passager" },
  { value: 10, text: "10 - Piéton (sans objet)" },
];

export const TRAJET_OPTIONS = [
  { value: 0, text: "Non renseigné / Autre" },
  { value: 1, text: "Domicile - Travail" },
  { value: 2, text: "Domicile - École" },
  { value: 3, text: "Courses / Achats" },
  { value: 4, text: "Utilisation professionnelle" },
  { value: 5, text: "Promenades / Loisirs" },
  { value: 9, text: "Autre motif" },
];

export const SECU_OPTIONS = [
  { value: 0, text: "Aucun équipement / Non renseigné" },
  { value: 1, text: "Ceinture de sécurité" },
  { value: 2, text: "Casque" },
  { value: 3, text: "Dispositif enfants" },
  { value: 4, text: "Gilet réfléchissant" },
  { value: 5, text: "Airbag (moto / 2-roues)" },
  { value: 6, text: "Gants" },
  { value: 7, text: "Gants + Airbag" },
  { value: 8, text: "Autre équipement" },
  { value: 9, text: "Équipement spécifique" },
];

export const LOCP_OPTIONS = [
  { value: 0, text: "Sans objet / Non piéton" },
  { value: 1, text: "Sur chaussée > 50m passage" },
  { value: 2, text: "Sur chaussée <= 50m passage" },
  { value: 3, text: "Sur passage sans feux" },
  { value: 4, text: "Sur passage avec feux" },
  { value: 5, text: "Sur trottoir" },
  { value: 6, text: "Sur accotement" },
  { value: 7, text: "Sur refuge / terre-plein" },
  { value: 8, text: "Sur contre-allée" },
  { value: 9, text: "Autre emplacement" },
];

export const ACTP_OPTIONS = [
  { value: 0, text: "Sans objet / Non renseigné" },
  { value: 1, text: "Sens des véhicules" },
  { value: 2, text: "Sens inverse" },
  { value: 3, text: "Traversant la chaussée" },
  { value: 4, text: "Masqué par obstacle" },
  { value: 5, text: "Jouant / Marchant" },
  { value: 6, text: "Sur véhicule tracté" },
  { value: 7, text: "Descendant du véhicule" },
  { value: 8, text: "Montant dans le véhicule" },
  { value: 9, text: "Autre action" },
];

export const ETATP_OPTIONS = [
  { value: 0, text: "Sans objet / Non renseigné" },
  { value: 1, text: "Seul" },
  { value: 2, text: "Accompagné" },
  { value: 3, text: "En groupe" },
];

// --- ASSOCIATIONS LOGIQUES AUTOMATIQUES ---

export function getAutoSpeedLimit(catr, agg) {
  if (catr === 1) return 9; // Autoroute -> 130 km/h
  if (catr === 7) return 8; // Route métropolitaine / voie rapide -> 110 km/h
  if (catr === 2) return agg === 2 ? 4 : 7; // Nationale -> 50 en agglo, 90 hors agglo
  if (catr === 3) return agg === 2 ? 4 : 6; // Départementale -> 50 en agglo, 80 hors agglo
  if (catr === 4) return agg === 2 ? 4 : 6; // Communale -> 50 en agglo, 80 hors agglo
  if (catr === 6) return 1; // Parking -> 10-20 km/h
  return agg === 2 ? 4 : 6;
}

export function getAutoRoadType(vmaCode) {
  if (vmaCode === 9) return 1; // 130 km/h -> Autoroute
  if (vmaCode === 8) return 1; // 110 km/h -> Autoroute / Voie express
  if (vmaCode === 7) return 2; // 90 km/h -> Nationale
  if (vmaCode === 6) return 3; // 80 km/h -> Départementale
  if (vmaCode === 4 || vmaCode === 3) return 4; // 50 ou 30 km/h -> Voie communale
  return 4;
}

export function getDayPeriodFromHour(hour) {
  const h = Number(hour);
  if (h >= 0 && h < 6) return "nuit";
  if (h >= 6 && h < 12) return "matin";
  if (h >= 12 && h < 18) return "apres_midi";
  return "soir";
}

export function getDayOfWeekName(date = new Date()) {
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  return days[date.getDay()];
}
