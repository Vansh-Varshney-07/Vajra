from vajra.impact.impact_zone import ImpactZoneGenerator
from shapely.geometry import shape

def test_geodesic_5km_impact_buffer():
    lat = 19.82
    lon = 86.85
    radius_m = 5000.0

    geojson = ImpactZoneGenerator.generate_impact_buffer(
        centroid_lat=lat,
        centroid_lon=lon,
        radius_meters=radius_m,
        properties={"threat": "CYCLONE"}
    )

    assert geojson["type"] == "Feature"
    assert geojson["geometry"]["type"] == "Polygon"
    assert geojson["properties"]["impact_radius_km"] == 5.0
    assert geojson["properties"]["threat"] == "CYCLONE"

    # Verify polygon is valid and non-empty
    poly = shape(geojson["geometry"])
    assert poly.is_valid
    assert poly.area > 0.0
