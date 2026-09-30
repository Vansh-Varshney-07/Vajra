import React from 'react';

interface EnsembleConeProps {
  visible: boolean;
  waypoints?: Array<{ lat: number; lon: number }>;
}

export const EnsembleCone: React.FC<EnsembleConeProps> = ({ visible, waypoints = [] }) => {
  if (!visible || waypoints.length < 2) return null;

  return (
    <div className="absolute bottom-4 left-4 z-20 pointer-events-none bg-slate-900/80 border border-slate-700/80 rounded-lg p-2.5 backdrop-blur-md shadow-xl text-xs text-white">
      <div className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider mb-1 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-amber-400"></span>
        <span>Ensemble Uncertainty Cone</span>
      </div>
      <div className="flex flex-col gap-1 text-[10px] text-slate-300">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-1.5 rounded-sm bg-amber-500/70"></span>
          <span>50% Consensus Cone (P50)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-1.5 rounded-sm bg-orange-600/40 border border-orange-500/60 border-dashed"></span>
          <span>90% Uncertainty Envelope (P90)</span>
        </div>
      </div>
    </div>
  );
};
