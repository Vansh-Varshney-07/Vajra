/**
 * carto.ts — CARTO Maps API + SQL API integration for Vajra
 *
 * Provides:
 *  - cartoTileUrl()       → Authenticated vector tile URL for a CARTO dataset
 *  - cartoSqlQuery()      → Run spatial SQL against CARTO data warehouse
 *  - cartoBoundaryLayer() → Fetch admin boundary GeoJSON from CARTO
 *  - cartoVizStyle()      → Standard CARTO color ramp for precipitation/wind layers
 *
 * Setup:
 *   1. Set VITE_CARTO_API_TOKEN in frontend/.env
 *   2. Set VITE_CARTO_API_BASE_URL=https://gcp-asia-northeast1.api.carto.com
 */

const CARTO_BASE = import.meta.env.VITE_CARTO_API_BASE_URL || 'https://gcp-asia-northeast1.api.carto.com';
const CARTO_TOKEN = import.meta.env.VITE_CARTO_API_TOKEN || '';
const CARTO_ACCOUNT = import.meta.env.VITE_CARTO_ACCOUNT_ID || 'ac_yl5r440d';

export const isCartoConnected = (): boolean => !!CARTO_TOKEN;

// ─── Auth headers ──────────────────────────────────────────────────────────
function cartoHeaders(): HeadersInit {
  return {
    'Authorization': `Bearer ${CARTO_TOKEN}`,
    'Content-Type': 'application/json',
  };
}

// ─── Maps API: Tile URL for a CARTO dataset ─────────────────────────────────
/**
 * Returns an XYZ tile URL template for rendering a CARTO dataset on Leaflet.
 * Usage: L.tileLayer(cartoTileUrl('my_dataset'))
 */
export function cartoTileUrl(tableName: string, connection = 'carto_dw'): string {
  const encoded = encodeURIComponent(`SELECT * FROM ${tableName}`);
  return (
    `${CARTO_BASE}/v3/maps/${CARTO_ACCOUNT}/${connection}/tileset/{z}/{x}/{y}` +
    `?apiVersion=v3&q=${encoded}&formatTiles=mvt&access_token=${CARTO_TOKEN}`
  );
}

// ─── SQL API: Run spatial SQL ────────────────────────────────────────────────
/**
 * Execute spatial SQL against the CARTO data warehouse.
 * Returns raw JSON from the CARTO SQL API.
 */
export async function cartoSqlQuery(sql: string, connection = 'carto_dw'): Promise<any> {
  if (!CARTO_TOKEN) {
    console.warn('[CARTO] No API token set. Set VITE_CARTO_API_TOKEN in frontend/.env');
    return null;
  }
  const url = `${CARTO_BASE}/v3/sql/${CARTO_ACCOUNT}/${connection}/query`;
  const res = await fetch(url, {
    method: 'POST',
    headers: cartoHeaders(),
    body: JSON.stringify({ q: sql }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`CARTO SQL Error ${res.status}: ${err}`);
  }
  return res.json();
}

// ─── Maps API: Fetch GeoJSON boundary from CARTO ────────────────────────────
/**
 * Fetch a GeoJSON FeatureCollection from CARTO for a given SQL query.
 * Useful for admin boundary overlays (India states, coastal districts).
 */
export async function cartoBoundaryLayer(
  sql: string,
  connection = 'carto_dw'
): Promise<GeoJSON.FeatureCollection | null> {
  if (!CARTO_TOKEN) return null;
  const url = `${CARTO_BASE}/v3/sql/${CARTO_ACCOUNT}/${connection}/query?q=${encodeURIComponent(sql)}&format=geojson`;
  const res = await fetch(url, { headers: cartoHeaders() });
  if (!res.ok) return null;
  return res.json();
}

// ─── Standard color ramps for Vajra overlays ────────────────────────────────
export const CARTO_RAMPS = {
  precipitation: ['#edf8b1', '#7fcdbb', '#2c7fb8', '#1a3f5c'],  // light→dark blue
  wind:          ['#f7f7f7', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac'],
  heatwave:      ['#fee391', '#fec44f', '#fe9929', '#d95f0e', '#993404'],
  efi:           ['#2166ac', '#abd9e9', '#fdae61', '#d7191c'],   // cold→hot EFI
} as const;

// ─── CARTO datasets expected in account ac_yl5r440d ─────────────────────────
// These match what the CARTO MCP server would discover via its tools.
// Update these to your actual CARTO data warehouse table names.
export const CARTO_DATASETS = {
  /** Indian administrative districts (coastal zones) */
  INDIA_DISTRICTS: 'carto-data.ac_yl5r440d.sub_ind_india_districts_1',
  /** Bay of Bengal bathymetry / coastal outline */
  BOB_COASTAL:     'carto-data.ac_yl5r440d.sub_ind_india_coastal_districts',
  /** NCMRWF NWP output grid cells (if loaded into CARTO DW) */
  NWP_GRID:        'carto-data.ac_yl5r440d.nwp_grid_south_asia_12km',
} as const;

// ─── Convenience: verify connection ─────────────────────────────────────────
export async function verifyCartoConnection(): Promise<{ connected: boolean; account?: string; error?: string }> {
  if (!CARTO_TOKEN) {
    return { connected: false, error: 'No API token configured. Set VITE_CARTO_API_TOKEN.' };
  }
  try {
    const res = await fetch(`${CARTO_BASE}/v3/connections`, { headers: cartoHeaders() });
    if (res.ok) {
      return { connected: true, account: CARTO_ACCOUNT };
    }
    const data = await res.json().catch(() => ({}));
    const allowed = data.allowed_a_p_is || data.allowedAPIs || [];
    if (allowed.includes('mcp') || allowed.includes('resources')) {
      return { connected: true, account: `${CARTO_ACCOUNT} (MCP)` };
    }
    return { connected: false, error: `HTTP ${res.status}` };
  } catch (e: any) {
    return { connected: false, error: e.message };
  }
}
