import React, { useEffect } from 'react';
import { Calendar, Sun, AlertOctagon, Hash } from 'lucide-react';
import {
  LUM_OPTIONS,
  TYPE_CRASH_OPTIONS,
  getDayPeriodFromHour,
} from '../../config/constants';

export default function CaracteristiquesZone({ formValues, onChange, openingTime }) {
  // Formatage de la date en français complet
  const dateObj = openingTime || new Date();
  const currentHour = dateObj.getHours();

  const formattedOpeningDate = dateObj.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
  const formattedOpeningHour = dateObj.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit'
  });

  // Calcul automatique de la période selon les créneaux demandés :
  // apres_midi (12h - 18h), matin (06h - 12h), nuit (00h - 06h), soir (18h - 00h)
  const computedPeriodKey = getDayPeriodFromHour(currentHour);
  const periodLabelMap = {
    matin: "Matin (06h - 12h)",
    apres_midi: "Après-midi (12h - 18h)",
    soir: "Soir (18h - 00h)",
    nuit: "Nuit (00h - 06h)",
  };

  // Mise à jour automatique de day_period dans formValues si nécessaire
  useEffect(() => {
    if (formValues.day_period !== computedPeriodKey) {
      onChange('day_period', computedPeriodKey);
    }
  }, [computedPeriodKey, formValues.day_period, onChange]);

  // Calcul automatique de la luminosité naturelle de base (si non encore configurée sur l'éclairage 3, 4 ou 5)
  useEffect(() => {
    // Si ce n'est pas la nuit et que lum n'est ni 1 ni 2, ajuster selon l'heure
    if (currentHour >= 6 && currentHour < 18) {
      if (formValues.lum !== 1 && ![3, 4, 5].includes(formValues.lum)) {
        onChange('lum', 1); // Plein jour
      }
    } else if (currentHour >= 18 && currentHour < 22) {
      if (formValues.lum !== 2 && ![3, 4, 5].includes(formValues.lum)) {
        onChange('lum', 2); // Crépuscule / Aube
      }
    }
  }, [currentHour, formValues.lum, onChange]);

  // Options d'éclairage public (valeurs 3, 4, 5)
  const lightingOptions = LUM_OPTIONS.filter(opt => [3, 4, 5].includes(opt.value));

  return (
    <div className="zone-caract p-3 rounded-xl border border-red-500/40 shadow-sm flex flex-col space-y-3 h-full justify-between">
      <div>
        {/* Entête Catégorie 1 */}
        <div className="flex items-center justify-between border-b border-red-500/20 pb-1.5 mb-2.5">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-md bg-red-600/20 text-red-500 flex items-center justify-center border border-red-500/40">
              <AlertOctagon className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-black uppercase tracking-wider text-red-600 dark:text-red-400">
              1. Caractéristiques
            </h2>
          </div>
          <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-600 dark:text-slate-400 font-semibold">
            <Hash className="w-3 h-3 text-red-500" />
            <span>#{formValues.Num_Acc || '2026-001'}</span>
          </div>
        </div>

        {/* Date d'ouverture en français & Période Automatique */}
        <div className="card-caract p-2.5 text-xs flex flex-col space-y-2 border border-red-500/30 mb-3">
          <div className="flex items-start space-x-2">
            <Calendar className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
            <div>
              <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400">
                Horodatage d'ouverture du sinistre :
              </div>
              <div className="font-bold text-slate-900 dark:text-slate-100 capitalize text-sm mt-0.5">
                {formattedOpeningDate} à {formattedOpeningHour}
              </div>
            </div>
          </div>

          {/* Période calculée automatiquement par l'horaire */}
          <div className="flex items-center justify-between pt-1.5 border-t border-red-500/10 text-xs">
            <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">
              Période (Définie automatiquement) :
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-black bg-red-600 text-white shadow-sm">
              {periodLabelMap[computedPeriodKey] || computedPeriodKey}
            </span>
          </div>
        </div>

        {/* Type d'accident (CRITIQUE : boutons directs apparents) */}
        <div className="flex flex-col space-y-1.5 mb-3">
          <label className="text-[11px] font-bold uppercase tracking-wider text-red-600 dark:text-red-400 flex items-center justify-between">
            <span>Type d'accident (Critique)</span>
            <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">Accès direct</span>
          </label>
          
          <div className="grid grid-cols-1 gap-1.5">
            {TYPE_CRASH_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => onChange('type_crash', opt.key)}
                className={`p-2 rounded-lg border text-left text-xs font-bold transition-all flex items-center justify-between ${
                  formValues.type_crash === opt.key
                    ? 'bg-red-600 text-white border-red-500 shadow-md ring-1 ring-red-400'
                    : 'card-caract text-slate-800 dark:text-slate-200 hover:border-red-400'
                }`}
              >
                <span>{opt.text}</span>
                {formValues.type_crash === opt.key && (
                  <span className="w-2 h-2 rounded-full bg-white animate-ping ml-1" />
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Conditions de Luminosité & Éclairage Public */}
      <div className="flex flex-col space-y-2 pt-1">
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-bold uppercase tracking-wider text-red-600 dark:text-red-400 flex items-center space-x-1.5">
            <Sun className="w-3.5 h-3.5 text-amber-500" />
            <span>Luminosité & Éclairage</span>
          </label>
          <span className="text-[10px] font-mono font-bold text-slate-500 dark:text-slate-400">
            {formValues.lum === 1 ? '☀️ Plein jour' : formValues.lum === 2 ? '🌅 Crépuscule' : '🌙 Nuit'}
          </span>
        </div>

        {/* Boutons d'état pour la Luminosité (Plein jour / Crépuscule auto + Choix Éclairage Public) */}
        <div className="grid grid-cols-1 gap-1.5">
          {/* Statuts automatiques Plein Jour / Crépuscule */}
          <div className="grid grid-cols-2 gap-1.5">
            {LUM_OPTIONS.slice(0, 2).map((opt) => {
              const isSelected = formValues.lum === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => onChange('lum', opt.value)}
                  className={`flex items-center space-x-2 p-2 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'bg-red-600 text-white border-red-500 shadow-md ring-2 ring-red-400'
                      : 'card-caract text-slate-800 dark:text-slate-200 hover:border-red-400'
                  }`}
                >
                  <span className="text-lg leading-none">{opt.icon}</span>
                  <span className="text-[11px] font-bold">{opt.text}</span>
                </button>
              );
            })}
          </div>

          {/* Choix spécifiques d'Éclairage Public en Nuit */}
          <div className="flex flex-col space-y-1 pt-1 border-t border-red-500/10">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Conditions de nuit / Éclairage public :
            </span>
            <div className="grid grid-cols-1 gap-1">
              {lightingOptions.map((opt) => {
                const isSelected = formValues.lum === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onChange('lum', opt.value)}
                    className={`flex items-center space-x-2 py-1.5 px-2 rounded-lg border text-left text-xs font-bold transition-all ${
                      isSelected
                        ? 'bg-red-600 text-white border-red-500 shadow-md ring-1 ring-red-400'
                        : 'card-caract text-slate-800 dark:text-slate-200 hover:border-red-400'
                    }`}
                  >
                    <span className="text-sm">{opt.icon}</span>
                    <span className="text-[10px] font-semibold">{opt.text}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
