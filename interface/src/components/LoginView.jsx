import React, { useState } from 'react';
import { ShieldAlert, Lock, User, Radio, ArrowRight } from 'lucide-react';

export default function LoginView({ onLogin, error }) {
  const [username, setUsername] = useState('alice');
  const [password, setPassword] = useState('wonderland');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) return;
    setIsLoading(true);
    await onLogin(username, password);
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900/95 border border-slate-700/80 rounded-2xl shadow-2xl p-6 backdrop-blur-xl flex flex-col space-y-5">
        {/* Logo & Titre */}
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-red-600/90 text-white flex items-center justify-center shadow-xl shadow-red-600/30 border border-red-400/40">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div>
            <div className="inline-flex items-center space-x-1.5 bg-red-600/20 text-red-400 border border-red-500/30 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider">
              <Radio className="w-3 h-3 text-red-500 animate-pulse" />
              <span>CENTRE D'APPELS D'URGENCE 112 / 18</span>
            </div>
            <h1 className="text-xl font-black text-slate-100 mt-1">
              Système Prédictif d'Accidents MLOps
            </h1>
            <p className="text-xs text-slate-400">
              Authentification sécurisée des opérateurs de régulation
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-red-950/60 border border-red-500/50 text-red-200 text-xs p-2.5 rounded-lg text-center font-medium">
            {error}
          </div>
        )}

        {/* Formulaire de Connexion */}
        <form onSubmit={handleSubmit} className="flex flex-col space-y-3.5">
          <div className="flex flex-col space-y-1">
            <label className="text-xs font-bold text-slate-300 flex items-center space-x-1.5">
              <User className="w-3.5 h-3.5 text-slate-400" />
              <span>Nom d'utilisateur</span>
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Ex: alice ou matricule"
              className="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-red-500"
            />
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-xs font-bold text-slate-300 flex items-center space-x-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              <span>Mot de passe</span>
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-red-500"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-red-600/20 transition-all flex items-center justify-center space-x-2 border border-red-400/40 active:scale-[0.98]"
          >
            <span>{isLoading ? 'Connexion en cours...' : 'Ouvrir la session d\'urgence'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Note démo */}
        <div className="pt-2 border-t border-slate-800 text-center">
          <p className="text-[11px] text-slate-400">
            Identifiants configurés dans <span className="font-mono text-amber-400">.env</span> : <code className="text-slate-300">alice / wonderland</code>
          </p>
        </div>
      </div>
    </div>
  );
}
