import pytest
import numpy as np
from vajra.utils.geo_utils import (
    latlon_to_cartesian,
    cartesian_to_latlon,
    great_circle_distance_km,
    create_geodesic_buffer,
    polygon_area_km2,
    to_feature_collection
)

def test_spherical_coordinate_roundtrip():
    lat, lon = 19.82, 86.85
    xyz = latlon_to_cartesian(lat, lon)
    assert np.isclose(np.linalg.norm(xyz), 1.0, atol=1e-5)

    rec_lat, rec_lon = cartesian_to_latlon(xyz)
    assert np.isclose(rec_lat, lat, atol=1e-4)
    assert np.isclose(rec_lon, lon, atol=1e-4)

def test_great_circle_distance():
    # Distance between Mumbai (19.076, 72.877) and Pune (18.520, 73.856) is ~120 km
    dist = great_circle_distance_km(19.076, 72.877, 18.520, 73.856)
    assert 110.0 < dist < 140.0

def test_geodesic_buffer_area():
    # 5 km radius circle -> Area should be ~ pi * r^2 = 3.14159 * 25 = ~78.5 km^2
    poly = create_geodesic_buffer(20.0, 85.0, radius_m=5000.0)
    area = polygon_area_km2(poly)
    assert 70.0 < area < 85.0

def test_to_feature_collection():
    fc = to_feature_collection([{"type": "Feature", "geometry": None, "properties": {}}])
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1
