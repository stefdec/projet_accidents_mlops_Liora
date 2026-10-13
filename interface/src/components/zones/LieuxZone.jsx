import React from 'react';
import { MapPin, Navigation, AlertTriangle, CloudRain, Sun } from 'lucide-react';
import SpeedSign from '../SpeedSign';
import OpenStreetMapViewer from '../OpenStreetMapViewer';
import {
  CATR_OPTIONS,
  AGG_OPTIONS,
  CIRC_OPTIONS,
  PROF_OPTIONS,
  SURF_OPTIONS,
  INFRA_OPTIONS,
  SITU_OPTIONS,
  ATM_OPTIONS,
  getAutoSpeedLimit,
  getAutoRoadType,
} from '../../config/constants';

export default function LieuxZone({ formValues, onChange, openingTime }) {
  // Gestion de la sélection sur la carte OpenStreetMap
  const handleMapLocationSelect = ({ lat, long, catr, vma, agg }) => {
    onChange('lat', lat);
    onChange('long', long);
    if (catr) onChange('catr', catr);
    if (vma) onChange('vma', vma);
    if (agg) onChange('agg', agg);
  };

  // Mise à jour de la météo depuis Open-Meteo
  const handleWeatherUpdate = (atmCode, weatherData) => {
    if (atmCode) {
      onChange('atm', atmCode);
    }
  };

  // Association automatique Route <-> VMA
  const handleRoadChange = (newCatr) => {
    onChange('catr', newCatr);
    const suggestedVma = getAutoSpeedLimit(newCatr, formValues.agg);
    if (suggestedVma) {
      onChange('vma', suggestedVma);
    }
  };

  const handleAggChange = (newAgg) => {
    onChange('agg', newAgg);
    const suggestedVma = getAutoSpeedLimit(formValues.catr, newAgg);
    if (suggestedVma) {
      onChange('vma', suggestedVma);
    }
  };

  const handleVmaChange = (newVma) => {
    onChange('vma', newVma);
    const suggestedRoad = getAutoRoadType(newVma);
    if (suggestedRoad && formValues.catr !== suggestedRoad) {
      onChange('catr', suggestedRoad);
    }
  };

  return (
    <div className="zone-lieux p-3 rounded-xl border border-amber-500/40 shadow-sm flex flex-col space-y-3">
      {/* Entête Catégorie 2 */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-1.5">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-md bg-amber-600/20 text-amber-500 flex items-center justify-center border border-amber-500/40">
            <MapPin className="w-4 h-4" />
          </div>
          <h2 className="text-xs font-black uppercase tracking-wider text-amber-600 dark:text-amber-400">
            2. Lieux & Environnement
          </h2>
        </div>
        <span className="text-[11px] text-amber-600 dark:text-amber-400 font-bold font-mono">
          {formValues.agg === 2 ? "Zone Urbaine" : "Rase Campagne"}
        </span>
      </div>

      {/* CARTE OPENSTREETMAP + GÉOLOCALISATION + OPEN-METEO + SIMULATION GEOJSON ÉCLAIRAGE */}
      <OpenStreetMapViewer
        latitude={formValues.lat || 48.8566}
        longitude={formValues.long || 2.3522}
        openingTime={openingTime}
        onLocationSelect={handleMapLocationSelect}
        onWeatherUpdate={handleWeatherUpdate}
        onLightingUpdate={(lumCode) => onChange('lum', lumCode)}
      />

      {/* Agglomération (Boutons directs) + VMA (Panneaux routiers) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 pt-1 items-center">
        {/* Agglomération direct */}
        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
            Localisation (Critique)
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            {AGG_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleAggChange(opt.value)}
                className={`py-2 px-1 rounded-lg border text-xs font-black transition flex items-center justify-center ${
                  formValues.agg === opt.value
                    ? 'bg-amber-500 text-slate-950 border-amber-400 shadow-md ring-1 ring-amber-300'
                    : 'card-lieux text-slate-800 dark:text-slate-200 hover:border-amber-400'
                }`}
              >
                <span>{opt.text}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Panneaux VMA (Prend 2 colonnes) */}
        <div className="lg:col-span-2">
          <SpeedSign value={formValues.vma} onChange={handleVmaChange} />
        </div>
      </div>

      {/* Ligne Catégorie de Route + Atmosphère (Météo) + État Chaussée */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-1">
        {/* Type de voie */}
        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
            <Navigation className="w-3.5 h-3.5 text-amber-500" />
            <span>Type de voie</span>
          </label>
          <select
            value={formValues.catr !== undefined ? formValues.catr : ""}
            onChange={(e) => handleRoadChange(e.target.value === "" ? "" : Number(e.target.value))}
            className="card-lieux px-2 py-2 text-xs text-slate-900 dark:text-slate-100 focus:border-amber-500 font-medium"
          >
            <option value="">-- Non renseigné (à compléter) --</option>
            {CATR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.text}
              </option>
            ))}
          </select>
        </div>

        {/* Atmosphère / Météo */}
        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
            <CloudRain className="w-3.5 h-3.5 text-blue-500" />
            <span>Conditions météo</span>
          </label>
          <select
            value={formValues.atm !== undefined ? formValues.atm : ""}
            onChange={(e) => onChange('atm', e.target.value === "" ? "" : Number(e.target.value))}
            className="card-lieux px-2 py-2 text-xs text-slate-900 dark:text-slate-100 focus:border-amber-500 font-medium"
          >
            <option value="">-- Non renseigné (à compléter) --</option>
            {ATM_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.text}
              </option>
            ))}
          </select>
        </div>

        {/* État chaussée */}
        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            <span>État chaussée</span>
          </label>
          <select
            value={formValues.surf !== undefined ? formValues.surf : ""}
            onChange={(e) => onChange('surf', e.target.value === "" ? "" : Number(e.target.value))}
            className="card-lieux px-2 py-2 text-xs text-slate-900 dark:text-slate-100 focus:border-amber-500 font-medium"
          >
            <option value="">-- Non renseigné (à compléter) --</option>
            {SURF_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.text}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Régime de circulation, Aménagement, Situation sur voie */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-1">
        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
            <span className="text-xs">🔄</span>
            <span>Régime circulation</span>
          </label>
          <select
            value={formValues.circ !== undefined ? formValues.circ : ""}
            onChange={(e) => onChange('circ', e.target.value === "" ? "" : Number(e.target.value))}
            className="card-lieux px-2 py-2 text-xs text-slate-900 dark:text-slate-100 focus:border-amber-500 font-medium"
          >
            <option value="">-- Non renseigné (à compléter) --</option>
            {CIRC_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.text}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
            <span className="text-xs">🏗️</span>
            <span>Aménagement</span>
          </label>
          <select
            value={formValues.infra !== undefined ? formValues.infra : ""}
            onChange={(e) => onChange('infra', e.target.value === "" ? "" : Number(e.target.value))}
            className="card-lieux px-2 py-2 text-xs text-slate-900 dark:text-slate-100 focus:border-amber-500 font-medium"
          >
            <option value="">-- Non renseigné (à compléter) --</option>
            {INFRA_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.text}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col space-y-1">
          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
            <span className="text-xs">📍</span>
            <span>Situation sur voie</span>
          </label>
          <select
            value={formValues.situ !== undefined ? formValues.situ : ""}
            onChange={(e) => onChange('situ', e.target.value === "" ? "" : Number(e.target.value))}
            className="card-lieux px-2 py-2 text-xs text-slate-900 dark:text-slate-100 focus:border-amber-500 font-medium"
          >
            <option value="">-- Non renseigné (à compléter) --</option>
            {SITU_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.text}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
