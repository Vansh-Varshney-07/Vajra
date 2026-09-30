/**
 * Vajra API Client
 * Connects frontend dashboard to FastAPI microservice endpoints.
 */

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export interface AnomalyEvent {
  event_id: string;
  event_type: 'CYCLONE' | 'HEATWAVE' | 'COLDWAVE';
  name: string;
  probability: number;
  threat_level: 'LOW' | 'MODERATE' | 'SEVERE' | 'CATASTROPHIC';
  color_code: 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED';
  current_centroid: { lat: number; lon: number };
  peak_wind_kmh: number;
  peak_rainfall_mm_12hr: number;
  lead_time_hr: number;
  action_recommended: string;
  trajectory: Array<{ lead_time_hr: number; lat: number; lon: number; intensity: number }>;
}

export interface TrajectoryResponse {
  event_id: string;
  consensus_path: any;
  ensemble_tracks: number[][][];
  waypoints: Array<{ lead_time_hr: number; lat: number; lon: number; intensity: number }>;
}

export interface ImpactResponse {
  event_id: string;
  impact_zone_geojson: any;
  action_advisory: string;
}

export interface DownscaleResponse {
  event_id: string;
  target_lead_time_hr: number;
  grid_resolution_km: number;
  grid_dimensions: [number, number];
  statistics: {
    mean_rainfall_peak: number;
    p90_extreme_rainfall_peak: number;
    spatial_uncertainty_mean: number;
  };
  raster_sample_p90: number[][];
}

export const vajraApi = {
  async getHealth() {
    const res = await fetch(`${API_BASE_URL}/`);
    return res.json();
  },

  async getEvents(): Promise<AnomalyEvent[]> {
    const res = await fetch(`${API_BASE_URL}/events`);
    if (!res.ok) throw new Error('Failed to fetch events');
    return res.json();
  },

  async getEvent(eventId: string): Promise<AnomalyEvent> {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}`);
    if (!res.ok) throw new Error(`Failed to fetch event ${eventId}`);
    return res.json();
  },

  async getTrajectory(eventId: string): Promise<TrajectoryResponse> {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/trajectory`);
    if (!res.ok) throw new Error(`Failed to fetch trajectory for ${eventId}`);
    return res.json();
  },

  async getImpactZone(eventId: string): Promise<ImpactResponse> {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/impact`);
    if (!res.ok) throw new Error(`Failed to fetch impact zone for ${eventId}`);
    return res.json();
  },

  async runDownscale(eventId: string, leadTimeHr: number = 72): Promise<DownscaleResponse> {
    const res = await fetch(`${API_BASE_URL}/events/${eventId}/downscale`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_id: eventId,
        target_lead_time_hr: leadTimeHr,
        num_samples: 20,
      }),
    });
    if (!res.ok) throw new Error(`Failed to downscale event ${eventId}`);
    return res.json();
  },

  async triggerForecastPipeline(members: number = 50) {
    const res = await fetch(`${API_BASE_URL}/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ensemble_members: members }),
    });
    return res.json();
  },
};
