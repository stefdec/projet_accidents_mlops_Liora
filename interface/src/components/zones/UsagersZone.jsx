import React from 'react';
import { User, Users, Shield } from 'lucide-react';
import {
  CATU_OPTIONS,
  SEXE_OPTIONS,
  PLACE_OPTIONS,
  SECU_OPTIONS,
  LOCP_OPTIONS,
  ACTP_OPTIONS,
  ETATP_OPTIONS,
} from '../../config/constants';

function SingleVictimSubForm({
  title,
  catu,
  sexe,
  age,
  place,
  secu1,
  secu2,
  secu3,
  locp,
  actp,
  etatp,
  onCatuChange,
  onSexeChange,
  onAgeChange,
  onPlaceChange,
  onSecu1Change,
  onSecu2Change,
  onSecu3Change,
  onLocpChange,
  onActpChange,
  onEtatpChange,
}) {
  const isPieton = catu === 3;

  return (
    <div className="flex flex-col space-y-2.5 p-2.5 rounded-lg bg-slate-100/80 dark:bg-slate-900/60 border border-emerald-500/30">
      {/* En-tête de la fiche victime */}
      <div className="flex items-center justify-between border-b border-emerald-500/20 pb-1">
        <span className="text-xs font-black uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
          {title}
        </span>
        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
          {catu === 1 ? "Conducteur" : catu === 2 ? "Passager" : "Piéton"}
        </span>
      </div>

      {/* Rôle de la victime */}
      <div className="flex flex-col space-y-1">
        <label className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
          <span>Rôle</span>
          <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">Boutons directs</span>
        </label>
        <div className="grid grid-cols-3 gap-1">
          {CATU_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onCatuChange(opt.value);
                if (opt.value === 3) onPlaceChange(10);
                else if (opt.value === 1) onPlaceChange(1);
              }}
              className={`py-1.5 px-1 rounded-md border text-[11px] font-black transition flex items-center justify-center ${
                catu === opt.value
                  ? 'bg-emerald-600 text-white border-emerald-500 shadow-sm ring-1 ring-emerald-400'
                  : 'card-usagers text-slate-800 dark:text-slate-200 hover:border-emerald-400'
              }`}
            >
              <span>{opt.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sexe & Âge */}
      <div className="grid grid-cols-2 gap-2">
        {/* Sexe */}
        <div className="flex flex-col space-y-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
            Sexe
          </label>
          <div className="grid grid-cols-2 gap-1">
            {SEXE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => onSexeChange(opt.value)}
                className={`py-1 px-1 rounded-md border text-center text-[11px] font-black transition ${
                  sexe === opt.value
                    ? 'bg-emerald-600 text-white border-emerald-500 shadow-sm'
                    : 'card-usagers text-slate-800 dark:text-slate-200 hover:border-emerald-400'
                }`}
              >
                {opt.text}
              </button>
            ))}
          </div>
        </div>

        {/* Âge avec incrémentation rapide */}
        <div className="flex flex-col space-y-1">
          <label className="text-[10px] font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
            <span>Âge</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">{age} ans</span>
          </label>
          <div className="flex items-center space-x-1">
            <button
              type="button"
              onClick={() => onAgeChange(Math.max(1, (age || 30) - 5))}
              className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded font-black text-xs hover:bg-slate-300 dark:hover:bg-slate-700"
            >
              -5
            </button>
            <input
              type="number"
              min="0"
              max="120"
              value={age}
              onChange={(e) => onAgeChange(Number(e.target.value))}
              className="card-usagers w-full py-0.5 text-center font-black text-xs text-slate-900 dark:text-slate-100 focus:border-emerald-500"
            />
            <button
              type="button"
              onClick={() => onAgeChange(Math.min(120, (age || 30) + 5))}
              className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded font-black text-xs hover:bg-slate-300 dark:hover:bg-slate-700"
            >
              +5
            </button>
          </div>
        </div>
      </div>

      {/* Place dans le véhicule */}
      <div className="flex flex-col space-y-1">
        <label className="text-[10px] font-semibold text-slate-700 dark:text-slate-300">
          Place dans le véhicule
        </label>
        <select
          value={place}
          disabled={isPieton}
          onChange={(e) => onPlaceChange(Number(e.target.value))}
          className="card-usagers px-2 py-1 text-xs text-slate-900 dark:text-slate-100 focus:border-emerald-500 disabled:opacity-50 font-medium"
        >
          {PLACE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.text}
            </option>
          ))}
        </select>
      </div>

      {/* Équipement de sécurité (3 choix BAAC possibles max: secu1, secu2, secu3) */}
      <div className="flex flex-col space-y-1">
        <label className="text-[10px] font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
          <div className="flex items-center space-x-1 text-emerald-600 dark:text-emerald-400">
            <Shield className="w-3.5 h-3.5 text-emerald-500" />
            <span className="uppercase tracking-wider">Équipements de sécurité (3 max)</span>
          </div>
          <span className="text-[9px] text-slate-500 font-normal">Champs BAAC secu1/2/3</span>
        </label>
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
          {/* Équipement 1 */}
          <div className="flex flex-col space-y-0.5">
            <span className="text-[9px] font-bold text-slate-500 dark:text-slate-400">Équipement 1</span>
            <select
              value={secu1 !== undefined ? secu1 : 1}
              onChange={(e) => onSecu1Change(Number(e.target.value))}
              className="card-usagers w-full px-1.5 py-1 text-[11px] text-slate-900 dark:text-slate-100 focus:border-emerald-500 font-semibold"
            >
              {SECU_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>

          {/* Équipement 2 */}
          <div className="flex flex-col space-y-0.5">
            <span className="text-[9px] font-bold text-slate-500 dark:text-slate-400">Équipement 2</span>
            <select
              value={secu2 !== undefined ? secu2 : 0}
              onChange={(e) => onSecu2Change && onSecu2Change(Number(e.target.value))}
              className="card-usagers w-full px-1.5 py-1 text-[11px] text-slate-900 dark:text-slate-100 focus:border-emerald-500 font-semibold"
            >
              {SECU_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>

          {/* Équipement 3 */}
          <div className="flex flex-col space-y-0.5">
            <span className="text-[9px] font-bold text-slate-500 dark:text-slate-400">Équipement 3</span>
            <select
              value={secu3 !== undefined ? secu3 : 0}
              onChange={(e) => onSecu3Change && onSecu3Change(Number(e.target.value))}
              className="card-usagers w-full px-1.5 py-1 text-[11px] text-slate-900 dark:text-slate-100 focus:border-emerald-500 font-semibold"
            >
              {SECU_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.text}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Détails spécifiques si Piéton */}
      {isPieton && (
        <div className="p-2 bg-emerald-50/80 dark:bg-emerald-950/40 border border-emerald-400/50 rounded-lg grid grid-cols-3 gap-1 mt-1">
          <div>
            <label className="text-[9px] font-bold text-emerald-800 dark:text-emerald-300">Localisation</label>
            <select
              value={locp || 0}
              onChange={(e) => onLocpChange && onLocpChange(Number(e.target.value))}
              className="card-usagers w-full text-[9px] p-1 mt-0.5 font-medium"
            >
              {LOCP_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.text}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[9px] font-bold text-emerald-800 dark:text-emerald-300">Action</label>
            <select
              value={actp || 0}
              onChange={(e) => onActpChange && onActpChange(Number(e.target.value))}
              className="card-usagers w-full text-[9px] p-1 mt-0.5 font-medium"
            >
              {ACTP_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.text}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[9px] font-bold text-emerald-800 dark:text-emerald-300">Accompagnement</label>
            <select
              value={etatp || 0}
              onChange={(e) => onEtatpChange && onEtatpChange(Number(e.target.value))}
              className="card-usagers w-full text-[9px] p-1 mt-0.5 font-medium"
            >
              {ETATP_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.text}</option>)}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

export default function UsagersZone({ formValues, onChange }) {
  const isMultipleVictims = formValues.plusieurs_victimes || false;
  const rawCount = formValues.nb_victimes_accident || 1;

  const handleMultipleVictimsToggle = (checked) => {
    onChange('plusieurs_victimes', checked);
    if (checked) {
      onChange('nb_victimes_accident', Math.max(2, formValues.nb_victimes_accident || 2));
    } else {
      onChange('nb_victimes_accident', 1);
    }
  };

  const handleIncrementVictims = () => {
    const current = formValues.nb_victimes_accident || 1;
    const nextVal = current + 1; // Pas de limite sur le compteur total de blessés
    onChange('nb_victimes_accident', nextVal);
    if (nextVal > 1) {
      onChange('plusieurs_victimes', true);
    }
  };

  const handleDecrementVictims = () => {
    const current = formValues.nb_victimes_accident || 1;
    const nextVal = Math.max(1, current - 1);
    onChange('nb_victimes_accident', nextVal);
    if (nextVal <= 1) {
      onChange('plusieurs_victimes', false);
    }
  };

  // Configuration dynamique des clés de formulaire pour les victimes 1 à 6
  const getVictimProps = (index) => {
    const suffix = index === 1 ? '' : String(index);
    const secu1Key = index === 1 ? 'secu1' : `secu1_${index}`;
    const secu2Key = index === 1 ? 'secu2' : `secu2_${index}`;
    const secu3Key = index === 1 ? 'secu3' : `secu3_${index}`;

    return {
      title: `Victime ${index}`,
      catu: formValues[`catu${suffix}`] || 1, // Conducteur par défaut
      sexe: formValues[`sexe${suffix}`] || (index % 2 === 1 ? 1 : 2),
      age: formValues[`age${suffix}`] || (30 + index * 2),
      place: formValues[`place${suffix}`] || (index === 1 ? 1 : Math.min(9, index)),
      secu1: formValues[secu1Key] !== undefined ? formValues[secu1Key] : 1,
      secu2: formValues[secu2Key] !== undefined ? formValues[secu2Key] : 0,
      secu3: formValues[secu3Key] !== undefined ? formValues[secu3Key] : 0,
      locp: formValues[`locp${suffix}`] || 0,
      actp: formValues[`actp${suffix}`] || 0,
      etatp: formValues[`etatp${suffix}`] || 0,
      onCatuChange: (v) => onChange(`catu${suffix}`, v),
      onSexeChange: (v) => onChange(`sexe${suffix}`, v),
      onAgeChange: (v) => onChange(`age${suffix}`, v),
      onPlaceChange: (v) => onChange(`place${suffix}`, v),
      onSecu1Change: (v) => onChange(secu1Key, v),
      onSecu2Change: (v) => onChange(secu2Key, v),
      onSecu3Change: (v) => onChange(secu3Key, v),
      onLocpChange: (v) => onChange(`locp${suffix}`, v),
      onActpChange: (v) => onChange(`actp${suffix}`, v),
      onEtatpChange: (v) => onChange(`etatp${suffix}`, v),
    };
  };

  // Liste des victimes à afficher (1 à 6 max)
  const displayVictimsCount = isMultipleVictims ? Math.min(6, Math.max(2, rawCount)) : 1;
  const victimIndices = Array.from({ length: displayVictimsCount }, (_, i) => i + 1);

  return (
    <div className="zone-usagers p-3 rounded-xl border border-emerald-500/40 shadow-sm flex flex-col space-y-3 h-full justify-between">
      <div>
        {/* Entête Catégorie 4 */}
        <div className="flex items-center justify-between border-b border-emerald-500/20 pb-1.5 mb-2.5">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-md bg-emerald-600/20 text-emerald-500 flex items-center justify-center border border-emerald-500/40">
              <User className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-black uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
              4. Usagers & Victimes
            </h2>
          </div>

          {/* CASE À COCHER : PLUSIEURS VICTIMES */}
          <label className="flex items-center space-x-1.5 cursor-pointer bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-400/40 px-2 py-0.5 rounded-lg select-none hover:bg-emerald-200 dark:hover:bg-emerald-900/60 transition">
            <input
              type="checkbox"
              checked={isMultipleVictims}
              onChange={(e) => handleMultipleVictimsToggle(e.target.checked)}
              className="w-3.5 h-3.5 accent-emerald-600 rounded cursor-pointer"
            />
            <span className="text-[11px] font-black text-emerald-800 dark:text-emerald-300">
              Plusieurs victimes
            </span>
          </label>
        </div>

        {/* Indication visuelle si plusieurs victimes & compteur (Formulaires limités à 6 max) */}
        {isMultipleVictims && (
          <div className="mb-2.5 p-2 bg-amber-500/10 border border-amber-500/40 rounded-lg flex flex-wrap items-center justify-between text-xs gap-1.5">
            <div className="flex items-center space-x-1.5 text-amber-700 dark:text-amber-300 font-bold">
              <Users className="w-4 h-4 text-amber-500 animate-pulse" />
              <span>Nombre estimé de blessés :</span>
            </div>
            <div className="flex items-center space-x-1">
              <button
                type="button"
                onClick={handleDecrementVictims}
                className="w-6 h-6 rounded bg-amber-200 dark:bg-amber-900/60 font-black text-amber-900 dark:text-amber-200 flex items-center justify-center hover:bg-amber-300"
              >
                -
              </button>
              <span className="font-mono font-black text-sm px-2 text-slate-900 dark:text-slate-100">
                {formValues.nb_victimes_accident || 2}
              </span>
              <button
                type="button"
                onClick={handleIncrementVictims}
                className="w-6 h-6 rounded bg-amber-200 dark:bg-amber-900/60 font-black text-amber-900 dark:text-amber-200 flex items-center justify-center hover:bg-amber-300"
              >
                +
              </button>
            </div>
            {(formValues.nb_victimes_accident || 2) > 6 && (
              <span className="w-full text-right text-[10px] font-semibold text-amber-600 dark:text-amber-400">
                (Saisie détaillée limitée aux 6 premières victimes)
              </span>
            )}
          </div>
        )}

        {/* FORMULAIRES DE VICTIMES DYNAMIQUES (1 à 6 selon le nombre estimé de blessés) */}
        <div className={`grid gap-2.5 ${displayVictimsCount > 1 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
          {victimIndices.map((index) => {
            const props = getVictimProps(index);
            return <SingleVictimSubForm key={index} {...props} />;
          })}
        </div>
      </div>
    </div>
  );
}
