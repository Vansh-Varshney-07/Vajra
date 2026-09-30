import numpy as np
from typing import List, Dict, Any, Tuple
from scipy.ndimage import label
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, MultiPoint, Polygon, mapping
from shapely.ops import unary_union

class SpatioTemporalTracker:
    """
    Tracks evolving atmospheric anomalies across forecast lead-times (T+0 to T+240h).
    Calculates trajectories, bounding polygons, and multi-member ensemble uncertainty cones.
    """

    def __init__(
        self,
        prob_threshold: float = 0.70,
        min_area_pixels: int = 5,
        max_hop_distance_deg: float = 4.0
    ):
        self.prob_threshold = prob_threshold
        self.min_area_pixels = min_area_pixels
        self.max_hop_distance_deg = max_hop_distance_deg

    def detect_spatial_clusters(
        self,
        prob_map: np.ndarray,
        lats: np.ndarray,
        lons: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Isolates contiguous regions exceeding anomaly threshold.
        Returns centroid (lat, lon), bounding box, and peak value.
        """
        binary_mask = prob_map >= self.prob_threshold
        labeled_array, num_features = label(binary_mask)
        clusters = []

        for region_id in range(1, num_features + 1):
            coords = np.argwhere(labeled_array == region_id)
            if len(coords) < self.min_area_pixels:
                continue

            r_idx = coords[:, 0]
            c_idx = coords[:, 1]

            region_lats = lats[r_idx]
            region_lons = lons[c_idx]

            centroid_lat = float(np.mean(region_lats))
            centroid_lon = float(np.mean(region_lons))
            peak_val = float(np.max(prob_map[r_idx, c_idx]))

            # GeoJSON Bounding Box [min_lon, min_lat, max_lon, max_lat]
            bbox = [
                float(np.min(region_lons)),
                float(np.min(region_lats)),
                float(np.max(region_lons)),
                float(np.max(region_lats))
            ]

            # Approximate footprint polygon from convex hull of cluster points
            points = [Point(lon, lat) for lat, lon in zip(region_lats, region_lons)]
            hull = MultiPoint(points).convex_hull
            footprint_geojson = mapping(hull) if hull.geom_type in ["Polygon", "MultiPolygon"] else None

            clusters.append({
                "region_id": int(region_id),
                "centroid": {"lat": centroid_lat, "lon": centroid_lon},
                "bbox": bbox,
                "peak_intensity": peak_val,
                "pixel_count": int(len(coords)),
                "footprint": footprint_geojson
            })

        return clusters

    def link_temporal_trajectory(
        self,
        temporal_clusters: List[List[Dict[str, Any]]],
        lead_time_hours: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Links detected spatial clusters across consecutive lead-times using the Hungarian algorithm.
        Outputs complete 4D trajectories with timestamps.
        """
        if not temporal_clusters:
            return []

        active_tracks: List[Dict[str, Any]] = []

        for t_idx, (clusters, lead_time) in enumerate(zip(temporal_clusters, lead_time_hours)):
            if t_idx == 0 or len(active_tracks) == 0:
                for c in clusters:
                    active_tracks.append({
                        "track_id": f"track_{len(active_tracks)+1}",
                        "points": [{
                            "lead_time_hr": lead_time,
                            "lat": c["centroid"]["lat"],
                            "lon": c["centroid"]["lon"],
                            "intensity": c["peak_intensity"]
                        }],
                        "last_centroid": (c["centroid"]["lat"], c["centroid"]["lon"]),
                        "status": "ACTIVE"
                    })
                continue

            # Cost matrix based on Euclidean distance in lat/lon
            cost_matrix = np.full((len(active_tracks), len(clusters)), fill_value=1e5)
            for i, track in enumerate(active_tracks):
                if track["status"] != "ACTIVE":
                    continue
                last_lat, last_lon = track["last_centroid"]
                for j, cluster in enumerate(clusters):
                    curr_lat = cluster["centroid"]["lat"]
                    curr_lon = cluster["centroid"]["lon"]
                    dist = np.hypot(curr_lat - last_lat, curr_lon - last_lon)
                    if dist <= self.max_hop_distance_deg:
                        cost_matrix[i, j] = dist

            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            assigned_clusters = set()

            for r, c in zip(row_ind, col_ind):
                if cost_matrix[r, c] < 1e4: # Valid match
                    cluster = clusters[c]
                    active_tracks[r]["points"].append({
                        "lead_time_hr": lead_time,
                        "lat": cluster["centroid"]["lat"],
                        "lon": cluster["centroid"]["lon"],
                        "intensity": cluster["peak_intensity"]
                    })
                    active_tracks[r]["last_centroid"] = (cluster["centroid"]["lat"], cluster["centroid"]["lon"])
                    assigned_clusters.add(c)

            # Mark unmatched tracks as finished
            for i, track in enumerate(active_tracks):
                if i not in row_ind or cost_matrix[i, col_ind[list(row_ind).index(i)]] >= 1e4:
                    track["status"] = "FINISHED"

            # Spawn new tracks for unassigned clusters
            for j, cluster in enumerate(clusters):
                if j not in assigned_clusters:
                    active_tracks.append({
                        "track_id": f"track_{len(active_tracks)+1}",
                        "points": [{
                            "lead_time_hr": lead_time,
                            "lat": cluster["centroid"]["lat"],
                            "lon": cluster["centroid"]["lon"],
                            "intensity": cluster["peak_intensity"]
                        }],
                        "last_centroid": (cluster["centroid"]["lat"], cluster["centroid"]["lon"]),
                        "status": "ACTIVE"
                    })

        return active_tracks

    def compute_ensemble_uncertainty_cone(
        self,
        member_trajectories: List[List[Tuple[float, float]]]
    ) -> Dict[str, Any]:
        """
        Takes trajectories from all ensemble members (e.g. 50 members)
        and computes the consensus path along with 50%, 75%, and 90% uncertainty envelopes.
        """
        if not member_trajectories:
            return {}

        min_len = min(len(t) for t in member_trajectories)
        consensus_path = []
        envelope_points_50 = []
        envelope_points_90 = []

        for step in range(min_len):
            step_pts = np.array([traj[step] for traj in member_trajectories])
            mean_lat = float(np.mean(step_pts[:, 0]))
            mean_lon = float(np.mean(step_pts[:, 1]))
            consensus_path.append([mean_lon, mean_lat])

            # Calculate spread
            std_lat = float(np.std(step_pts[:, 0]))
            std_lon = float(np.std(step_pts[:, 1]))
            radius_50 = 0.674 * max(std_lat, std_lon, 0.2)
            radius_90 = 1.645 * max(std_lat, std_lon, 0.5)

            center = Point(mean_lon, mean_lat)
            envelope_points_50.append(center.buffer(radius_50))
            envelope_points_90.append(center.buffer(radius_90))

        cone_50 = mapping(unary_union(envelope_points_50).convex_hull)
        cone_90 = mapping(unary_union(envelope_points_90).convex_hull)

        return {
            "consensus_trajectory": consensus_path,
            "uncertainty_cone_50pct": cone_50,
            "uncertainty_cone_90pct": cone_90,
            "ensemble_members_count": len(member_trajectories)
        }
