# Vajra — Final Implementation Blueprint
### PS 26078 · AI-Driven Spatio-Temporal Tracking of Extreme Weather Anomalies
#### Ministry of Earth Sciences (MoES) / NCMRWF

---

> **Strategy:** Start with one event type + one region (Cyclone over Indian Ocean → East Coast), prove the pipeline end-to-end, then generalize. Every component here is scoped to be demo-able.

---

## 1. System Architecture (Master Diagram)

```
NEPS-G / NCUM / ERA5 / IMDAA (GRIB2 / NetCDF)
                    │
                    ▼
     ┌──────────────────────────────┐
     │      Data Ingestion Layer    │
     │  Xarray + Dask + cfgrib      │
     │  GRIB2 → Zarr (chunked)      │
     └──────────────┬───────────────┘
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
┌──────────────┐         ┌────────────────────┐
│  Climatology │         │   Event Dataset     │
│  ERA5 30-yr  │         │   Construction      │
│  percentiles │         │   (EFI + Z-scores)  │
└──────┬───────┘         └─────────┬───────────┘
       └──────────┬────────────────┘
                  ▼
     ┌────────────────────────────┐
     │   EFI / Anomaly Field      │
     │   (per variable + event)   │
     └────────────┬───────────────┘
                  ▼
     ┌────────────────────────────┐
     │  Stage 1: Spherical GNN    │
     │  Icosahedral Mesh (L5/L6)  │
     │  DGL / PyTorch Geometric   │
     │  Spatio-Temporal MPNN      │
     └────────────┬───────────────┘
                  │
      ┌───────────┴──────────────┐
      │  4D Event Tracking       │
      │  centroid + GeoPolygon   │
      │  ensemble trajectories   │
      │  uncertainty cone        │
      └──────────────┬───────────┘
                     ▼
     ┌────────────────────────────┐
     │  Stage 2: Conditional      │
     │  Diffusion  12km → 5km     │
     │  HF Diffusers / CorrDiff   │
     │  Amplitude-Preserving      │
     └────────────┬───────────────┘
                  ▼
     ┌────────────────────────────┐
     │  Physics Validation Layer  │
     │  MetPy + Custom Loss       │
     │  Divergence / Moisture     │
     └────────────┬───────────────┘
                  ▼
     ┌────────────────────────────┐
     │  Impact / Risk Engine      │
     │  Flood / Wind / Heat       │
     │  Configurable Thresholds   │
     └────────┬──────────┬────────┘
              ▼          ▼
       ┌──────────┐  ┌──────────────────┐
       │ FastAPI  │  │  React Dashboard │
       │ REST API │  │  MapLibre GL JS  │
       │ GeoJSON  │  │  deck.gl Layers  │
       └──────────┘  └──────────────────┘
```

---

## 2. Data Layer — The First Real Milestone

> **Critical rule:** Validate this layer before any model training. Bad or inaccessible data kills everything else.

### 2.1 Directory Structure

```
data/
├── raw/
│   ├── ERA5/          ← 30-year reanalysis (1991–2020), GRIB2
│   ├── IMDAA/         ← Indian reanalysis alternative to ERA5
│   ├── NEPS-G/        ← 50-member global ensemble, 12 km, GRIB2
│   └── NCUM/          ← Deterministic 12 km, GRIB2
│
├── processed/
│   ├── climatology.zarr   ← mean, std, p90, p95, p99 per DOY
│   ├── events.zarr        ← labeled event cubes (Amphan, heatwaves, etc.)
│   └── training.zarr      ← (12km_coarse, 5km_target) paired samples
│
└── terrain/
    ├── srtm_india_1km.tif ← Static DEM for downscaling conditioning
    └── landuse_india.tif  ← Land/sea mask, crop zones
```

### 2.2 4D Dataset Schema

```
Dimensions: (time × ensemble_member × latitude × longitude)

Example shape:
  (40 forecast_lead_times,
   50 ensemble_members,
   1500 lat_points,
   3000 lon_points)

Variables per grid point:
  u10       → 10m zonal wind (m/s)
  v10       → 10m meridional wind (m/s)
  t2m       → 2m temperature (K)
  q850      → 850 hPa specific humidity (kg/kg)
  mslp      → Mean sea-level pressure (Pa)
  tp        → Total precipitation (m/6hr)
  z500      → 500 hPa geopotential height (m²/s²)
  vort850   → 850 hPa relative vorticity (s⁻¹)
```

### 2.3 Ingestion Pipeline

```python
# vajra/ingestion/nwp_loader.py
import xarray as xr
import dask

def open_ensemble(grib_dir: str, chunks: dict) -> xr.Dataset:
    """Opens a GRIB2 ensemble run, converts to chunked Zarr-friendly Dataset."""
    ds = xr.open_mfdataset(
        f"{grib_dir}/*.grib2",
        engine="cfgrib",
        combine="nested",
        concat_dim="number",    # ensemble member axis
        parallel=True,
        chunks=chunks,
    )
    return ds

# Usage — never loads full array into RAM
chunks = {"time": 10, "number": 10, "latitude": 300, "longitude": 300}
ds = open_ensemble("data/raw/NEPS-G/amphan_run/", chunks)
ds.to_zarr("data/processed/events.zarr", mode="w")
```

---

## 3. Climatology & EFI — The Anomaly Foundation

### 3.1 Build the 30-Year Baseline

```python
# vajra/ingestion/climatology.py
import xarray as xr
import numpy as np

def build_climatology(era5_zarr: str, output_zarr: str):
    ds = xr.open_zarr(era5_zarr)       # 1991–2020 ERA5
    clim = xr.Dataset()
    for var in ["t2m", "tp", "u10", "v10", "mslp", "z500"]:
        clim[f"{var}_mean"] = ds[var].groupby("time.dayofyear").mean("time")
        clim[f"{var}_std"]  = ds[var].groupby("time.dayofyear").std("time")
        clim[f"{var}_p90"]  = ds[var].groupby("time.dayofyear").quantile(0.90, dim="time")
        clim[f"{var}_p95"]  = ds[var].groupby("time.dayofyear").quantile(0.95, dim="time")
        clim[f"{var}_p99"]  = ds[var].groupby("time.dayofyear").quantile(0.99, dim="time")
    clim.to_zarr(output_zarr, mode="w")
```

### 3.2 Extreme Forecast Index (EFI)

The EFI compares the forecast ensemble CDF against the climatological CDF:

EFI = (2/π) ∫₀¹ [Fc(p) - Ff(p)] / √(p(1-p)) dp

Where:
- Fc(p) = climatological CDF at percentile p
- Ff(p) = ensemble forecast CDF at percentile p
- EFI ∈ [-1, 1]. Values > **0.75** trigger anomaly isolation.

### 3.3 Variable Signatures by Event Type

| Event | Key Variables |
|---|---|
| **Cyclone** | ↓ MSLP, ↑ wind speed, ↑ precipitation, ↑ vorticity_850 |
| **Heatwave** | ↑ T_2m, ↑ T_850, ↑ Z_500 (ridging), ↓ soil moisture |
| **Cold Wave** | ↓ T_2m, ↓ T_850, ↑ wind speed, ↑ pressure |
| **Flash Flood** | ↑ precipitation, ↑ moisture convergence, ↑ LLJ winds |

---

## 4. Stage 1 — Spherical GNN (Tracking Core)

### 4.1 Why Icosahedral Mesh?

A flat latitude-longitude grid has critical problems:
- Grid cells near poles are geometrically tiny but represent the same resolution as tropical cells → false gradients
- Longitude wraps around at ±180° creating discontinuous edges for convolutions

An icosahedral mesh discretizes the sphere uniformly. Each vertex covers the same solid angle.

```
Level 0 (icosahedron): 12 nodes,      20 faces
Level 4:               2,562 nodes    (~200 km spacing)
Level 5:               10,242 nodes   (~50 km spacing)  ← Use for Stage 1
Level 6:               40,962 nodes   (~25 km spacing)
```

### 4.2 Mesh Construction

```python
# vajra/tracking/mesh.py
import numpy as np
from scipy.spatial import ConvexHull
import torch
from torch_geometric.data import Data

def generate_icosahedron():
    phi = (1.0 + np.sqrt(5.0)) / 2.0
    vertices = np.array([
        [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
        [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
        [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
    ], dtype=np.float32)
    vertices /= np.linalg.norm(vertices, axis=1, keepdims=True)
    hull = ConvexHull(vertices)
    return vertices, hull.simplices

def subdivide_mesh(vertices, faces, level=5):
    for _ in range(level):
        midpoint_cache = {}
        new_faces = []

        def get_midpoint(i1, i2):
            key = tuple(sorted((i1, i2)))
            if key in midpoint_cache:
                return midpoint_cache[key]
            mid = (vertices[i1] + vertices[i2]) / 2.0
            mid /= np.linalg.norm(mid)
            nonlocal vertices
            vertices = np.vstack([vertices, mid])
            idx = len(vertices) - 1
            midpoint_cache[key] = idx
            return idx

        for tri in faces:
            v1, v2, v3 = tri
            a, b, c = get_midpoint(v1, v2), get_midpoint(v2, v3), get_midpoint(v3, v1)
            new_faces.extend([[v1, a, c], [v2, b, a], [v3, c, b], [a, b, c]])
        faces = np.array(new_faces)
    return vertices, faces

def build_spherical_graph(level=5) -> Data:
    v, f = generate_icosahedron()
    vertices, faces = subdivide_mesh(v, f, level=level)
    edges = set()
    for tri in faces:
        for a, b in [(tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])]:
            edges.add((a, b)); edges.add((b, a))
    edge_index = torch.tensor(list(edges), dtype=torch.long).t().contiguous()
    pos = torch.tensor(vertices, dtype=torch.float32)
    return Data(pos=pos, edge_index=edge_index)
```

### 4.3 GNN Architecture

```
Node Features (8 per node):
  [u10, v10, t2m, q850, mslp, tp, z500, EFI]
              │
              ▼
  Linear Projection (8 → 128)
              │
              ▼
  Graph Attention Layer 1 (multi-head)
              │
  Graph Attention Layer 2 (multi-head)
              │
              ▼
  Temporal GRU / Transformer
  across 40 lead-time steps
              │
        ┌─────┴─────┐
        ▼           ▼
  Event Prob     Event Properties
  sigmoid        ├── centroid (lat, lon)
  P(event)       ├── severity (0-1)
                 ├── radius (km)
                 └── event_type (one-hot)
```

```python
# vajra/tracking/gnn_model.py
import torch
import torch.nn as nn
from torch_geometric.nn import GATv2Conv

class WeatherGNN(nn.Module):
    def __init__(self, in_channels=8, hidden=128, heads=4, num_classes=3):
        super().__init__()
        self.proj = nn.Linear(in_channels, hidden)
        self.gat1 = GATv2Conv(hidden, hidden // heads, heads=heads, edge_dim=3)
        self.gat2 = GATv2Conv(hidden, hidden // heads, heads=heads, edge_dim=3)
        self.gru  = nn.GRU(hidden, hidden, batch_first=True)
        self.event_prob    = nn.Sequential(nn.Linear(hidden, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())
        self.severity_head = nn.Sequential(nn.Linear(hidden, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())
        self.centroid_head = nn.Sequential(nn.Linear(hidden, 64), nn.ReLU(), nn.Linear(64, 2), nn.Tanh())

    def forward(self, x_seq, edge_index, edge_attr):
        # x_seq: [T, N, in_channels]
        embeddings = []
        for t in range(x_seq.shape[0]):
            x = self.proj(x_seq[t])
            x = self.gat1(x, edge_index, edge_attr)
            x = self.gat2(x, edge_index, edge_attr)
            embeddings.append(x)
        x_time = torch.stack(embeddings, dim=1)     # [N, T, hidden]
        x_gru, _ = self.gru(x_time)
        x_final = x_gru[:, -1, :]                  # [N, hidden]
        return {
            "event_probability": self.event_prob(x_final),
            "severity":          self.severity_head(x_final),
            "centroid_delta":    self.centroid_head(x_final),
        }
```

### 4.4 Ensemble Trajectory and Uncertainty Cone

**Do not average ensemble members.** Run all 50 members through the GNN independently:

```
Member 01 → trajectory_01 ──┐
Member 02 → trajectory_02   ├── Stack → compute:
Member 03 → trajectory_03   │   P50 (median trajectory)
...                          │   P75 polygon
Member 50 → trajectory_50 ──┘   P90 polygon (uncertainty cone)
```

Output GeoJSON:
```json
{
  "trajectories": [
    {"member": 1, "path": [[17.2, 84.1], [18.1, 83.5]]},
    "..."
  ],
  "cone_50pct": { "type": "Polygon", "coordinates": ["..."] },
  "cone_75pct": { "type": "Polygon", "coordinates": ["..."] },
  "cone_90pct": { "type": "Polygon", "coordinates": ["..."] },
  "consensus_centroid": {"lat": 17.82, "lon": 84.31}
}
```

Linking centroids across timesteps uses **Hungarian matching** to maintain consistent event identity when multiple anomalies are present simultaneously.

---

## 5. Stage 2 — Amplitude-Preserving Diffusion Downscaling

### 5.1 The Core Problem: MSE Kills Extremes

```
Actual rainfall field:   [ 10,  12,  15, 180 ]   ← 180 mm/hr extreme event
MSE-trained model:       [ 12,  14,  18,  70 ]   ← Extreme is smoothed to 70
Diffusion model samples: [ 11,  13,  16, 175 ]   ← Extreme is preserved
```

The diffusion model samples from p(y|x) rather than computing E[y|x], preserving the heavy tail of the distribution.

### 5.2 Conditioning Inputs

```
Coarse 12 km variables:          Static channels:
  u10, v10, t2m                    DEM elevation
  q850, mslp, tp                   Slope / aspect
  z500, EFI anomaly                Land/sea mask
        +                          Latitude grid
  Trajectory centroid              Longitude grid
  Severity score
```

### 5.3 Architecture: Conditional UNet + Diffusion

```
12 km forecast tensor
       │
       ▼
Condition Encoder (CNN)
       │
       ├──────────────────┐
       ▼                  ▼
  Topography         Weather
  Encoder            Encoder
       │                  │
       └────────┬─────────┘
                ▼
    Conditional UNet Backbone
    (with cross-attention on
     lead-time + severity embed)
                │
       diffusion timestep t
                │
                ▼
      Score function s_θ(x_t, t, c)
                │
                ▼ (reverse diffusion)
         5 km output tensor
```

Use **NVIDIA CorrDiff** or **Hugging Face Diffusers EDM** as the backbone. Do not write a diffusion model from scratch.

### 5.4 Generating Multiple Futures (Critical)

```python
# At inference: generate 20 independent samples
samples = []
for _ in range(20):
    sample = diffusion_pipeline.sample(
        condition=coarse_12km_tensor,
        num_inference_steps=50,
        guidance_scale=3.5,
    )
    samples.append(sample)

sample_stack = torch.stack(samples)  # [20, C, H, W]
output = {
    "mean":        sample_stack.mean(0),
    "median":      sample_stack.median(0).values,
    "p90":         sample_stack.quantile(0.90, dim=0),
    "p95":         sample_stack.quantile(0.95, dim=0),
    "uncertainty": sample_stack.std(0),
}
```

---

## 6. Physics-Informed Loss Engine

### 6.1 Composite Loss Function

L_total = L_diffusion + λ1·L_extreme + λ2·L_divergence + λ3·L_moisture + λ4·L_gradient

### 6.2 Extreme Value Preservation Loss

Give higher weight to tail events above the 95th percentile:

```python
weight = 1.0 + alpha * (target > p95_threshold).float()   # alpha=5.0 typical
L_extreme = (weight * (pred - target).pow(2)).mean()
```

### 6.3 Physics Constraint Losses

```python
# vajra/downscaling/physics_loss.py
import torch
import torch.nn as nn

class AtmosphericPhysicsLoss(nn.Module):
    """
    Penalizes physically impossible weather states.
    Channels:  0=u, 1=v, 2=q, 3=precip
    """
    def __init__(self, dx=5000.0, dy=5000.0, lam_div=0.1, lam_moist=0.2):
        super().__init__()
        self.dx, self.dy = dx, dy
        self.lam_div, self.lam_moist = lam_div, lam_moist

    def forward(self, pred, target):
        u, v, q, p = pred[:,0:1], pred[:,1:2], pred[:,2:3], pred[:,3:4]

        # Reconstruction
        mse = nn.functional.mse_loss(pred, target)

        # 1. Horizontal divergence: du/dx + dv/dy ≈ 0 (incompressible approx)
        du_dx = (u[:,:,:,2:] - u[:,:,:,:-2]) / (2*self.dx)
        dv_dy = (v[:,:,2:,:] - v[:,:,:-2,:]) / (2*self.dy)
        div = du_dx[:,:,1:-1,:] + dv_dy[:,:,:,1:-1]
        L_div = torch.mean(torch.abs(div))

        # 2. Moisture flux convergence must support precipitation
        fx, fy = q * u, q * v
        dfc_x = (fx[:,:,:,2:] - fx[:,:,:,:-2]) / (2*self.dx)
        dfc_y = (fy[:,:,2:,:] - fy[:,:,:-2,:]) / (2*self.dy)
        moisture_conv = -(dfc_x[:,:,1:-1,:] + dfc_y[:,:,:,1:-1])
        p_int = p[:,:,1:-1,1:-1]
        L_moist = torch.mean(torch.relu(-moisture_conv * p_int))

        total = mse + self.lam_div * L_div + self.lam_moist * L_moist
        return total, {
            "mse": mse.item(),
            "divergence": L_div.item(),
            "moisture": L_moist.item()
        }
```

---

## 7. Impact / Risk Engine

Translate meteorological output into human-readable risk categories with **configurable thresholds** stored in YAML (not hardcoded):

```yaml
# configs/impact_thresholds.yaml
cyclone:
  wind_kmh:
    low:          [63, 89]
    moderate:     [89, 118]
    severe:       [118, 167]
    catastrophic: [167, 9999]
  rainfall_mm_12hr:
    low:    [64.5, 115.5]
    heavy:  [115.5, 204.4]
    extreme:[204.4, 9999]

heatwave:
  t2m_celsius:
    watch:     [40, 44]
    warning:   [44, 47]
    emergency: [47, 9999]
```

Output from the risk engine:
```json
{
  "event": "cyclone",
  "severity": "SEVERE",
  "probability": 0.82,
  "center": {"lat": 19.07, "lon": 72.87},
  "impact_radius_km": 5,
  "peak_rainfall_mm_12hr": 186,
  "peak_wind_kmh": 112,
  "forecast_window_hr": 12,
  "action": "Evacuate coastal zone within 5 km radius immediately"
}
```

---

## 8. FastAPI Backend

### 8.1 Endpoints

```
POST  /forecast                → Trigger full pipeline on a new GRIB run
POST  /events/detect           → Run GNN on uploaded tensor
GET   /events                  → List all detected events
GET   /events/{id}             → Full event metadata
GET   /events/{id}/trajectory  → 4D centroid path + uncertainty cone GeoJSON
GET   /events/{id}/impact      → 5 km impact polygon + risk level
GET   /events/{id}/forecast    → 20-sample diffusion output (mean, p90, std)
```

### 8.2 Impact Zone Generation (Geodesic 5 km Buffer)

```python
# vajra/api/geo.py
import pyproj
from shapely.geometry import Point, mapping
from shapely.ops import transform

def generate_impact_zone(lat: float, lon: float, radius_m: float = 5000.0) -> dict:
    """Returns a geodesic circular impact buffer as GeoJSON."""
    crs_wgs84 = pyproj.CRS("EPSG:4326")
    crs_aeqd  = pyproj.CRS(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +units=m")

    to_m   = pyproj.Transformer.from_crs(crs_wgs84, crs_aeqd, always_xy=True).transform
    to_deg = pyproj.Transformer.from_crs(crs_aeqd, crs_wgs84, always_xy=True).transform

    pt_m   = transform(to_m, Point(lon, lat))
    circle = transform(to_deg, pt_m.buffer(radius_m))
    return mapping(circle)
```

---

## 9. React + MapLibre Dashboard

### 9.1 UI Layout

```
┌────────────────────────────────────────────────────────┐
│  VAJRA — EXTREME WEATHER TRACKING SYSTEM        🛰 LIVE │
├──────────────────────────┬─────────────────────────────┤
│                          │  EVENT PANEL                 │
│     MapLibre GL Map      │  🌀 Cyclone BOB-01           │
│                          │  Severity: SEVERE            │
│   ╱──────────────╲       │  Probability: 82%            │
│  ╱   90% cone     ╲      │  Peak rain: 186 mm/12hr      │
│ ╱  75% cone        ╲     │  Wind: 112 km/h              │
│╱  ● centroid 82%    ╲    │  Impact radius: 5 km         │
│╲  5km impact zone   ╱    ├─────────────────────────────┤
│ ╲──────────────────╱     │  LAYERS                      │
│                          │  ☑ EFI Anomaly               │
│         India            │  ☑ GNN Event Region          │
│                          │  ☑ Ensemble Tracks           │
│                          │  ☑ Uncertainty Cone          │
│                          │  ☑ 5 km Rainfall             │
│                          │  ☑ 5 km Wind                 │
│                          │  ☑ Risk Zones                │
│                          │  ☐ Population Density        │
│                          │  ☐ Agricultural Areas        │
├──────────────────────────┴─────────────────────────────┤
│ ◀ ───────────●──────────────────────────── ▶           │
│  T+0        T+48h                        T+240h         │
│  Lead-time scrubber (3–10 day window)                   │
└────────────────────────────────────────────────────────┘
```

### 9.2 Key Frontend Components

| Component | Technology | Purpose |
|---|---|---|
| `MapView.jsx` | MapLibre GL JS | Raster tiles, GeoJSON overlays |
| `WindLayer.jsx` | deck.gl `IconLayer` | Animated wind particles |
| `RainfallGrid.jsx` | deck.gl `BitmapLayer` | 5 km precipitation raster |
| `TimeSlider.jsx` | Custom React | T+72h → T+240h scrubber |
| `EnsembleCone.jsx` | MapLibre `FillLayer` | P50/P75/P90 polygons |
| `AlertPanel.jsx` | React | Event metadata + impact list |
| `ThresholdControls.jsx` | React | Configurable risk thresholds |

---

## 10. Project Directory Structure

```
Vajra/
├── .github/
│   └── workflows/
│       ├── test.yml            # Pytest + physics loss validation
│       └── lint.yml            # ruff + mypy
│
├── configs/
│   ├── gnn.yaml                # Mesh level, hidden dims, attention heads
│   ├── diffusion.yaml          # Timesteps, beta schedule, guidance scale
│   └── impact_thresholds.yaml  # Configurable severity thresholds
│
├── data/                       # (git-ignored, managed separately)
│   ├── raw/
│   ├── processed/
│   └── terrain/
│
├── vajra/
│   ├── __init__.py
│   │
│   ├── ingestion/
│   │   ├── nwp_loader.py       # Xarray + cfgrib + Dask ingestion
│   │   ├── zarr_writer.py      # Convert GRIB chunks to Zarr
│   │   └── climatology.py      # 30-year ERA5 percentiles + EFI
│   │
│   ├── tracking/               # Stage 1 — Spherical GNN
│   │   ├── mesh.py             # Icosahedral mesh generator
│   │   ├── gnn_model.py        # GATv2 + GRU temporal model
│   │   ├── efi_calculator.py   # EFI + Z-score anomaly fields
│   │   └── anomaly_tracker.py  # Hungarian matching + trajectory
│   │
│   ├── downscaling/            # Stage 2 — Diffusion model
│   │   ├── unet_backbone.py    # Conditional UNet implementation
│   │   ├── diffusion_pipeline.py  # HF Diffusers / CorrDiff wrapper
│   │   ├── physics_loss.py     # Divergence + moisture constraints
│   │   └── sampler.py          # 20-sample probabilistic ensemble
│   │
│   ├── impact/
│   │   ├── risk_engine.py      # Weather → flood/wind/heat risk
│   │   └── impact_zone.py      # Geodesic 5 km impact buffer
│   │
│   ├── api/
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── geo.py              # GeoJSON utilities
│   │   └── celery_tasks.py     # Async inference task queue
│   │
│   └── utils/
│       ├── metrics.py          # CRPS, SEDI, Peak Amplitude Retention
│       └── geo_utils.py        # Coordinate transforms, Shapely helpers
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.jsx
│   │   │   ├── WindLayer.jsx
│   │   │   ├── RainfallGrid.jsx
│   │   │   ├── EnsembleCone.jsx
│   │   │   ├── TimeSlider.jsx
│   │   │   ├── AlertPanel.jsx
│   │   │   └── ThresholdControls.jsx
│   │   ├── App.tsx
│   │   └── api.ts              # FastAPI client
│   └── package.json
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_climatology_validation.ipynb
│   ├── 03_gnn_training.ipynb
│   └── 04_diffusion_training.ipynb
│
├── tests/
│   ├── test_mesh.py
│   ├── test_physics_loss.py
│   ├── test_impact_zone.py
│   └── test_api.py
│
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 11. Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11 | Ecosystem compatibility |
| Deep Learning | PyTorch 2.x | Standard, stable |
| GNN | DGL (primary) / PyTorch Geometric | PS-specified; DGL preferred |
| Diffusion | Hugging Face Diffusers + CorrDiff | PS-specified; CorrDiff is SOTA for weather |
| Meteorological ops | MetPy + Pint | Dimensioned computations |
| Multidim. data | Xarray + Dask | PS-specified |
| On-disk format | Zarr (not NetCDF) | Much faster chunked I/O vs NetCDF |
| GRIB2 reading | cfgrib + ecCodes | Industry standard |
| Geospatial | GeoPandas + Shapely + pyproj + Cartopy | GeoJSON, projections, buffers |
| Backend API | FastAPI + Pydantic v2 | Async, fast, typed |
| Task queue | Celery + Redis | Async inference jobs |
| Frontend | React 18 + TypeScript | Component isolation |
| Maps | MapLibre GL JS + deck.gl | GPU-accelerated, open-source |
| Experiment tracking | Weights & Biases | Better UI than MLflow for teams |
| Containerization | Docker + docker-compose | Reproducibility |
| GPU inference | CUDA 12 | NVIDIA GPU requirement |

---

## 12. Evaluation Metrics

| Metric | What it measures |
|---|---|
| **CRPS** (Continuous Ranked Probability Score) | Overall probabilistic forecast quality |
| **SEDI** (Symmetric Extremal Dependence Index) | Rare/extreme event detection skill |
| **Peak Amplitude Retention Error (PARE)** | How well the model preserves the top-1% intensity values |
| **Centroid Distance Error (km)** | Spatial accuracy of cyclone/event center tracking |
| **Trajectory RMSE (km)** | Path accuracy over 72h–240h lead times |
| **Physics Residual** | Mean divergence / moisture flux violation after generation |

---

## 13. Phased Execution Plan

### Phase 0 — Dataset Validation (Week 1, Days 1–3)
> **This is the real first milestone. Do not skip it.**

- [ ] Obtain sample NEPS-G / NCUM GRIB2 files for Cyclone Amphan (May 2020)
- [ ] Verify cfgrib can open all variables correctly
- [ ] Write to Zarr, confirm chunk shapes and memory behavior
- [ ] Download ERA5 subset for Bay of Bengal region (1991–2020)
- [ ] Build climatology.zarr and manually inspect EFI values against known Amphan track

### Phase 1 — Baseline Anomaly Tracker (Week 1, Days 4–7)

Build a **non-AI baseline** first. This gives you something to beat and a working demo skeleton.

```
ERA5 → EFI → Connected Component Labeling → Centroid → Map
```

- [ ] Implement `efi_calculator.py`
- [ ] Implement scipy `ndimage.label` based anomaly extractor
- [ ] Plot trajectory on Cartopy map
- [ ] This becomes the comparison baseline in your demo

### Phase 2 — Spherical GNN (Week 2)

- [ ] Build icosahedral mesh at level 5
- [ ] Interpolate 12 km NWP grids onto mesh vertices (use `scipy.interpolate.griddata`)
- [ ] Implement `WeatherGNN` with GATv2 + GRU
- [ ] Train on historical events (Amphan + 2 North India heatwaves)
- [ ] Compare GNN trajectory vs. baseline connected-component trajectory

### Phase 3 — Ensemble Uncertainty (Week 2–3)

- [ ] Run all 50 NEPS-G members through the trained GNN
- [ ] Stack trajectories → compute P50/P75/P90 polygons using Shapely
- [ ] Render uncertainty cone on MapLibre

### Phase 4 — Diffusion Downscaling (Week 3)

- [ ] Build training pairs: (12 km NCUM input, 5 km IMDAA/ERA5-Land target)
- [ ] Fine-tune CorrDiff or train conditional UNet
- [ ] Add `AtmosphericPhysicsLoss` — divergence + moisture constraints
- [ ] Add extreme value weighting (`L_extreme`)
- [ ] Generate 20-sample ensembles and compare mean/p90 to ground truth

### Phase 5 — API + Dashboard (Week 4)

- [ ] Build FastAPI with all 7 endpoints
- [ ] Integrate Celery for async inference
- [ ] Build React + MapLibre frontend
- [ ] Add layer toggles, time scrubber, alert panel
- [ ] Connect GeoJSON from API to map layers

### Phase 6 — Demo Polish (Week 4, final 2 days)

- [ ] Record demo using Cyclone Amphan historical replay
- [ ] Show: raw 12 km ensemble → GNN detection → 5 km downscaled → 5 km impact zone
- [ ] Show live uncertainty cone animation as lead time changes

---

## 14. Target Demo Sequence

```
1. Show raw 12 km NEPS-G fields for T−72h before Amphan landfall
              ↓
2. Hit "RUN AI TRACKING"
   → Spherical GNN processes 50 ensemble members
   → Trajectory + uncertainty cone appears on map
              ↓
3. Hit "GENERATE 5 KM IMPACT FIELD"
   → Visual transition: coarse 12 km → high-res 5 km
   → Extreme rainfall peaks retained (186 mm/12hr visible)
              ↓
4. Show alert box:
   ┌─────────────────────────────────┐
   │  ⚠ EXTREME WEATHER ALERT        │
   │  Cyclone — SEVERE               │
   │  Probability: 84%               │
   │  Peak rainfall: 186 mm / 12hr   │
   │  Impact radius: 5 km            │
   │  ● High-risk zone: Digha, WB    │
   └─────────────────────────────────┘
              ↓
5. Toggle layers: EFI → GNN polygon → Ensemble cone → 5km rain → Risk zones
```

---

## 15. Key Design Decisions

| Decision | Why |
|---|---|
| Start with cyclones over Bay of Bengal only | Fastest path to a working demo; generalize later |
| Zarr instead of NetCDF for processed data | 10–30× faster chunked parallel I/O with Dask |
| DGL over PyG for GNN | PS explicitly names DGL; judges will notice alignment |
| CorrDiff over plain DDPM | NVIDIA's CorrDiff is purpose-built for weather downscaling; SOTA results |
| 20-sample probabilistic output | Diffusion's main advantage over deterministic models; must demonstrate this |
| Configurable thresholds via YAML | Scientifically defensible; avoids hardcoding arbitrary numbers |
| Phase 0 dataset validation first | Inaccessible or malformed NWP data is the #1 project killer |
| Weights & Biases over MLflow | Better multi-user experiment visualization for team coordination |

---

*Built for Smart India Hackathon / MoES NCMRWF · Problem Statement 26078*
