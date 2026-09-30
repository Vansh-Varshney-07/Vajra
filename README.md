# Vajra 🌀
### AI-Driven Spatio-Temporal Tracking & Physics-Constrained Downscaling of Extreme Weather Anomalies
**Ministry of Earth Sciences (MoES) / NCMRWF · Problem Statement 26078**

---

## What Vajra Does

Vajra is an end-to-end AI pipeline that:

1. **Tracks** extreme weather anomalies (cyclones, heatwaves, cold waves) across a 3–10 day medium-range forecast window using a **Spherical Icosahedral GNN** — eliminating the latitude-longitude grid distortions that break standard CNNs.
2. **Downscales** coarse 12 km NWP ensemble data to high-fidelity **5 km impact fields** using a **Physics-Constrained Generative Diffusion Model** that preserves extreme amplitude peaks — not averages them away.
3. **Alerts** disaster management (NDRF / IMD) with **pinpoint geodesic 5 km impact buffers** and categorized severity advisories via a REST API.

---

## Quick Start

### 1. Python Backend (FastAPI)
```bash
# Activate the Python 3.14 virtual environment
.venv\Scripts\activate      # Windows

# Start FastAPI server
uvicorn vajra.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. React Dashboard (Vite Dev Server)
```bash
cd frontend
npm run dev    # Opens at http://localhost:3000
```

### 3. Run All Tests
```bash
.venv\Scripts\python.exe -m pytest -v
```

---

## Architecture Overview

```
NEPS-G / NCUM / ERA5 / IMDAA (GRIB2 / NetCDF)
                    │
              ┌─────▼─────┐
              │ Xarray+Dask│  →  Zarr Store
              └─────┬─────┘
                    │
          ┌─────────▼──────────┐
          │  Stage 1: Spherical │
          │  Icosahedral GNN    │  ← DGL / PyTorch Geometric
          │  (EFI + Tracking)   │  ← GATv2 + GRU temporal
          └─────────┬──────────┘
                    │  4D Trajectory + Uncertainty Cone
          ┌─────────▼──────────┐
          │  Stage 2: Diffusion │
          │  Downscaling        │  ← HF Diffusers / CorrDiff
          │  12 km → 5 km       │  ← Physics-guided loss
          └─────────┬──────────┘
                    │
          ┌─────────▼──────────┐
          │  FastAPI REST API   │  →  GeoJSON Alerts
          │  React + Leaflet    │  →  Interactive Map
          └────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Python | 3.14 (CPython) |
| GNN (Stage 1) | DGL / PyTorch Geometric · GATv2 + GRU |
| Diffusion (Stage 2) | HF Diffusers · Conditional UNet |
| NWP Data | Xarray · Dask · cfgrib · Zarr |
| Meteorological Physics | MetPy · Pint |
| Geospatial | Shapely · GeoPandas · pyproj |
| Backend API | FastAPI · Pydantic v2 · Uvicorn |
| Frontend | React 18 · TypeScript · Vite · Leaflet GL |
| Testing | Pytest (9 tests, all passing) |
| Experiment Tracking | Weights & Biases |

---

## Project Structure

```
Vajra/
├── configs/                  # GNN, Diffusion, Impact threshold configs (YAML)
├── vajra/
│   ├── ingestion/            # NWP loader (GRIB2/NetCDF → Zarr) + EFI Climatology
│   ├── tracking/             # Stage 1: Spherical Mesh + GNN + Trajectory Tracker
│   ├── downscaling/          # Stage 2: ConditionalUNet + Diffusion + Physics Loss
│   ├── impact/               # Risk Engine + Geodesic 5km Buffer Generator
│   └── api/                  # FastAPI microservice (7 endpoints + GeoJSON)
├── frontend/                 # React 18 + TypeScript + Vite + Leaflet dashboard
├── tests/                    # Pytest suite (Mesh · Physics Loss · Impact · API)
├── requirements.txt          # Python 3.14 dependencies (148 packages)
└── ARCHITECTURE.md           # Full system blueprint
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/events` | List all tracked events |
| `GET` | `/events/{id}` | Event metadata |
| `GET` | `/events/{id}/trajectory` | 4D path + 20-member uncertainty cones (GeoJSON) |
| `GET` | `/events/{id}/impact` | Geodesic 5 km impact buffer (GeoJSON) |
| `POST` | `/events/{id}/downscale` | Trigger 12km→5km diffusion downscaling |

---

## Test Results

```
============================= test session starts ============================
Python 3.14.4, pytest-9.1.1

tests/test_api.py::test_root_health                PASSED
tests/test_api.py::test_get_events                 PASSED
tests/test_api.py::test_get_trajectory             PASSED
tests/test_api.py::test_get_impact_zone            PASSED
tests/test_api.py::test_downscale_endpoint         PASSED
tests/test_impact_zone.py::test_geodesic_5km_impact_buffer  PASSED
tests/test_mesh.py::test_mesh_generation_and_subdivision    PASSED
tests/test_mesh.py::test_graph_construction                 PASSED
tests/test_physics_loss.py::test_physics_loss_computation   PASSED

========================== 9 passed in 26.40s ================================
```

---

*Built for Smart India Hackathon · MoES NCMRWF · Problem Statement 26078*
