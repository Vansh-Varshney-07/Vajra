import { useEffect, useRef } from 'react';
import L from 'leaflet';
import {
  isCartoConnected,
  cartoBoundaryLayer,
  verifyCartoConnection,
  CARTO_DATASETS,
} from '../carto';

interface CartoLayerProps {
  map: L.Map | null;
  visible: boolean;
  /** Which layer to show: 'districts' | 'coastal' | 'nwp_grid' */
  layerType?: 'districts' | 'coastal' | 'nwp_grid';
  onStatusChange?: (status: { connected: boolean; message: string }) => void;
}

/**
 * CartoLayer — adds CARTO-sourced GeoJSON overlays to the Leaflet map.
 *
 * When VITE_CARTO_API_TOKEN is set, fetches real data from the CARTO DW.
 * When token is absent (offline / demo mode), renders a placeholder outline.
 */
export function useCartoLayer({
  map,
  visible,
  layerType = 'coastal',
  onStatusChange,
}: CartoLayerProps): void {
  const layerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    if (!map) return;

    // Remove previous layer
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }

    if (!visible) return;

    (async () => {
      // ── Verify CARTO connection ────────────────────────────────────────────
      const status = await verifyCartoConnection();
      onStatusChange?.({
        connected: status.connected,
        message: status.connected
          ? `CARTO connected (${status.account})`
          : `CARTO offline: ${status.error}`,
      });

      if (!isCartoConnected() || !status.connected) {
        // ── Fallback: draw a simple coastal outline for Bay of Bengal ────────
        const fallbackCoords: [number, number][] = [
          [79.75, 12], [80.3, 13.1], [80.2, 14.4], [80.1, 15.8],
          [80.9, 15.8], [82.3, 16.9], [83.3, 17.7], [84, 18.3],
          [84.9, 19.3], [85.8, 19.8], [86.7, 20.3], [86.9, 20.8],
          [87, 21.5], [87.5, 21.6], [88.3, 21.7], [89, 21.8],
          [90, 22], [90.8, 22.4], [91.6, 22.2], [92.3, 21],
        ];
        const fallbackGeoJson: GeoJSON.Feature = {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: fallbackCoords },
          properties: { name: 'Bay of Bengal Coast (demo)', source: 'static' },
        };
        layerRef.current = L.geoJSON(fallbackGeoJson, {
          style: { color: '#3A454C', weight: 1.5, opacity: 0.6 },
        }).addTo(map);
        return;
      }

      // ── Fetch real CARTO boundary ──────────────────────────────────────────
      const sqlMap: Record<string, string> = {
        districts: `SELECT geom, district_name, state_name FROM \`${CARTO_DATASETS.INDIA_DISTRICTS}\` WHERE coastal = true LIMIT 50`,
        coastal:   `SELECT geom, name FROM \`${CARTO_DATASETS.BOB_COASTAL}\` LIMIT 100`,
        nwp_grid:  `SELECT geom, grid_id FROM \`${CARTO_DATASETS.NWP_GRID}\` LIMIT 500`,
      };

      const sql = sqlMap[layerType];
      const geojson = await cartoBoundaryLayer(sql);

      if (!geojson) return;

      layerRef.current = L.geoJSON(geojson, {
        style: feat => ({
          color: layerType === 'districts' ? '#6DB6F5' : '#3A454C',
          fillColor: layerType === 'districts' ? '#6DB6F5' : 'transparent',
          fillOpacity: layerType === 'districts' ? 0.06 : 0,
          weight: layerType === 'coastal' ? 1.5 : 0.8,
          opacity: 0.7,
        }),
        onEachFeature: (feat, layer) => {
          if (feat.properties?.district_name || feat.properties?.name) {
            layer.bindTooltip(
              feat.properties.district_name || feat.properties.name,
              { className: 'leaflet-carto-tooltip', sticky: true }
            );
          }
        },
      }).addTo(map);
    })();

    return () => {
      if (layerRef.current && map) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, visible, layerType]); // eslint-disable-line
}
