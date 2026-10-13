import React from 'react';
import { VMA_OPTIONS } from '../config/constants';

/**
 * Composant de panneau routier officiel français pour la sélection VMA
 */
export default function SpeedSign({ value, onChange }) {
  return (
    <div className="flex flex-col space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-amber-500 dark:text-amber-400">
          Vitesse Maximale Autorisée (VMA)
        </label>
        <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
          {VMA_OPTIONS.find(o => o.value === value)?.text || 'Sélectionner'}
        </span>
      </div>

      <div className="grid grid-cols-9 gap-1.5 p-1.5 bg-slate-100/80 dark:bg-slate-900/80 rounded-lg border border-amber-500/30">
        {VMA_OPTIONS.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              title={opt.text}
              className={`group relative flex flex-col items-center justify-center p-1 rounded-md transition-all transform active:scale-95 ${
                isSelected 
                  ? 'ring-2 ring-amber-400 bg-amber-400/10 scale-105 shadow-md' 
                  : 'hover:bg-slate-200/60 dark:hover:bg-slate-800/60 opacity-85 hover:opacity-100'
              }`}
            >
              {/* Panneau routier circulaire français */}
              <div
                className={`w-9 h-9 rounded-full bg-white flex items-center justify-center border-[3px] border-red-600 shadow-sm transition-transform ${
                  isSelected ? 'border-red-600 shadow-red-500/30 ring-1 ring-red-400' : 'group-hover:scale-105'
                }`}
              >
                <span className="text-black font-black text-[13px] font-mono tracking-tighter leading-none">
                  {opt.speed}
                </span>
              </div>
              <span className="text-[9px] font-bold mt-1 text-slate-600 dark:text-slate-300">
                {opt.speed}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
