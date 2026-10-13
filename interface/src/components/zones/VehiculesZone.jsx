import React, { useEffect } from 'react';
import { Car, ShieldAlert, Cpu } from 'lucide-react';
import Vehicle3DViewer from '../Vehicle3DViewer';
import {
  CATV_GROUP_OPTIONS,
  MOTOR_OPTIONS,
  MANV_OPTIONS,
  PREST_OBSTACLE_OPTIONS,
  MACRO_OBSM_OPTIONS,
  COL_OPTIONS,
} from '../../config/constants';

export default function VehiculesZone({ formValues, onChange }) {
  const nbVehicules = formValues.nb_vehicules || 1;
  const showTwoModelers = nbVehicules >= 2;

  // Ajustement automatique des obstacles mobiles selon le nombre de véhicules
  useEffect(() => {
    if (nbVehicules >= 2) {
      if (formValues.macro_obsm_code === undefined || formValues.macro_obsm_code === null) {
        onChange('macro_obsm_code', 1); // Véhicule en mouvement
        onChange('macro_obsm', 'Vehicule');
      }
    } else {
      if (formValues.macro_obsm_code === undefined || formValues.macro_obsm_code === null) {
        onChange('macro_obsm_code', 4); // Autre / Inconnu
        onChange('macro_obsm', 'Autre/Inconnu');
      }
    }
  }, [nbVehicules, formValues.macro_obsm_code, onChange]);

  const handleImpactA = (zoneKey, macroChoc, chocCode) => {
    onChange('macro_choc', macroChoc);
    onChange('choc', chocCode);
  };

  const handleImpactB = (zoneKey, macroChoc, chocCode) => {
    onChange('macro_choc_b', macroChoc);
    onChange('choc_b', chocCode);
  };

  return (
    <div className="zone-vehicules p-3 rounded-xl border border-blue-500/40 shadow-sm flex flex-col space-y-3">
      {/* Entête Catégorie 3 */}
      <div className="flex items-center justify-between border-b border-blue-500/20 pb-1.5">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-md bg-blue-600/20 text-blue-500 flex items-center justify-center border border-blue-500/40">
            <Car className="w-4 h-4" />
          </div>
          <h2 className="text-xs font-black uppercase tracking-wider text-blue-600 dark:text-blue-400">
            3. Véhicules & Chocs 3D
          </h2>
        </div>

        {/* Sélection du nombre de véhicules : 1, 2, ou 3+ Véhicules */}
        <div className="flex items-center space-x-1 bg-slate-200 dark:bg-slate-800/80 p-0.5 rounded-lg border border-blue-500/30">
          <button
            type="button"
            onClick={() => {
              onChange('nb_vehicules', 1);
              onChange('macro_obsm_code', 4);
              onChange('macro_obsm', 'Autre/Inconnu');
            }}
            className={`px-2.5 py-1 rounded-md text-xs font-bold transition ${
              nbVehicules === 1
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            1 Véhicule
          </button>
          <button
            type="button"
            onClick={() => {
              onChange('nb_vehicules', 2);
              onChange('macro_obsm_code', 1);
              onChange('macro_obsm', 'Vehicule');
            }}
            className={`px-2.5 py-1 rounded-md text-xs font-bold transition ${
              nbVehicules === 2
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            2 Véhicules
          </button>
          <button
            type="button"
            onClick={() => {
              onChange('nb_vehicules', 3);
              onChange('macro_obsm_code', 1);
              onChange('macro_obsm', 'Vehicule');
              if (!formValues.col || ![4, 5].includes(formValues.col)) {
                onChange('col', 4); // Carambolage par défaut
              }
            }}
            className={`px-2.5 py-1 rounded-md text-xs font-bold transition ${
              nbVehicules >= 3
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            3+ Véhicules
          </button>
        </div>
      </div>

      {/* Obstacle fixe : boutons directs apparents & indication si carambolage */}
      <div className="flex flex-wrap items-center justify-between bg-slate-200/50 dark:bg-slate-800/40 px-2.5 py-1.5 rounded-lg border border-blue-500/20 gap-2">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
            Obstacle Fixe Heurté ?
          </span>
          <div className="flex items-center space-x-1">
            {PREST_OBSTACLE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => onChange('presence_obstacle_fixe', opt.key)}
                className={`py-1 px-3 rounded-md border text-center text-xs font-black transition ${
                  formValues.presence_obstacle_fixe === opt.key
                    ? 'bg-blue-600 text-white border-blue-500 shadow-sm'
                    : 'card-vehicules text-slate-800 dark:text-slate-200 hover:border-blue-400'
                }`}
              >
                {opt.text}
              </button>
            ))}
          </div>
        </div>

        {nbVehicules >= 3 && (
          <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/30">
            3+ Véhicules (Modélisation des 2 véhicules principaux)
          </span>
        )}
      </div>

      {/* SOUS-MENU TYPE DE COLLISION SPÉCIFIQUE (SI 3+ VÉHICULES SELECTIONNES) */}
      {nbVehicules >= 3 && (
        <div className="p-2.5 bg-blue-50/80 dark:bg-blue-950/40 border border-blue-400/40 rounded-lg flex flex-col space-y-1.5 animate-fadeIn">
          <label className="text-[11px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-300">
            Type de collision (3+ Véhicules) :
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => onChange('col', 4)}
              className={`p-2 rounded-lg border text-left text-xs font-bold transition flex items-center justify-between ${
                formValues.col === 4
                  ? 'bg-blue-600 text-white border-blue-500 shadow-md ring-1 ring-blue-400'
                  : 'card-vehicules text-slate-800 dark:text-slate-200 hover:border-blue-400'
              }`}
            >
              <div>
                <div>Carambolage</div>
                <div className="text-[10px] font-normal opacity-80">(série de chocs successifs)</div>
              </div>
              <span className="text-xs font-mono font-bold ml-1">[Code 4]</span>
            </button>

            <button
              type="button"
              onClick={() => onChange('col', 5)}
              className={`p-2 rounded-lg border text-left text-xs font-bold transition flex items-center justify-between ${
                formValues.col === 5
                  ? 'bg-blue-600 text-white border-blue-500 shadow-md ring-1 ring-blue-400'
                  : 'card-vehicules text-slate-800 dark:text-slate-200 hover:border-blue-400'
              }`}
            >
              <div>
                <div>Accident en accordéon</div>
                <div className="text-[10px] font-normal opacity-80">(collisions multiples par l'arrière)</div>
              </div>
              <span className="text-xs font-mono font-bold ml-1">[Code 5]</span>
            </button>
          </div>
        </div>
      )}

      {/* ZONE MODÉLISATEURS 3D (Agrandie sur l'onglet 2) */}
      <div className={`grid gap-3 ${showTwoModelers ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
        {/* Colonne Véhicule A */}
        <div className="flex flex-col">
          <div className="mb-1 flex items-center justify-between px-1">
            <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <span>🚗</span>
              <span>Type de Véhicule A :</span>
            </label>
            <select
              value={formValues.catv_group_code || 1}
              onChange={(e) => {
                const code = Number(e.target.value);
                const opt = CATV_GROUP_OPTIONS.find(o => o.value === code);
                onChange('catv_group_code', code);
                onChange('catv_group', opt ? opt.key : "Véhicules légers");
              }}
              className="card-vehicules text-xs py-1 px-2 font-bold focus:border-blue-500"
            >
              {CATV_GROUP_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>
          <Vehicle3DViewer
            label="Véhicule A"
            vehicleType={formValues.catv_group_code || 1}
            selectedImpact={formValues.macro_choc === "Frontal" ? "front" : formValues.macro_choc === "Arriere" ? "rear" : formValues.macro_choc === "Lateral" ? "left" : "roof"}
            onImpactSelect={handleImpactA}
          />
        </div>

        {/* Colonne Véhicule B (Si 2 ou 3+ véhicules impliqués) */}
        {showTwoModelers && (
          <div className="flex flex-col">
            <div className="mb-1 flex items-center justify-between px-1">
              <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                <span>🚙</span>
                <span>Type de Véhicule B :</span>
              </label>
              <select
                value={formValues.catv_b_group_code || 1}
                onChange={(e) => onChange('catv_b_group_code', Number(e.target.value))}
                className="card-vehicules text-xs py-1 px-2 font-bold focus:border-blue-500"
              >
                {CATV_GROUP_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.text}
                  </option>
                ))}
              </select>
            </div>
            <Vehicle3DViewer
              label="Véhicule B"
              vehicleType={formValues.catv_b_group_code || 1}
              selectedImpact={formValues.macro_choc_b === "Frontal" ? "front" : "rear"}
              onImpactSelect={handleImpactB}
            />
          </div>
        )}
      </div>

      {/* CARACTÉRISTIQUES VÉHICULE A (ET DUPLICATION VÉHICULE B SI CONCERNÉ) */}
      <div className="flex flex-col space-y-2 pt-1 border-t border-blue-500/20">
        <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
          Caractéristiques Véhicule A :
        </span>
        <div className="grid grid-cols-3 gap-2">
          {/* Motorisation A */}
          <div className="flex flex-col space-y-1">
            <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <span>⚡ Motorisation</span>
            </label>
            <select
              value={formValues.motor !== undefined ? formValues.motor : 0}
              onChange={(e) => onChange('motor', Number(e.target.value))}
              className="card-vehicules px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-blue-500 font-medium"
            >
              {MOTOR_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>

          {/* Manœuvre A */}
          <div className="flex flex-col space-y-1">
            <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <span>↪️ Manœuvre avant choc</span>
            </label>
            <select
              value={formValues.manv !== undefined ? formValues.manv : 0}
              onChange={(e) => onChange('manv', Number(e.target.value))}
              className="card-vehicules px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-blue-500 font-medium"
            >
              {MANV_OPTIONS.slice(0, 16).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>

          {/* Obstacle Mobile A */}
          <div className="flex flex-col space-y-1">
            <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
              <span>🚧 Obstacle mobile</span>
            </label>
            <select
              value={formValues.macro_obsm_code !== undefined ? formValues.macro_obsm_code : (nbVehicules >= 2 ? 1 : 4)}
              onChange={(e) => {
                const code = Number(e.target.value);
                const opt = MACRO_OBSM_OPTIONS.find(o => o.value === code);
                onChange('macro_obsm_code', code);
                onChange('macro_obsm', opt ? opt.key : "Vehicule");
              }}
              className="card-vehicules px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-blue-500 font-medium"
            >
              {MACRO_OBSM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* DUPLICATION POUR VÉHICULE B (SI 2 OU 3+ VÉHICULES) */}
        {showTwoModelers && (
          <div className="flex flex-col space-y-2 pt-2 border-t border-blue-500/10 animate-fadeIn">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              Caractéristiques Véhicule B :
            </span>
            <div className="grid grid-cols-3 gap-2">
              {/* Motorisation B */}
              <div className="flex flex-col space-y-1">
                <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                  <span>⚡ Motorisation (B)</span>
                </label>
                <select
                  value={formValues.motor_b !== undefined ? formValues.motor_b : 0}
                  onChange={(e) => onChange('motor_b', Number(e.target.value))}
                  className="card-vehicules px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-blue-500 font-medium"
                >
                  {MOTOR_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.text}
                    </option>
                  ))}
                </select>
              </div>

              {/* Manœuvre B */}
              <div className="flex flex-col space-y-1">
                <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                  <span>↪️ Manœuvre avant choc (B)</span>
                </label>
                <select
                  value={formValues.manv_b !== undefined ? formValues.manv_b : 0}
                  onChange={(e) => onChange('manv_b', Number(e.target.value))}
                  className="card-vehicules px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-blue-500 font-medium"
                >
                  {MANV_OPTIONS.slice(0, 16).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.text}
                    </option>
                  ))}
                </select>
              </div>

              {/* Obstacle Mobile B */}
              <div className="flex flex-col space-y-1">
                <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                  <span>🚧 Obstacle mobile (B)</span>
                </label>
                <select
                  value={formValues.macro_obsm_code_b !== undefined ? formValues.macro_obsm_code_b : 1}
                  onChange={(e) => onChange('macro_obsm_code_b', Number(e.target.value))}
                  className="card-vehicules px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-blue-500 font-medium"
                >
                  {MACRO_OBSM_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.text}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
