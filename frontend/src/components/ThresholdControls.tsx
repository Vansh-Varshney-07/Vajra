import React, { useState } from 'react';

interface Thresholds {
  cycloneWindKmhSevere: number;
  rainMmExtreme: number;
  heatwaveEmergencyC: number;
  geodesicBufferKm: number;
}

const DEFAULTS: Thresholds = {
  cycloneWindKmhSevere: 118,
  rainMmExtreme: 204.4,
  heatwaveEmergencyC: 47,
  geodesicBufferKm: 5,
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  background: 'var(--raised)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  padding: '6px 8px',
  color: 'var(--text)',
  font: '500 13px var(--font-mono)',
  outline: 'none',
};

export const ThresholdControls: React.FC = () => {
  const [t, setT] = useState<Thresholds>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  return (
    <div className="panel" style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="eyebrow">Risk Engine Thresholds</div>
        <button
          onClick={() => { setT(DEFAULTS); setSaved(false); }}
          style={{ font: '500 11px var(--font-mono)', color: 'var(--muted)', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          ↺ Reset
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        {[
          { label: 'Cyclone severe wind (km/h)', key: 'cycloneWindKmhSevere' as const },
          { label: 'Extreme rainfall (mm/12h)',  key: 'rainMmExtreme'        as const },
          { label: 'Heatwave emergency (°C)',    key: 'heatwaveEmergencyC'   as const },
          { label: 'Geodesic buffer (km)',        key: 'geodesicBufferKm'     as const, disabled: true },
        ].map(({ label, key, disabled }) => (
          <div key={key}>
            <label style={{ font: '11px var(--font-sans)', color: 'var(--muted)', display: 'block', marginBottom: 4 }}>
              {label}
            </label>
            <input
              type="number"
              value={t[key]}
              disabled={disabled}
              onChange={e => setT(prev => ({ ...prev, [key]: +e.target.value }))}
              style={{ ...inputStyle, opacity: disabled ? 0.5 : 1, cursor: disabled ? 'not-allowed' : 'text' }}
            />
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ font: '10px var(--font-mono)', color: 'var(--muted)' }}>
          configs/impact_thresholds.yaml
        </span>
        <button
          onClick={handleSave}
          className="cta"
          style={{ width: 'auto', padding: '7px 14px', fontSize: 12 }}
        >
          {saved ? '✓ Applied' : 'Update thresholds'}
        </button>
      </div>
    </div>
  );
};
