from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class CentroidCoordinates(BaseModel):
    lat: float = Field(..., description="Latitude in decimal degrees", ge=-90.0, le=90.0)
    lon: float = Field(..., description="Longitude in decimal degrees", ge=-180.0, le=180.0)

class TrajectoryPoint(BaseModel):
    lead_time_hr: int = Field(..., description="Forecast lead time in hours (e.g. 72, 78, 120)")
    lat: float
    lon: float
    intensity: float

class AnomalyEvent(BaseModel):
    event_id: str = Field(..., json_schema_extra={"example": "BOB-CYC-2026-001"})
    event_type: str = Field(..., json_schema_extra={"example": "CYCLONE"}) # CYCLONE, HEATWAVE, COLDWAVE, HEAVY_RAINFALL
    probability: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.84})
    threat_level: str = Field(..., json_schema_extra={"example": "SEVERE"}) # LOW, MODERATE, SEVERE, CATASTROPHIC
    color_code: str = Field(..., json_schema_extra={"example": "RED"})
    current_centroid: CentroidCoordinates
    peak_wind_kmh: Optional[float] = 112.0
    peak_rainfall_mm_12hr: Optional[float] = 186.0
    lead_time_hr: int = 72
    action_recommended: str = Field(..., json_schema_extra={"example": "Evacuate coastal zone within 5 km radius immediately"})

class DetectAnomalyRequest(BaseModel):
    lead_time_hours: List[int] = Field(default=[72, 78, 84, 90, 96, 102, 108, 114, 120])
    ensemble_member_count: int = Field(default=10, ge=1, le=50)
    region: str = Field(default="Bay of Bengal / East Coast India")

class ForecastDownscaleRequest(BaseModel):
    event_id: str
    target_lead_time_hr: int = 72
    num_samples: int = Field(default=20, ge=1, le=50)
    guidance_scale: float = Field(default=3.5, ge=1.0, le=10.0)

class ImpactZoneResponse(BaseModel):
    event_id: str
    impact_zone_geojson: Dict[str, Any]
    action_advisory: str
