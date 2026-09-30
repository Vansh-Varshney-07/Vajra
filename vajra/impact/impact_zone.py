import pyproj
from shapely.geometry import Point, mapping
from shapely.ops import transform
from typing import Dict, Any

class ImpactZoneGenerator:
    """
    Generates high-precision geodesic circular buffers around threat centroids.
    Guarantees consistent 5 km spatial coverage across any latitude without distortion.
    """

    @staticmethod
    def generate_impact_buffer(
        centroid_lat: float,
        centroid_lon: float,
        radius_meters: float = 5000.0,
        properties: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Creates an Azimuthal Equidistant geodesic buffer around (lat, lon)
        and outputs a GeoJSON Feature with attached meteorological properties.
        """
        proj_wgs84 = pyproj.CRS("EPSG:4326")
        # Custom local metric projection centered exactly on anomaly centroid
        proj_aeqd = pyproj.CRS(f"+proj=aeqd +lat_0={centroid_lat} +lon_0={centroid_lon} +units=m")

        transformer_to_metric = pyproj.Transformer.from_crs(proj_wgs84, proj_aeqd, always_xy=True).transform
        transformer_to_wgs84 = pyproj.Transformer.from_crs(proj_aeqd, proj_wgs84, always_xy=True).transform

        center_point_deg = Point(centroid_lon, centroid_lat)
        center_point_m = transform(transformer_to_metric, center_point_deg)

        # Buffer metric circle (e.g. 5,000 meters)
        buffered_circle_m = center_point_m.buffer(radius_meters)
        buffered_polygon_wgs84 = transform(transformer_to_wgs84, buffered_circle_m)

        feature_properties = properties or {}
        feature_properties.update({
            "centroid": [centroid_lon, centroid_lat],
            "impact_radius_km": radius_meters / 1000.0,
            "crs": "EPSG:4326"
        })

        geojson_feature = {
            "type": "Feature",
            "geometry": mapping(buffered_polygon_wgs84),
            "properties": feature_properties
        }

        return geojson_feature
