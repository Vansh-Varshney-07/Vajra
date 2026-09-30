import React, { useState, useEffect } from 'react';
import { MapView } from './components/MapView';
import { AlertPanel } from './components/AlertPanel';
import { TimeSlider } from './components/TimeSlider';
import { DownscalingModal } from './components/DownscalingModal';
import { Layers, Activity, Cpu } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const FALLBACK_EVENT = {
  event_id: 'BOB-CYC-2026-001',
  event_type: 'CYCLONE',
  name: 'Cyclone Amphan Replay (Bay of Bengal)',
  probability: 0.88,
  threat_level: 'SEVERE',
  color_code: 'RED',
  current_centroid: { lat: 19.82, lon: 86.85 },
  peak_wind_kmh: 145.0,
  peak_rainfall_mm_12hr: 195.0,
  lead_time_hr: 72,
  action_recommended: 'Immediate evacuation of 5km coastal zone. Severe storm surge alert across Digha & Balasore sectors.'
};

const FALLBACK_TRAJECTORY = {
  waypoints: [
    { lead_time_hr: 24, lat: 13.5, lon: 87.2, intensity: 85.0 },
    { lead_time_hr: 48, lat: 16.8, lon: 87.0, intensity: 115.0 },
    { lead_time_hr: 72, lat: 19.82, lon: 86.85, intensity: 145.0 },
    { lead_time_hr: 96, lat: 22.1, lon: 87.8, intensity: 130.0 },
    { lead_time_hr: 120, lat: 24.3, lon: 89.2, intensity: 75.0 }
  ],
  ensemble_tracks: Array.from({ length: 20 }, (_, idx) => {
    return [
      [87.2 + (idx - 10) * 0.04, 13.5 + (idx - 10) * 0.03],
      [87.0 + (idx - 10) * 0.08, 16.8 + (idx - 10) * 0.06],
      [86.85 + (idx - 10) * 0.12, 19.82 + (idx - 10) * 0.08],
      [87.8 + (idx - 10) * 0.18, 22.1 + (idx - 10) * 0.14],
      [89.2 + (idx - 10) * 0.25, 24.3 + (idx - 10) * 0.2]
    ] as [number, number][];
  })
};

export const App: React.FC = () => {
  const [event, setEvent] = useState<any>(FALLBACK_EVENT);
  const [trajectoryData, setTrajectoryData] = useState<any>(FALLBACK_TRAJECTORY);
  const [impactGeojson, setImpactGeojson] = useState<any>(null);
  const [currentLeadTime, setCurrentLeadTime] = useState<number>(72);
  const [isDownscaling, setIsDownscaling] = useState<boolean>(false);
  const [downscaleData, setDownscaleData] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  // Layer Visibility State
  const [layers, setLayers] = useState({
    showEnsembleTracks: true,
    showUncertaintyCone: true,
    showImpactZone: true,
    show5kmHeatmap: true
  });

  // Fetch initial event & trajectory from FastAPI
  useEffect(() => {
    const fetchData = async () => {
      try {
        const eventRes = await fetch(`${API_BASE}/events/BOB-CYC-2026-001`);
        if (eventRes.ok) {
          const evData = await eventRes.json();
          setEvent(evData);
        }

        const trajRes = await fetch(`${API_BASE}/events/BOB-CYC-2026-001/trajectory`);
        if (trajRes.ok) {
          const tData = await trajRes.json();
          setTrajectoryData(tData);
        }

        const impactRes = await fetch(`${API_BASE}/events/BOB-CYC-2026-001/impact`);
        if (impactRes.ok) {
          const impData = await impactRes.json();
          setImpactGeojson(impData.impact_zone_geojson);
        }
      } catch (err) {
        console.log('Using local fallback state (FastAPI backend can be connected locally).');
      }
    };

    fetchData();
  }, []);

  const handleTriggerDownscale = async () => {
    setIsDownscaling(true);
    try {
      const res = await fetch(`${API_BASE}/events/BOB-CYC-2026-001/downscale`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: 'BOB-CYC-2026-001',
          target_lead_time_hr: currentLeadTime,
          num_samples: 20
        })
      });

      if (res.ok) {
        const data = await res.json();
        setDownscaleData(data);
      } else {
        throw new Error('Fallback to local simulation');
      }
    } catch {
      // Local fallback simulation
      setDownscaleData({
        statistics: {
          p90_extreme_rainfall_peak: 195.0,
          spatial_uncertainty_mean: 22.4
        }
      });
    } finally {
      setIsDownscaling(false);
      setIsModalOpen(true);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: 'var(--bg-primary)' }}>
      {/* Top Navigation Bar */}
      <header
        className="glass-panel"
        style={{
          height: '60px',
          margin: '8px 12px',
          padding: '0 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderRadius: '10px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.1rem',
              color: '#FFF'
            }}
          >
            V
          </div>
          <div>
            <h1 style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#F8FAFC' }}>
              VAJRA <span style={{ color: '#06B6D4', fontWeight: 500 }}>· WEATHER THREAT TRACKER</span>
            </h1>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Ministry of Earth Sciences (MoES) · NCMRWF
            </div>
          </div>
        </div>

        {/* Center Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={15} color="#10B981" />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              STAGE 1 GNN: <strong>ICOSA-MESH L5</strong>
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={15} color="#38BDF8" />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              STAGE 2 DIFFUSION: <strong>12KM → 5KM</strong>
            </span>
          </div>
        </div>

        {/* Right Status Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="glass-badge" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }} />
            LIVE INFERENCE
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <div style={{ display: 'flex', flex: 1, padding: '0 12px 12px 12px', gap: '12px', overflow: 'hidden' }}>
        {/* Left Side: Alert & Threat Overview Panel */}
        <div style={{ width: '420px', height: '100%' }}>
          <AlertPanel
            event={event}
            onTriggerDownscale={handleTriggerDownscale}
            isDownscaling={isDownscaling}
          />
        </div>

        {/* Center: Interactive GIS Map & Timeline Scrubber */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px', height: '100%', position: 'relative' }}>
          <div className="glass-panel" style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
            <MapView
              currentLeadTime={currentLeadTime}
              layers={layers}
              trajectoryData={trajectoryData}
              impactGeojson={impactGeojson}
            />

            {/* Floating Layer Controls (Top Right of Map) */}
            <div
              className="glass-panel"
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                padding: '12px 16px',
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                <Layers size={13} style={{ display: 'inline', marginRight: '4px' }} /> Visual Layers
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#F8FAFC', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={layers.showEnsembleTracks}
                  onChange={(e) => setLayers({ ...layers, showEnsembleTracks: e.target.checked })}
                />
                50-Member Ensemble Tracks
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#F8FAFC', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={layers.showUncertaintyCone}
                  onChange={(e) => setLayers({ ...layers, showUncertaintyCone: e.target.checked })}
                />
                90% Uncertainty Envelope
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#EF4444', cursor: 'pointer', fontWeight: 600 }}>
                <input
                  type="checkbox"
                  checked={layers.showImpactZone}
                  onChange={(e) => setLayers({ ...layers, showImpactZone: e.target.checked })}
                />
                5 km Geodesic Threat Ring
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#06B6D4', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={layers.show5kmHeatmap}
                  onChange={(e) => setLayers({ ...layers, show5kmHeatmap: e.target.checked })}
                />
                5 km Downscaled Simulation
              </label>
            </div>
          </div>

          {/* Bottom Timeline Scrubber */}
          <TimeSlider
            currentLeadTime={currentLeadTime}
            availableLeadTimes={[24, 48, 72, 96, 120]}
            onChange={setCurrentLeadTime}
          />
        </div>
      </div>

      {/* Downscale Showcase Modal */}
      <DownscalingModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        downscaleData={downscaleData}
      />
    </div>
  );
};

export default App;
