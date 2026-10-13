import React, { useState } from 'react';
import { Truck, HeartPulse, Siren, CheckCircle2, RotateCcw, Send } from 'lucide-react';

export default function DispatchSecours({
  hasPredicted = false,
  onResetForm,
}) {
  // DÉSACTIVÉES PAR DÉFAUT pour que l'utilisateur décide lui-même
  const [selectedUnits, setSelectedUnits] = useState({
    pompiers: false,
    samu: false,
    police: false,
  });
  const [isRequestSent, setIsRequestSent] = useState(false);

  const toggleUnit = (unitKey) => {
    setSelectedUnits(prev => ({
      ...prev,
      [unitKey]: !prev[unitKey]
    }));
    setIsRequestSent(false); // Réactive si on change les choix
  };

  const handleValidate = () => {
    const hasAtLeastOne = Object.values(selectedUnits).some(Boolean);
    if (!hasAtLeastOne) {
      alert("Veuillez sélectionner au moins un service de secours (Pompiers, SAMU ou Police) avant de valider l'envoi.");
      return;
    }
    setIsRequestSent(true);
  };

  const unitsList = [
    { key: 'pompiers', label: 'Pompiers (18)', icon: Truck, activeBg: 'bg-red-600 text-white border-red-500' },
    { key: 'samu', label: 'SAMU (15)', icon: HeartPulse, activeBg: 'bg-rose-600 text-white border-rose-500' },
    { key: 'police', label: 'Police / Gendarmerie (17)', icon: Siren, activeBg: 'bg-blue-600 text-white border-blue-500' },
  ];

  return (
    <div className="w-full bg-slate-100/95 dark:bg-slate-900/95 border-t border-slate-300 dark:border-slate-800 p-3 shadow-2xl backdrop-blur-md flex flex-wrap items-center justify-between gap-3 sticky bottom-0 z-30">
      {/* SECTION DISPATCH SECOURS */}
      <div className="flex flex-wrap items-center space-x-3">
        <span className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-slate-200">
          Envoyer sur le lieu de l'accident :
        </span>

        {/* 3 boutons multi-sélectionnables */}
        <div className="flex items-center space-x-2">
          {unitsList.map((unit) => {
            const Icon = unit.icon;
            const isSelected = selectedUnits[unit.key];
            return (
              <button
                key={unit.key}
                type="button"
                onClick={() => toggleUnit(unit.key)}
                className={`px-3 py-1.5 rounded-lg border text-xs font-bold transition-all flex items-center space-x-1.5 ${
                  isSelected
                    ? `${unit.activeBg} shadow-md scale-105 ring-2 ring-slate-400 dark:ring-white/20`
                    : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:border-slate-400 hover:text-slate-950 dark:hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{unit.label}</span>
              </button>
            );
          })}
        </div>

        {/* Bouton Valider -> Passe à 'Demande envoyée' */}
        <button
          type="button"
          onClick={handleValidate}
          disabled={isRequestSent}
          className={`px-4 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider transition-all flex items-center space-x-1.5 shadow-md ${
            isRequestSent
              ? 'bg-emerald-600 text-white cursor-default shadow-emerald-600/30 ring-2 ring-emerald-400'
              : 'bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 hover:shadow-amber-500/30 active:scale-95'
          }`}
        >
          {isRequestSent ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-white animate-bounce" />
              <span>Demande envoyée</span>
            </>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>Valider l'envoi</span>
            </>
          )}
        </button>
      </div>

      {/* EN BAS À DROITE : Bouton 'Nouveau sinistre' plus petit */}
      <div className="ml-auto">
        <button
          type="button"
          onClick={() => {
            setIsRequestSent(false);
            setSelectedUnits({ pompiers: false, samu: false, police: false });
            onResetForm();
          }}
          title="Réinitialiser pour un nouvel appel d'urgence"
          className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 text-xs font-bold transition flex items-center space-x-1.5 shadow-sm active:scale-95"
        >
          <RotateCcw className="w-3.5 h-3.5 text-amber-500" />
          <span>Nouveau sinistre</span>
        </button>
      </div>
    </div>
  );
}
