import React, { useState, useEffect } from 'react';
import { ShieldAlert, Sun, Moon, LogOut, Clock, Radio } from 'lucide-react';

export default function Header({ user, onLogout, isDark, toggleTheme }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formattedDate = currentTime.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  });

  const formattedTime = currentTime.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  return (
    <header className="w-full bg-white/95 dark:bg-slate-950/95 border-b border-slate-300 dark:border-slate-800 shadow-md backdrop-blur-md px-4 py-2 flex items-center justify-between text-slate-900 dark:text-slate-100 z-30 sticky top-0 transition-colors duration-200">
      {/* GAUCHE : Service d'Urgence 112 / 18 */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-red-600 text-white font-black shadow-lg shadow-red-600/30 border border-red-400/40">
          <ShieldAlert className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="bg-red-600 text-white text-xs font-black px-1.5 py-0.5 rounded tracking-wider uppercase shadow-sm">
              URGENCES ACCIDENT
            </span>
            <span className="flex items-center text-xs text-emerald-600 dark:text-emerald-400 font-bold">
              <Radio className="w-3 h-3 mr-1 animate-pulse text-emerald-500" />
              Ligne active
            </span>
          </div>
          <h1 className="text-sm font-black tracking-tight text-slate-900 dark:text-slate-100">
            Poste de Régulation & Triage Routier MLOps
          </h1>
        </div>
      </div>

      {/* CENTRE : Date et Heure en temps réel en français */}
      <div className="flex items-center space-x-2 bg-slate-100 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 px-4 py-1.5 rounded-full shadow-inner">
        <Clock className="w-4 h-4 text-amber-500 animate-spin-slow" />
        <span className="text-xs font-bold capitalize text-slate-700 dark:text-slate-300">
          {formattedDate}
        </span>
        <span className="text-slate-400 dark:text-slate-500">•</span>
        <span className="text-sm font-mono font-black text-amber-600 dark:text-amber-400 tracking-wider">
          {formattedTime}
        </span>
      </div>

      {/* DROITE : Bienvenue [nom user], Thème & Déconnexion */}
      <div className="flex items-center space-x-3">
        <div className="text-right">
          <div className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold">Opérateur de garde</div>
          <div className="text-xs font-black text-slate-900 dark:text-slate-100 flex items-center justify-end space-x-1">
            <span>Bienvenue</span>
            <span className="text-red-700 dark:text-red-400 uppercase tracking-wide bg-red-50 dark:bg-slate-800 px-2 py-0.5 rounded border border-red-300 dark:border-red-500/30 font-black">
              {user || 'Opérateur'}
            </span>
          </div>
        </div>

        {/* Bouton Thème Clair / Sombre */}
        <button
          onClick={toggleTheme}
          title={isDark ? "Passer en thème clair" : "Passer en thème sombre"}
          className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white transition shadow-sm"
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-blue-600" />}
        </button>

        {/* Déconnexion */}
        <button
          onClick={onLogout}
          title="Fermer la session"
          className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-red-50 dark:bg-red-950/60 hover:bg-red-100 dark:hover:bg-red-900/80 text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-white border border-red-200 dark:border-red-800/50 text-xs font-bold transition shadow-sm"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Quitter</span>
        </button>
      </div>
    </header>
  );
}
