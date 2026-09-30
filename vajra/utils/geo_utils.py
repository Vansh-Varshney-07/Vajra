"""
Geospatial utility functions for coordinate transforms, projections,
spherical trigonometry, and Shapely GeoJSON geometries.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import pyproj
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, mapping, box
from shapely.ops import transform

EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_M = 6371000.0

def latlon_to_cartesian(lat_deg: Union[float, np.ndarray], lon_deg: Union[float, np.ndarray]) -> np.ndarray:
    """
    Converts spherical latitude and longitude (in degrees) to 3D Cartesian coordinates on unit sphere.
    """
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    x = np.cos(lat_rad) * np.cos(lon_rad)
    y = np.cos(lat_rad) * np.sin(lon_rad)
    z = np.sin(lat_rad)
    if isinstance(lat_deg, np.ndarray):
        return np.stack([x, y, z], axis=-1)
    return np.array([x, y, z], dtype=np.float32)

def cartesian_to_latlon(xyz: np.ndarray) -> Tuple[float, float]:
    """
    Converts a 3D unit sphere vector [x, y, z] back to (lat, lon) in degrees.
    """
    x, y, z = xyz[0], xyz[1], xyz[2]
    hypot_xy = math.sqrt(x * x + y * y)
    lat_rad = math.atan2(z, hypot_xy)
    lon_rad = math.atan2(y, x)
    return math.degrees(lat_rad), math.degrees(lon_rad)

def great_circle_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great circle distance between two points on Earth using Haversine formula.
    """
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c

def create_geodesic_buffer(lat: float, lon: float, radius_m: float = 5000.0) -> Polygon:
    """
    Generates an exact geodesic circular buffer around (lat, lon)
    using Azimuthal Equidistant projection (AEQD) centered at the point.
    """
    crs_wgs84 = pyproj.CRS("EPSG:4326")
    crs_aeqd = pyproj.CRS(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +units=m")

    proj_to_aeqd = pyproj.Transformer.from_crs(crs_wgs84, crs_aeqd, always_xy=True).transform
    proj_to_wgs84 = pyproj.Transformer.from_crs(crs_aeqd, crs_wgs84, always_xy=True).transform

    point_wgs = Point(lon, lat)
    point_aeqd = transform(proj_to_aeqd, point_wgs)
    circle_aeqd = point_aeqd.buffer(radius_m)
    circle_wgs = transform(proj_to_wgs84, circle_aeqd)
    return circle_wgs

def polygon_area_km2(geom: Union[Polygon, MultiPolygon]) -> float:
    """
    Estimates geodesic area of a polygon in square kilometers using equal-area projection.
    """
    if geom.is_empty:
        return 0.0
    centroid = geom.centroid
    crs_wgs84 = pyproj.CRS("EPSG:4326")
    crs_laea = pyproj.CRS(f"+proj=laea +lat_0={centroid.y} +lon_0={centroid.x} +units=m")
    transformer = pyproj.Transformer.from_crs(crs_wgs84, crs_laea, always_xy=True).transform
    projected = transform(transformer, geom)
    return float(projected.area / 1e6)

def to_feature_collection(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Wraps a list of GeoJSON Feature dictionaries into a valid FeatureCollection.
    """
    return {
        "type": "FeatureCollection",
        "features": features
    }

# ─── Aliases for Vajra utils package ──────────────────────────────────────────
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return great_circle_distance_km(lat1, lon1, lat2, lon2)

def geodesic_buffer_polygon(lat: float, lon: float, radius_m: float = 5000.0) -> Polygon:
    return create_geodesic_buffer(lat, lon, radius_m)

def bbox_from_centroid(lat: float, lon: float, radius_km: float = 50.0) -> Tuple[float, float, float, float]:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)

