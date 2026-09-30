import React, { useState, useRef, useEffect } from 'react';

interface TimeSliderProps {
  currentLeadTime: number;
  availableLeadTimes: number[];
  onChange: (t: number) => void;
}

export const TimeSlider: React.FC<TimeSliderProps> = ({
  currentLeadTime,
  availableLeadTimes,
  onChange,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sortedTimes = [...availableLeadTimes].sort((a, b) => a - b);
  const min = sortedTimes[0] ?? 0;
  const max = sortedTimes[sortedTimes.length - 1] ?? 120;
  const pct = max > min ? ((currentLeadTime - min) / (max - min)) * 100 : 100;

  function stop() {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setIsPlaying(false);
  }

  function handlePlay() {
    if (isPlaying) { stop(); return; }
    // If at end, reset to start
    if (currentLeadTime >= max) onChange(min);
    setIsPlaying(true);
    timerRef.current = setInterval(() => {
      onChange(prev => {
        // need functional update — we'll use a ref trick
        return prev; // see below
      });
    }, 180);
  }

  // Better play logic using ref
  const currentRef = useRef(currentLeadTime);
  currentRef.current = currentLeadTime;

  function play() {
    if (isPlaying) { stop(); return; }
    let t = currentLeadTime >= max ? min : currentLeadTime;
    onChange(t);
    setIsPlaying(true);
    timerRef.current = setInterval(() => {
      t += 6;
      if (t > max) { stop(); return; }
      onChange(t);
    }, 200);
  }

  useEffect(() => () => stop(), []); // cleanup

  function stepBack() {
    stop();
    const prev = sortedTimes.filter(t => t < currentLeadTime).pop() ?? min;
    onChange(prev);
  }

  function stepFwd() {
    stop();
    const next = sortedTimes.find(t => t > currentLeadTime) ?? max;
    onChange(next);
  }

  return (
    <div className="timeline">
      {/* Controls */}
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="icon-btn" onClick={stepBack} aria-label="Previous step">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 5h2v14H6zM20 5v14L9 12z" />
          </svg>
        </button>
        <button className={`icon-btn ${isPlaying ? 'active' : ''}`} onClick={play} aria-label={isPlaying ? 'Pause' : 'Play'}>
          {isPlaying ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 4h4v16H6zM14 4h4v16h-4z" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 4v16l13-8z" />
            </svg>
          )}
        </button>
        <button className="icon-btn" onClick={stepFwd} aria-label="Next step">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
            <path d="M16 5h2v14h-2zM4 5v14l11-7z" />
          </svg>
        </button>
      </div>

      {/* Lead time display */}
      <div style={{ minWidth: 96 }}>
        <span className="eyebrow">Lead time</span>
        <div style={{ font: '500 20px/1.1 var(--font-mono)' }}>T+{currentLeadTime}h</div>
      </div>

      {/* Scrubber */}
      <div style={{ flex: 1, minWidth: 200 }}>
        <input
          type="range"
          min={min}
          max={max}
          step={6}
          value={currentLeadTime}
          style={{ '--p': `${pct}%` } as React.CSSProperties}
          onChange={e => { stop(); onChange(+e.target.value); }}
        />
        <div className="ticks">
          {sortedTimes.map(t => <span key={t}>T+{t}</span>)}
        </div>
      </div>

      {/* Horizon label */}
      <div style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'right' }}>
        Horizon: 10-day medium range
      </div>
    </div>
  );
};
