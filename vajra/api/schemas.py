"""
Pydantic v2 request/response schemas for the Vajra API.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CentroidCoordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class TrajectoryWaypoint(BaseModel):
    lead_time_hr: int
    lat: float
    lon: float
    intensity: float


class AnomalyEvent(BaseModel):
    event_id: str
    event_type: str
    name: str
    probability: float
    threat_level: str
    color_code: str
    current_centroid: CentroidCoordinates
    peak_wind_kmh: float
    peak_rainfall_mm_12hr: float
    lead_time_hr: int
    action_recommended: str
    trajectory: Optional[List[TrajectoryWaypoint]] = []


class DetectAnomalyRequest(BaseModel):
    variable: str = "tp"
    threshold_percentile: float = 95.0
    ensemble_members: int = 50
    lead_times_hr: List[int] = [24, 48, 72, 96, 120]


class ForecastDownscaleRequest(BaseModel):
    event_id: str = "BOB-CYC-2026-001"
    target_lead_time_hr: int = 72
    num_samples: int = 20


class ImpactZoneResponse(BaseModel):
    event_id: str
    impact_zone_geojson: Dict[str, Any]
    action_advisory: str


class EFIFieldRequest(BaseModel):
    variable: str = "tp"
    lead_time_hr: int = 72
    ensemble_members: int = 50


class EFIFieldResponse(BaseModel):
    variable: str
    lead_time_hr: int
    efi_mean: float
    efi_max: float
    z_score_mean: float
    percentile_rank: float
    interpretation: str
