import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import LoginView from './components/LoginView';
import CaracteristiquesZone from './components/zones/CaracteristiquesZone';
import LieuxZone from './components/zones/LieuxZone';
import VehiculesZone from './components/zones/VehiculesZone';
import UsagersZone from './components/zones/UsagersZone';
import PredictionResult from './components/PredictionResult';
import DispatchSecours from './components/DispatchSecours';
import { getDayPeriodFromHour, getDayOfWeekName } from './config/constants';
import { authenticateWithHost, sendPredictionRequest } from './services/predictionService';

export default function App() {
  const [user, setUser] = useState(null);
  const [credentials, setCredentials] = useState(null);
  const [authError, setAuthError] = useState(null);

  // Thème Sombre / Clair (Sombre par défaut pour régulateurs)
  const [isDark, setIsDark] = useState(true);

  // Date et heure d'ouverture de l'application / du sinistre
  const [openingTime, setOpeningTime] = useState(new Date());

  // État de prédiction
  const [predictionResult, setPredictionResult] = useState(null);
  const [isPredicting, setIsPredicting] = useState(false);
  const [predictError, setPredictError] = useState(null);

  // Initialisation automatique des variables d'appel
  const generateInitialValues = (baseDate = new Date()) => {
    const currentHour = baseDate.getHours();
    return {
      Num_Acc: Number(`${baseDate.getFullYear()}${Math.floor(10000 + Math.random() * 90000)}`),
      year: baseDate.getFullYear(),
      mois: baseDate.getMonth() + 1,
      day_of_week: getDayOfWeekName(baseDate),
      hour: currentHour,
      day_period: getDayPeriodFromHour(currentHour),
      lum: 1, // Plein jour
      atm: 1, // Normale (actualisé automatiquement par Open-Meteo)
      col: 1,
      type_crash: "Vehicule_vs_Vehicule",

      catr: 4, // Voie communale
      agg: 2, // En agglomération
      vma: 4, // 50 km/h
      circ: 2, // Bidirectionnelle
      prof: 1, // Plat
      surf: 1, // Normale (sèche)
      infra: 0, // Aucun
      situ: 1, // Sur chaussée
      vosp: 0,
      lat: 48.8566,
      long: 2.3522,

      nb_vehicules: 1,
      catv_group_code: 1,
      catv_group: "Véhicules légers",
      motor: 1,
      manv: 1,
      macro_choc: "Frontal",
      choc: 1,
      presence_obstacle_fixe: "Non/Inconnu",
      macro_obsm_code: 1,
      macro_obsm: "Vehicule",

      catv_b_group_code: 1,
      macro_choc_b: "Frontal",
      choc_b: 1,

      catu: 1, // Conducteur
      sexe: 1, // Masculin
      age: 34,
      place: 1,
      secu1: 1, // Ceinture
      secu2: 0,
      secu3: 0,
      plusieurs_victimes: false,
      nb_victimes_accident: 1,
      catu2: 2, // Passager
      sexe2: 2, // Féminin
      age2: 28,
      place2: 2,
      secu1_2: 1, // Ceinture
      locp2: 0,
      actp2: 0,
      etatp2: 0,
      locp: 0,
      actp: 0,
      etatp: 0,
    };
  };

  const [formValues, setFormValues] = useState(generateInitialValues(openingTime));

  // Onglet actif : 'principal' (Zone 1 + 2) ou 'details' (Zone 3 + 4)
  const [activeTab, setActiveTab] = useState('principal');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const toggleTheme = () => {
    setIsDark(prev => !prev);
  };

  const handleFieldChange = (field, value) => {
    setFormValues(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleLogin = async (username, password) => {
    try {
      setAuthError(null);
      const token = await authenticateWithHost(username, password);
      setUser(username);
      setCredentials({ username, password, token });
    } catch (err) {
      setAuthError(err.message || 'Identifiants invalides');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setCredentials(null);
    setPredictionResult(null);
  };

  const handleSendPrediction = async () => {
    if (!credentials) return;
    setIsPredicting(true);
    setPredictError(null);

    // Application des fallbacks automatiques pour les champs vides de la Zone Lieux & Environnement
    const payloadWithFallbacks = {
      ...formValues,
      catr: formValues.catr !== "" && formValues.catr !== undefined ? formValues.catr : 9, // autre voie
      atm: formValues.atm !== "" && formValues.atm !== undefined ? formValues.atm : 1, // normale
      surf: formValues.surf !== "" && formValues.surf !== undefined ? formValues.surf : 1, // normale (sèche)
      circ: formValues.circ !== "" && formValues.circ !== undefined ? formValues.circ : 0, // non renseigné / autre
      infra: formValues.infra !== "" && formValues.infra !== undefined ? formValues.infra : 0, // aucun aménagement particulier
      situ: formValues.situ !== "" && formValues.situ !== undefined ? formValues.situ : 8, // autre situation
    };

    try {
      const result = await sendPredictionRequest(payloadWithFallbacks, credentials);
      setPredictionResult(result);
    } catch (err) {
      setPredictError(err.message || "Erreur lors de l'appel au modèle de prédiction");
    } finally {
      setIsPredicting(false);
    }
  };

  const handleResetForm = () => {
    const freshDate = new Date();
    setOpeningTime(freshDate);
    setFormValues(generateInitialValues(freshDate));
    setPredictionResult(null);
    setPredictError(null);
  };

  // Page 1 : Authentification
  if (!user) {
    return <LoginView onLogin={handleLogin} error={authError} />;
  }

  // Page 2 : Écran de régulation d'urgence (Répartition sur 2 Onglets + Action & Prédiction Figées)
  return (
    <div className="min-h-screen flex flex-col justify-between transition-colors duration-200">
      {/* HEADER : Date/Heure temps réel en français, Bienvenue user, Thème */}
      <Header
        user={user}
        onLogout={handleLogout}
        isDark={isDark}
        toggleTheme={toggleTheme}
      />

      {/* CORPS PRINCIPAL : BARRE D'ONGLETS + CONTENU DE L'ONGLET SÉLECTIONNÉ */}
      <main className="flex-1 max-w-[1780px] w-full mx-auto p-3 flex flex-col space-y-3">
        {predictError && (
          <div className="bg-red-100 dark:bg-red-950/80 border border-red-500 text-red-900 dark:text-red-200 text-xs p-2.5 rounded-xl flex items-center justify-between shadow-sm">
            <span>{predictError}</span>
            <button onClick={() => setPredictError(null)} className="font-bold underline text-red-700 dark:text-white">Fermer</button>
          </div>
        )}

        {/* BARRE D'ONGLETS STYLISÉE */}
        <div className="flex items-center justify-between bg-slate-200/80 dark:bg-slate-900/80 p-1.5 rounded-xl border border-slate-300 dark:border-slate-800 backdrop-blur-sm">
          <div className="flex items-center space-x-2 flex-1 max-w-2xl">
            <button
              type="button"
              onClick={() => setActiveTab('principal')}
              className={`flex-1 py-2.5 px-4 rounded-lg font-black text-xs uppercase tracking-wider transition-all flex items-center justify-center space-x-2 shadow-sm ${
                activeTab === 'principal'
                  ? 'bg-gradient-to-r from-red-600 to-amber-600 text-white border border-amber-400/40 shadow-md ring-2 ring-amber-500/20 scale-[1.01]'
                  : 'bg-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-300/50 dark:hover:bg-slate-800/50'
              }`}
            >
              <span className="text-base">📋</span>
              <span>1. Principal</span>
              <span className="text-[10px] font-normal opacity-80 lowercase font-sans">
                (Caractéristiques & Lieux)
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('details')}
              className={`flex-1 py-2.5 px-4 rounded-lg font-black text-xs uppercase tracking-wider transition-all flex items-center justify-center space-x-2 shadow-sm ${
                activeTab === 'details'
                  ? 'bg-gradient-to-r from-blue-600 to-emerald-600 text-white border border-emerald-400/40 shadow-md ring-2 ring-emerald-500/20 scale-[1.01]'
                  : 'bg-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-300/50 dark:hover:bg-slate-800/50'
              }`}
            >
              <span className="text-base">🚗</span>
              <span>2. Détails</span>
              <span className="text-[10px] font-normal opacity-80 lowercase font-sans">
                (Véhicules & Usagers)
              </span>
            </button>
          </div>

          <div className="hidden md:flex items-center space-x-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400 px-3">
            <span>Numéro d'intervention :</span>
            <span className="font-mono font-bold text-red-500">#{formValues.Num_Acc || '2026-001'}</span>
          </div>
        </div>

        {/* AFFICHAGE CONDITIONNEL SELON L'ONGLET ACTIF */}
        <div className="flex-1">
          {/* ONGLET 1 : PRINCIPAL (Caractéristiques ~35% / Lieux ~65%) */}
          {activeTab === 'principal' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch animate-fadeIn">
              <div className="lg:col-span-4 flex flex-col">
                <CaracteristiquesZone
                  formValues={formValues}
                  onChange={handleFieldChange}
                  openingTime={openingTime}
                />
              </div>

              <div className="lg:col-span-8 flex flex-col">
                <LieuxZone
                  formValues={formValues}
                  onChange={handleFieldChange}
                  openingTime={openingTime}
                />
              </div>
            </div>
          )}

          {/* ONGLET 2 : DÉTAILS (Véhicules 50% / Usagers 50%) */}
          {activeTab === 'details' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch animate-fadeIn">
              <div className="lg:col-span-6 flex flex-col">
                <VehiculesZone
                  formValues={formValues}
                  onChange={handleFieldChange}
                />
              </div>

              <div className="lg:col-span-6 flex flex-col">
                <UsagersZone
                  formValues={formValues}
                  onChange={handleFieldChange}
                />
              </div>
            </div>
          )}
        </div>

        {/* ZONE ACTION & PRÉDICTION (FIGÉE & PERMANENTE SUR LES 2 ONGLETS) */}
        <div className="w-full pt-2">
          <PredictionResult
            result={predictionResult}
            isLoading={isPredicting}
            onSendPrediction={handleSendPrediction}
          />
        </div>
      </main>

      {/* BAS DE PAGE : Mobilisation Secours & Nouveau Sinistre */}
      <DispatchSecours
        hasPredicted={!!predictionResult}
        onResetForm={handleResetForm}
      />
    </div>
  );
}
