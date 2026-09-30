import React, { useState, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Clock } from 'lucide-react';

interface TimeSliderProps {
  currentLeadTime: number;
  availableLeadTimes: number[];
  onChange: (time: number) => void;
}

export const TimeSlider: React.FC<TimeSliderProps> = ({
  currentLeadTime,
  availableLeadTimes,
  onChange
}) => {
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      const currIdx = availableLeadTimes.indexOf(currentLeadTime);
      const nextIdx = (currIdx + 1) % availableLeadTimes.length;
      onChange(availableLeadTimes[nextIdx]);
    }, 1500);

    return () => clearInterval(interval);
  }, [isPlaying, currentLeadTime, availableLeadTimes, onChange]);

  const handleStepBack = () => {
    const currIdx = availableLeadTimes.indexOf(currentLeadTime);
    if (currIdx > 0) onChange(availableLeadTimes[currIdx - 1]);
  };

  const handleStepForward = () => {
    const currIdx = availableLeadTimes.indexOf(currentLeadTime);
    if (currIdx < availableLeadTimes.length - 1) onChange(availableLeadTimes[currIdx + 1]);
  };

  return (
    <div
      className="glass-panel"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '20px',
        padding: '12px 24px',
        width: '100%',
        zIndex: 1000
      }}
    >
      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={handleStepBack}
          style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
        >
          <SkipBack size={18} />
        </button>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          style={{
            background: 'rgba(6, 182, 212, 0.2)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            color: '#38BDF8',
            borderRadius: '50%',
            width: '36px',
            height: '36px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer'
          }}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} style={{ marginLeft: '2px' }} />}
        </button>

        <button
          onClick={handleStepForward}
          style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
        >
          <SkipForward size={18} />
        </button>
      </div>

      {/* Label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '160px' }}>
        <Clock size={16} color="#06B6D4" />
        <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#F8FAFC' }}>
          Lead-Time: T+{currentLeadTime}h
        </span>
      </div>

      {/* Range Slider */}
      <input
        type="range"
        min={availableLeadTimes[0]}
        max={availableLeadTimes[availableLeadTimes.length - 1]}
        step={24}
        value={currentLeadTime}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{
          flex: 1,
          accentColor: '#06B6D4',
          cursor: 'pointer'
        }}
      />

      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
        Forecast Horizon: 10-Day Medium Range
      </span>
    </div>
  );
};
