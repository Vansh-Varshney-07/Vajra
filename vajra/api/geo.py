from typing import List, Dict, Any
from shapely.geometry import Point, LineString, Polygon, mapping

def points_to_geojson_linestring(points: List[List[float]], properties: Dict[str, Any] = None) -> Dict[str, Any]:
    """Converts a sequence of [lon, lat] points to a GeoJSON LineString feature."""
    line = LineString(points)
    return {
        "type": "Feature",
        "geometry": mapping(line),
        "properties": properties or {}
    }

def polygon_to_geojson_feature(polygon_coords: List[List[float]], properties: Dict[str, Any] = None) -> Dict[str, Any]:
    """Converts a list of boundary coordinates [[lon, lat], ...] to a GeoJSON Polygon feature."""
    poly = Polygon(polygon_coords)
    return {
        "type": "Feature",
        "geometry": mapping(poly),
        "properties": properties or {}
    }
