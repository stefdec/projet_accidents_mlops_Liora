import React from 'react';
import { AlertCircle, CheckCircle2, TrendingUp, Cpu, Activity } from 'lucide-react';

export default function PredictionResult({
  result,
  isLoading,
  onSendPrediction,
}) {
  const isGrave = result ? Number(result.prediction) === 1 : false;
  const probability = result ? Number(result.probability || 0) : 0;
  const probPercent = Math.round(probability * 100);

  return (
    <div className="flex flex-col space-y-3">
      {/* Bouton d'envoi de la prédiction */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onSendPrediction}
          disabled={isLoading}
          className={`w-full py-3 px-6 rounded-xl font-black text-sm uppercase tracking-wider text-white shadow-lg transition-all duration-200 transform active:scale-[0.99] flex items-center justify-center space-x-2 ${
            isLoading
              ? 'bg-slate-700 cursor-not-allowed'
              : 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 hover:shadow-red-600/30 hover:scale-[1.01] border border-red-400/40'
          }`}
        >
          {isLoading ? (
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-white animate-ping" />
              <span className="text-base tracking-widest animate-pulse">...</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4" />
              <span>Envoyer</span>
            </div>
          )}
        </button>
      </div>

      {/* Résultat de la prédiction (Intervient après l'envoi) */}
      {result && (
        <div className="flex flex-col space-y-3 animate-fadeIn">
          {/* ENCADRÉ ROUGE OU VERT AVEC TEXTE BLANC GROS ET ULTRA VISIBLE */}
          <div
            className={`p-4 rounded-xl text-white shadow-2xl border-2 flex items-center justify-between transition-all duration-300 ${
              isGrave
                ? 'bg-red-600 border-red-400 ring-4 ring-red-600/30'
                : 'bg-emerald-700 border-emerald-400 ring-4 ring-emerald-600/30'
            }`}
          >
            <div className="flex items-center space-x-3">
              {isGrave ? (
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center animate-pulse">
                  <AlertCircle className="w-8 h-8 text-white" />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <CheckCircle2 className="w-8 h-8 text-white" />
                </div>
              )}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-widest text-white/90">
                  Diagnostic de Gravité Modèle MLOps
                </div>
                <div className="text-2xl font-black tracking-tight uppercase">
                  {isGrave ? 'GRAVE' : 'NON GRAVE'}
                </div>
              </div>
            </div>

            {/* Pourcentage de gravité en très gros */}
            <div className="text-right flex flex-col items-end">
              <div className="text-4xl font-mono font-black tracking-tight leading-none">
                {probPercent}%
              </div>
              <div className="text-[10px] uppercase font-bold text-white/80 mt-1">
                Indice de risque
              </div>
              {result.status && (
                <div className="mt-1.5 inline-flex items-center space-x-1 bg-black/30 text-white/90 px-2 py-0.5 rounded text-[10px] font-mono">
                  <Cpu className="w-3 h-3 text-amber-300" />
                  <span>
                    {result.status === 'remote_api'
                      ? `BentoML (${result.model_version || 'predict-api'})`
                      : "Moteur d'Urgence Fallback"}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
