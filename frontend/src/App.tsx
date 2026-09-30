import React, { useState, useEffect, useCallback } from 'react';
import { MapView } from './components/MapView';
import { AlertPanel } from './components/AlertPanel';
import { TimeSlider } from './components/TimeSlider';
import { DownscalingModal } from './components/DownscalingModal';
import { ThresholdControls } from './components/ThresholdControls';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Fallback data (used when backend is offline) ──────────────────────────
const FALLBACK_EVENTS: Record<string, any> = {
  'BOB-CYC-2026-001': {
    event_id: 'BOB-CYC-2026-001',
    event_type: 'CYCLONE',
    name: 'Super Cyclone (Bay of Bengal)',
    probability: 0.88,
    threat_level: 'SEVERE',
    color_code: 'RED',
    current_centroid: { lat: 19.82, lon: 86.85 },
    peak_wind_kmh: 145.0,
    peak_rainfall_mm_12hr: 195.0,
    lead_time_hr: 72,
    action_recommended: 'Immediate evacuation of 5 km coastal zone. Severe storm surge alert across Digha & Balasore sectors.',
    trajectory: [
      { lead_time_hr: 24, lat: 13.5,  lon: 87.2,  intensity: 85.0  },
      { lead_time_hr: 48, lat: 16.8,  lon: 87.0,  intensity: 115.0 },
      { lead_time_hr: 72, lat: 19.82, lon: 86.85, intensity: 145.0 },
      { lead_time_hr: 96, lat: 22.1,  lon: 87.8,  intensity: 130.0 },
      { lead_time_hr: 120,lat: 24.3,  lon: 89.2,  intensity: 75.0  },
    ],
  },
  'NWI-HEAT-2026-002': {
    event_id: 'NWI-HEAT-2026-002',
    event_type: 'HEATWAVE',
    name: 'Heat Dome (NW India)',
    probability: 0.74,
    threat_level: 'WARNING',
    color_code: 'ORANGE',
    current_centroid: { lat: 27.5, lon: 73.0 },
    peak_wind_kmh: 22.0,
    peak_rainfall_mm_12hr: 0.0,
    lead_time_hr: 96,
    action_recommended: 'Severe heat stress probable T+96h. Avoid outdoor activity 11:00–17:00 IST. Heat action plan activation recommended.',
    trajectory: [
      { lead_time_hr: 24, lat: 26.5, lon: 71.0, intensity: 44.5 },
      { lead_time_hr: 48, lat: 27.0, lon: 72.5, intensity: 45.8 },
      { lead_time_hr: 72, lat: 27.5, lon: 73.0, intensity: 46.9 },
      { lead_time_hr: 96, lat: 28.0, lon: 73.5, intensity: 47.2 },
    ],
  },
  'KER-FLOOD-2026-003': {
    event_id: 'KER-FLOOD-2026-003',
    event_type: 'EXTREME_RAINFALL',
    name: 'Kerala Flash Flood Risk',
    probability: 0.67,
    threat_level: 'MODERATE',
    color_code: 'ORANGE',
    current_centroid: { lat: 10.8, lon: 76.2 },
    peak_wind_kmh: 45.0,
    peak_rainfall_mm_12hr: 320.0,
    lead_time_hr: 48,
    action_recommended: 'Extremely heavy rainfall (>200 mm/12h) forecast for Kerala Western Ghats. Flash flood and landslide risk advisory.',
    trajectory: [
      { lead_time_hr: 12, lat: 9.5,  lon: 76.8, intensity: 180.0 },
      { lead_time_hr: 24, lat: 10.2, lon: 76.5, intensity: 240.0 },
      { lead_time_hr: 48, lat: 10.8, lon: 76.2, intensity: 320.0 },
      { lead_time_hr: 72, lat: 11.5, lon: 75.8, intensity: 210.0 },
    ],
  },
};

function buildFallbackTrajectory(event: any) {
  const waypoints = event.trajectory || [];
  return {
    waypoints,
    ensemble_tracks: Array.from({ length: 20 }, (_, idx) =>
      waypoints.map((wp: any) => [
        wp.lon + (idx - 10) * 0.04 * (wp.lead_time_hr / 24),
        wp.lat + (idx - 10) * 0.03 * (wp.lead_time_hr / 24),
      ] as [number, number])
    ),
  };
}

// ─── Event type → badge colour ─────────────────────────────────────────────
function eventBadgeClass(type: string) {
  if (type === 'CYCLONE') return '';        // red (default)
  if (type === 'HEATWAVE') return 'amber';
  return 'ok';                              // green for rainfall/others
}

// ─── App ──────────────────────────────────────────────────────────────────
export const App: React.FC = () => {
  const [events, setEvents] = useState<Record<string, any>>(FALLBACK_EVENTS);
  const [selectedId, setSelectedId] = useState<string>('BOB-CYC-2026-001');
  const [trajectoryData, setTrajectoryData] = useState<any>(
    buildFallbackTrajectory(FALLBACK_EVENTS['BOB-CYC-2026-001'])
  );
  const [impactGeojson, setImpactGeojson] = useState<any>(null);
  const [currentLeadTime, setCurrentLeadTime] = useState<number>(72);
  const [isDownscaling, setIsDownscaling] = useState<boolean>(false);
  const [downscaleData, setDownscaleData] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [showThresholds, setShowThresholds] = useState<boolean>(false);
  const [apiConnected, setApiConnected] = useState<boolean>(false);

  const [layers, setLayers] = useState({
    showEnsembleTracks: true,
    showUncertaintyCone: false,
    showImpactZone: true,
    show5kmHeatmap: true,
    showWindStreamlines: true,
  });

  const event = events[selectedId];
  const availableLeadTimes = (event?.trajectory || []).map((w: any) => w.lead_time_hr);

  // ── Fetch all events from API ──────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/events`);
        if (res.ok) {
          const list: any[] = await res.json();
          const map: Record<string, any> = {};
          list.forEach(e => { map[e.event_id] = e; });
          setEvents(map);
          setApiConnected(true);
        }
      } catch {
        // Offline — keep fallback
      }
    })();
  }, []);

  // ── Fetch trajectory + impact when selected event changes ─────────────
  useEffect(() => {
    if (!event) return;
    setCurrentLeadTime(event.lead_time_hr ?? 72);
    setTrajectoryData(buildFallbackTrajectory(event));
    setImpactGeojson(null);

    (async () => {
      try {
        const [trajRes, impRes] = await Promise.all([
          fetch(`${API_BASE}/events/${selectedId}/trajectory`),
          fetch(`${API_BASE}/events/${selectedId}/impact`),
        ]);
        if (trajRes.ok) setTrajectoryData(await trajRes.json());
        if (impRes.ok) {
          const d = await impRes.json();
          setImpactGeojson(d.impact_zone_geojson);
        }
      } catch {
        // Keep fallback
      }
    })();
  }, [selectedId, event?.event_id]); // eslint-disable-line

  // ── Downscale ─────────────────────────────────────────────────────────
  const handleTriggerDownscale = useCallback(async () => {
    setIsDownscaling(true);
    try {
      const res = await fetch(`${API_BASE}/events/${selectedId}/downscale`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: selectedId, target_lead_time_hr: currentLeadTime, num_samples: 20 }),
      });
      setDownscaleData(res.ok ? await res.json() : {
        statistics: { p90_extreme_rainfall_peak: event?.peak_rainfall_mm_12hr * 1.35, spatial_uncertainty_mean: 22.4 },
      });
    } catch {
      setDownscaleData({
        statistics: { p90_extreme_rainfall_peak: event?.peak_rainfall_mm_12hr * 1.35, spatial_uncertainty_mean: 22.4 },
      });
    } finally {
      setIsDownscaling(false);
      setIsModalOpen(true);
    }
  }, [selectedId, currentLeadTime, event]);

  if (!event) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header style={{
        display: 'flex', alignItems: 'center', gap: 20,
        padding: '10px 20px', background: 'var(--surface)',
        borderBottom: '1px solid var(--line)', flexShrink: 0,
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'var(--text)', color: 'var(--bg)',
            display: 'grid', placeItems: 'center',
            font: '600 16px var(--font-mono)',
          }}>V</div>
          <div>
            <div style={{ font: '600 14px var(--font-mono)', letterSpacing: '.12em' }}>VAJRA</div>
            <div className="eyebrow" style={{ marginTop: 2 }}>Weather Threat Tracker · MoES · NCMRWF</div>
          </div>
        </div>

        {/* Pipeline pills */}
        <div className="header-pipeline" style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '0 auto' }}>
          <div className="stage-pill">
            <span className="eyebrow">Stage 1 · GNN</span>
            <em>ICOSA-MESH L5</em>
          </div>
          <span style={{ color: 'var(--muted)' }}>→</span>
          <div className="stage-pill">
            <span className="eyebrow">EFI Anomaly</span>
            <em>ERA5 30yr Baseline</em>
          </div>
          <span style={{ color: 'var(--muted)' }}>→</span>
          <div className="stage-pill">
            <span className="eyebrow">Stage 2 · Diffusion</span>
            <em>12 km → 5 km</em>
          </div>
          <span style={{ color: 'var(--muted)' }}>→</span>
          <div className="stage-pill">
            <span className="eyebrow">Impact</span>
            <em>5 km Buffer</em>
          </div>
        </div>

        {/* Right: live + thresholds */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <button
            onClick={() => setShowThresholds(v => !v)}
            className="icon-btn"
            style={{ width: 'auto', padding: '0 12px', fontSize: 12, fontFamily: 'var(--font-sans)', gap: 6, display: 'flex', alignItems: 'center' }}
            title="Configure Risk Engine Thresholds"
          >
            ⚙ Thresholds
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, font: '500 11px var(--font-mono)', letterSpacing: '.08em', color: 'var(--ok)' }}>
            <div className="live-dot" />
            {apiConnected ? 'LIVE INFERENCE' : 'OFFLINE MODE'}
          </div>
        </div>
      </header>

      {/* ── Event Selector Row ──────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 8, padding: '8px 20px', background: 'var(--raised)', borderBottom: '1px solid var(--line)', flexShrink: 0, flexWrap: 'wrap' }}>
        {Object.values(events).map((ev: any) => (
          <button
            key={ev.event_id}
            onClick={() => setSelectedId(ev.event_id)}
            className={`event-chip ${ev.event_id === selectedId ? 'selected' : ''}`}
          >
            <span
              className="dot"
              style={{
                background: ev.color_code === 'RED' ? 'var(--alert)'
                  : ev.color_code === 'ORANGE' ? 'var(--amber)'
                  : 'var(--ok)',
              }}
            />
            {ev.event_id}
            <span className="eyebrow" style={{ marginLeft: 4 }}>{ev.event_type}</span>
          </button>
        ))}
      </div>

      {/* ── Main Layout ─────────────────────────────────────────────────── */}
      <div className="layout" style={{ flex: 1, display: 'grid', gridTemplateColumns: '380px 1fr', gap: 0, overflow: 'hidden' }}>

        {/* ── Left Sidebar ──────────────────────────────────────────────── */}
        <aside style={{
          display: 'flex', flexDirection: 'column', gap: 12,
          padding: 12, overflowY: 'auto',
          borderRight: '1px solid var(--line)',
        }}>
          <AlertPanel
            event={event}
            onTriggerDownscale={handleTriggerDownscale}
            isDownscaling={isDownscaling}
          />
          {showThresholds && <ThresholdControls />}
        </aside>

        {/* ── Map Area ──────────────────────────────────────────────────── */}
        <section style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
          {/* Map */}
          <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
            <MapView
              currentLeadTime={currentLeadTime}
              layers={layers}
              trajectoryData={trajectoryData}
              impactGeojson={impactGeojson}
              event={event}
            />

            {/* Layer controls */}
            <div className="layer-panel">
              <div className="eyebrow" style={{ marginBottom: 8 }}>Visual layers</div>
              {([
                ['showEnsembleTracks',   '50-member ensemble',      'var(--data)', .5],
                ['showUncertaintyCone',  '90% uncertainty envelope','var(--data)', .25],
                ['showImpactZone',       '5 km threat ring',        'var(--alert)',1 ],
                ['show5kmHeatmap',       '5 km downscaled field',   'var(--amber)',1 ],
                ['showWindStreamlines',  'Wind streamlines',        'var(--muted)',1 ],
              ] as const).map(([key, label, color, op]) => (
                <label key={key} className="layer-label">
                  <input
                    type="checkbox"
                    checked={layers[key as keyof typeof layers]}
                    onChange={e => setLayers(l => ({ ...l, [key]: e.target.checked }))}
                  />
                  {label}
                  <span className="sw" style={{ background: color, opacity: op }} />
                </label>
              ))}
            </div>

            {/* Region chip */}
            <div style={{
              position: 'absolute', top: 14, left: 14,
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 12px',
              background: 'var(--surface)', border: '1px solid var(--line)',
              borderRadius: 8, font: '500 11px var(--font-mono)', letterSpacing: '.06em',
              zIndex: 1000,
            }}>
              <div className="live-dot" style={{ width: 8, height: 8 }} />
              {event.event_type === 'CYCLONE' ? 'BAY OF BENGAL' :
               event.event_type === 'HEATWAVE' ? 'NW INDIA' :
               'KERALA / W GHATS'} · 12 KM EPS MESH
            </div>

            {/* Scale legend */}
            <div style={{
              position: 'absolute', left: 14, bottom: 14,
              padding: '6px 12px', background: 'var(--surface)',
              border: '1px solid var(--line)', borderRadius: 8,
              font: '11px var(--font-mono)', color: 'var(--muted)', zIndex: 1000,
            }}>
              Schematic scale · 5 km features enlarged for legibility
            </div>
          </div>

          {/* Timeline */}
          <TimeSlider
            currentLeadTime={currentLeadTime}
            availableLeadTimes={availableLeadTimes.length > 0 ? availableLeadTimes : [24, 48, 72, 96, 120]}
            onChange={setCurrentLeadTime}
          />
        </section>
      </div>

      {/* ── Downscaling Modal ─────────────────────────────────────────────── */}
      <DownscalingModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        downscaleData={downscaleData}
        event={event}
      />
    </div>
  );
};

export default App;
