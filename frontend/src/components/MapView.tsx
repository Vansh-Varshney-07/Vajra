import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { WindLayer } from './WindLayer';
import { RainfallGrid } from './RainfallGrid';
import { useCartoLayer } from './CartoLayer';

interface MapViewProps {
  currentLeadTime: number;
  layers: {
    showEnsembleTracks: boolean;
    showUncertaintyCone: boolean;
    showImpactZone: boolean;
    show5kmHeatmap: boolean;
    showWindStreamlines?: boolean;
    showCartoCoastal?: boolean;
  };
  trajectoryData: {
    waypoints: Array<{ lead_time_hr: number; lat: number; lon: number; intensity: number }>;
    ensemble_tracks: Array<Array<[number, number]>>;
  };
  impactGeojson: any;
  event?: any;
  onCartoStatusChange?: (status: { connected: boolean; message: string }) => void;
}

// Centre of map based on event type
function getMapCentre(event?: any): [number, number] {
  if (!event) return [18.5, 87.0];
  const c = event.current_centroid;
  return [c.lat, c.lon];
}

export const MapView: React.FC<MapViewProps> = ({
  currentLeadTime,
  layers,
  trajectoryData,
  impactGeojson,
  event,
  onCartoStatusChange,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef  = useRef<L.Map | null>(null);
  const layerGroupRef   = useRef<L.LayerGroup | null>(null);

  // ── CARTO GIS boundary overlay hook ─────────────────────────────────────
  useCartoLayer({
    map: mapInstanceRef.current,
    visible: layers.showCartoCoastal ?? true,
    layerType: 'coastal',
    onStatusChange: onCartoStatusChange,
  });

  // ── Initialize map ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const centre = getMapCentre(event);
    const map = L.map(mapContainerRef.current, {
      center: centre,
      zoom: 6,
      zoomControl: false,
      attributionControl: false,
    });

    // Clean high-contrast dark canvas basemap (No watermark, 100% free)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16,
    }).addTo(map);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16,
      opacity: 0.65,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const lg = L.layerGroup().addTo(map);
    layerGroupRef.current = lg;
    mapInstanceRef.current = map;

    return () => { map.remove(); mapInstanceRef.current = null; };
  }, []); // eslint-disable-line

  // ── Pan to new event centroid ────────────────────────────────────────────
  useEffect(() => {
    if (!mapInstanceRef.current || !event) return;
    const c = event.current_centroid;
    mapInstanceRef.current.setView([c.lat, c.lon], 6, { animate: true });
  }, [event?.event_id]); // eslint-disable-line

  // ── Re-draw layers when data changes ────────────────────────────────────
  useEffect(() => {
    if (!mapInstanceRef.current || !layerGroupRef.current) return;
    const lg = layerGroupRef.current;
    lg.clearLayers();

    const { waypoints = [], ensemble_tracks = [] } = trajectoryData;

    // 1. Ensemble spaghetti tracks
    if (layers.showEnsembleTracks && ensemble_tracks.length > 0) {
      ensemble_tracks.forEach(track => {
        const latLngs = track.map(([lon, lat]) => [lat, lon] as [number, number]);
        L.polyline(latLngs, { color: '#6DB6F5', weight: 1.1, opacity: 0.28, dashArray: '4,4' }).addTo(lg);
      });
    }

    // 2. Uncertainty cone polygon
    if (layers.showUncertaintyCone && ensemble_tracks.length > 0) {
      const minLen = Math.min(...ensemble_tracks.map(t => t.length));
      const leftBoundary: [number, number][] = [];
      const rightBoundary: [number, number][] = [];
      for (let i = 0; i < minLen; i++) {
        const pts = ensemble_tracks.map(t => t[i]);
        const lats = pts.map(p => p[1]);
        const lons = pts.map(p => p[0]);
        const avgLon = lons.reduce((a, b) => a + b, 0) / lons.length;
        const avgLat = lats.reduce((a, b) => a + b, 0) / lats.length;
        const spread = (i + 1) * 0.35;
        leftBoundary.push([avgLat + spread * 0.4, avgLon - spread * 0.5]);
        rightBoundary.push([avgLat - spread * 0.4, avgLon + spread * 0.5]);
      }
      L.polygon([...leftBoundary, ...rightBoundary.reverse()], {
        color: '#6DB6F5', fillColor: '#6DB6F5', fillOpacity: 0.1,
        weight: 1.5, dashArray: '3,6',
      }).addTo(lg);
    }

    // 3. Consensus track
    if (waypoints.length > 0) {
      const consensusLatLngs = waypoints.map(wp => [wp.lat, wp.lon] as [number, number]);
      L.polyline(consensusLatLngs, { color: '#6DB6F5', weight: 3, opacity: 0.9 }).addTo(lg);

      waypoints.forEach(wp => {
        const isCurrent = wp.lead_time_hr === currentLeadTime;
        const marker = L.circleMarker([wp.lat, wp.lon], {
          radius: isCurrent ? 9 : 4.5,
          color: isCurrent ? '#FF5E52' : '#6DB6F5',
          fillColor: isCurrent ? '#FF5E52' : '#151A1D',
          fillOpacity: 0.9,
          weight: 2,
        });
        marker.bindPopup(`
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#1E293B">
            <b>T+${wp.lead_time_hr}h</b><br/>
            Intensity: ${wp.intensity} km/h<br/>
            ${wp.lat.toFixed(2)}°N, ${wp.lon.toFixed(2)}°E
          </div>
        `);
        marker.addTo(lg);
      });
    }

    // 4. 5 km impact zone
    if (layers.showImpactZone && impactGeojson) {
      L.geoJSON(impactGeojson, {
        style: { color: '#FF5E52', fillColor: '#FF5E52', fillOpacity: 0.2, weight: 2.5 },
      }).addTo(lg);
    }

    // 5. 5 km downscaled heatmap simulation ring
    if (layers.show5kmHeatmap && waypoints.length > 0) {
      const currWp = waypoints.find(w => w.lead_time_hr === currentLeadTime) || waypoints[Math.floor(waypoints.length / 2)];
      if (currWp) {
        L.circle([currWp.lat, currWp.lon], {
          radius: 38000, color: '#F0A63A', fillColor: '#F0A63A',
          fillOpacity: 0.18, weight: 1.2,
        }).addTo(lg);
      }
    }
  }, [layers, trajectoryData, impactGeojson, currentLeadTime]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />
      <WindLayer visible={layers.showWindStreamlines ?? true} intensity={event?.event_type === 'CYCLONE' ? 1.4 : 0.7} />
      <RainfallGrid visible={layers.show5kmHeatmap} />
    </div>
  );
};
