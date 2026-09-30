import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface MapViewProps {
  currentLeadTime: number;
  layers: {
    showEnsembleTracks: boolean;
    showUncertaintyCone: boolean;
    showImpactZone: boolean;
    show5kmHeatmap: boolean;
  };
  trajectoryData: {
    waypoints: Array<{ lead_time_hr: number; lat: number; lon: number; intensity: number }>;
    ensemble_tracks: Array<Array<[number, number]>>;
  };
  impactGeojson: any;
  onWaypointSelect?: (wp: any) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  currentLeadTime,
  layers,
  trajectoryData,
  impactGeojson
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [18.5, 87.0],
      zoom: 6,
      zoomControl: false,
      attributionControl: false
    });

    // Dark high-contrast basemap (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    layerGroupRef.current = layerGroup;
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Layers when props change
  useEffect(() => {
    if (!mapInstanceRef.current || !layerGroupRef.current) return;
    const lg = layerGroupRef.current;
    lg.clearLayers();

    const { waypoints, ensemble_tracks } = trajectoryData;

    // 1. Render Ensemble Spaghetti Tracks (20 members)
    if (layers.showEnsembleTracks && ensemble_tracks) {
      ensemble_tracks.forEach((track) => {
        const latLngs = track.map(([lon, lat]) => [lat, lon] as [number, number]);
        L.polyline(latLngs, {
          color: '#38BDF8',
          weight: 1.2,
          opacity: 0.28,
          dashArray: '4, 4'
        }).addTo(lg);
      });
    }

    // 2. Render Uncertainty Cone Polygon (Shaded envelope)
    if (layers.showUncertaintyCone && ensemble_tracks && ensemble_tracks.length > 0) {
      const minLen = Math.min(...ensemble_tracks.map((t) => t.length));
      const leftBoundary: [number, number][] = [];
      const rightBoundary: [number, number][] = [];

      for (let i = 0; i < minLen; i++) {
        const pts = ensemble_tracks.map((t) => t[i]);
        const lats = pts.map((p) => p[1]);
        const lons = pts.map((p) => p[0]);
        const avgLon = lons.reduce((a, b) => a + b, 0) / lons.length;
        const avgLat = lats.reduce((a, b) => a + b, 0) / lats.length;
        const spread = (i + 1) * 0.35;

        leftBoundary.push([avgLat + spread * 0.4, avgLon - spread * 0.5]);
        rightBoundary.push([avgLat - spread * 0.4, avgLon + spread * 0.5]);
      }

      const conePolygon = [...leftBoundary, ...rightBoundary.reverse()];
      L.polygon(conePolygon, {
        color: '#F59E0B',
        fillColor: '#F59E0B',
        fillOpacity: 0.15,
        weight: 1.5,
        dashArray: '3, 6'
      }).addTo(lg);
    }

    // 3. Render Consensus Trajectory Track
    if (waypoints && waypoints.length > 0) {
      const consensusLatLngs = waypoints.map((wp) => [wp.lat, wp.lon] as [number, number]);
      L.polyline(consensusLatLngs, {
        color: '#06B6D4',
        weight: 3.5,
        opacity: 0.95
      }).addTo(lg);

      // Render Waypoints
      waypoints.forEach((wp) => {
        const isCurrent = wp.lead_time_hr === currentLeadTime;
        const marker = L.circleMarker([wp.lat, wp.lon], {
          radius: isCurrent ? 9 : 5,
          color: isCurrent ? '#EF4444' : '#06B6D4',
          fillColor: isCurrent ? '#EF4444' : '#070B12',
          fillOpacity: 0.9,
          weight: 2
        });

        marker.bindPopup(`
          <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; color: #1E293B;">
            <strong>Lead Time: T+${wp.lead_time_hr}h</strong><br/>
            <span>Intensity: ${wp.intensity} km/h</span><br/>
            <span>Coord: ${wp.lat.toFixed(2)}°N, ${wp.lon.toFixed(2)}°E</span>
          </div>
        `);
        marker.addTo(lg);
      });
    }

    // 4. Render 5km Geodesic Impact Zone
    if (layers.showImpactZone && impactGeojson) {
      L.geoJSON(impactGeojson, {
        style: {
          color: '#EF4444',
          fillColor: '#EF4444',
          fillOpacity: 0.35,
          weight: 2.5
        }
      }).addTo(lg);
    }

    // 5. Render 5km Heatmap Simulation
    if (layers.show5kmHeatmap && waypoints.length > 0) {
      const currWp = waypoints.find((w) => w.lead_time_hr === currentLeadTime) || waypoints[2];
      if (currWp) {
        L.circle([currWp.lat, currWp.lon], {
          radius: 35000,
          color: '#10B981',
          fillColor: '#06B6D4',
          fillOpacity: 0.22,
          weight: 1
        }).addTo(lg);
      }
    }
  }, [layers, trajectoryData, impactGeojson, currentLeadTime]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Floating Coordinates Tag */}
      <div
        className="glass-panel"
        style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          padding: '8px 16px',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}
      >
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981' }} />
        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          REGION: BAY OF BENGAL · 12KM EPS MESH
        </span>
      </div>
    </div>
  );
};
