import React, { useState } from 'react';
import { Sliders, CheckCircle, RefreshCw } from 'lucide-react';

interface Thresholds {
  cycloneWindKmhLow: number;
  cycloneWindKmhSevere: number;
  rainMmLow: number;
  rainMmExtreme: number;
  heatwaveWatchC: number;
  heatwaveEmergencyC: number;
}

const defaultThresholds: Thresholds = {
  cycloneWindKmhLow: 63,
  cycloneWindKmhSevere: 118,
  rainMmLow: 64.5,
  rainMmExtreme: 204.4,
  heatwaveWatchC: 40,
  heatwaveEmergencyC: 47,
};

export const ThresholdControls: React.FC = () => {
  const [thresholds, setThresholds] = useState<Thresholds>(defaultThresholds);
  const [saved, setSaved] = useState(false);

  const handleReset = () => {
    setThresholds(defaultThresholds);
    setSaved(false);
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-700/80 rounded-xl p-4 shadow-xl backdrop-blur-md text-white text-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
        <div className="flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold uppercase tracking-wider text-slate-200">
            Risk Engine Thresholds (MoES Config)
          </span>
        </div>
        <button
          onClick={handleReset}
          className="text-slate-400 hover:text-slate-200 transition-colors flex items-center space-x-1"
          title="Reset to defaults"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Reset</span>
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="space-y-1">
          <label className="text-slate-400 block">Cyclone Severe Wind (km/h)</label>
          <input
            type="number"
            value={thresholds.cycloneWindKmhSevere}
            onChange={(e) => setThresholds({ ...thresholds, cycloneWindKmhSevere: Number(e.target.value) })}
            className="w-full bg-slate-800/90 border border-slate-700 rounded px-2 py-1 text-cyan-300 focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>

        <div className="space-y-1">
          <label className="text-slate-400 block">Extreme Rainfall (mm/12hr)</label>
          <input
            type="number"
            value={thresholds.rainMmExtreme}
            onChange={(e) => setThresholds({ ...thresholds, rainMmExtreme: Number(e.target.value) })}
            className="w-full bg-slate-800/90 border border-slate-700 rounded px-2 py-1 text-cyan-300 focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>

        <div className="space-y-1">
          <label className="text-slate-400 block">Heatwave Emergency (°C)</label>
          <input
            type="number"
            value={thresholds.heatwaveEmergencyC}
            onChange={(e) => setThresholds({ ...thresholds, heatwaveEmergencyC: Number(e.target.value) })}
            className="w-full bg-slate-800/90 border border-slate-700 rounded px-2 py-1 text-amber-300 focus:outline-none focus:border-amber-500 font-mono"
          />
        </div>

        <div className="space-y-1">
          <label className="text-slate-400 block">Geodesic Buffer (km)</label>
          <input
            type="number"
            defaultValue={5}
            disabled
            className="w-full bg-slate-800/50 border border-slate-800 rounded px-2 py-1 text-slate-500 cursor-not-allowed font-mono"
          />
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <span className="text-[10px] text-slate-500">
          Source: configs/impact_thresholds.yaml
        </span>
        <button
          onClick={handleSave}
          className="bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-3 py-1 rounded transition-colors flex items-center space-x-1"
        >
          {saved ? (
            <>
              <CheckCircle className="w-3 h-3 text-emerald-300" />
              <span>Applied</span>
            </>
          ) : (
            <span>Update Thresholds</span>
          )}
        </button>
      </div>
    </div>
  );
};
