interface RainfallGridProps {
  visible: boolean;
}

export const RainfallGrid: React.FC<RainfallGridProps> = ({ visible }) => {
  if (!visible) return null;

  return (
    <div className="absolute top-4 right-4 z-20 pointer-events-none bg-slate-900/80 border border-slate-700/80 rounded-lg p-2.5 backdrop-blur-md shadow-xl text-xs text-white">
      <div className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center justify-between">
        <span>5 km Precipitation Legend</span>
        <span className="text-cyan-400 font-mono">mm/12hr</span>
      </div>
      <div className="flex items-center space-x-1">
        <div className="w-5 h-3 rounded-sm bg-blue-900/80" title="10-35 mm"></div>
        <div className="w-5 h-3 rounded-sm bg-cyan-700/80" title="35-65 mm"></div>
        <div className="w-5 h-3 rounded-sm bg-emerald-600/80" title="65-115 mm (Heavy)"></div>
        <div className="w-5 h-3 rounded-sm bg-yellow-500/80" title="115-180 mm (Very Heavy)"></div>
        <div className="w-5 h-3 rounded-sm bg-red-600/90" title=">180 mm (Extreme Peak)"></div>
      </div>
      <div className="flex justify-between text-[9px] text-slate-400 mt-1 font-mono">
        <span>10</span>
        <span>65</span>
        <span>115</span>
        <span>180+</span>
      </div>
    </div>
  );
};
