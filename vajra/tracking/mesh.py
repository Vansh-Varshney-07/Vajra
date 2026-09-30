import numpy as np
import torch
from scipy.spatial import ConvexHull
from scipy.interpolate import NearestNDInterpolator
from torch_geometric.data import Data
from typing import Tuple, Dict

class SphericalMeshBuilder:
    """
    Constructs multi-resolution icosahedral geodesic meshes on the sphere.
    Maps planar NWP coordinates to uniform spherical mesh representations.
    """

    @staticmethod
    def latlon_to_cartesian(lat_deg: np.ndarray, lon_deg: np.ndarray, radius: float = 1.0) -> np.ndarray:
        """Converts latitude and longitude (degrees) to 3D Cartesian points on a sphere."""
        lat_rad = np.radians(lat_deg)
        lon_rad = np.radians(lon_deg)
        x = radius * np.cos(lat_rad) * np.cos(lon_rad)
        y = radius * np.cos(lat_rad) * np.sin(lon_rad)
        z = radius * np.sin(lat_rad)
        return np.column_stack([x, y, z])

    @staticmethod
    def cartesian_to_latlon(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Converts 3D Cartesian points to latitude and longitude (degrees)."""
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        r = np.linalg.norm(points, axis=1)
        lat_rad = np.arcsin(np.clip(z / r, -1.0, 1.0))
        lon_rad = np.arctan2(y, x)
        return np.degrees(lat_rad), np.degrees(lon_rad)

    @classmethod
    def generate_icosahedron(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Generates 12 vertices and 20 triangular faces of a regular icosahedron."""
        phi = (1.0 + np.sqrt(5.0)) / 2.0
        vertices = np.array([
            [-1,  phi,  0], [ 1,  phi,  0], [-1, -phi,  0], [ 1, -phi,  0],
            [ 0, -1,  phi], [ 0,  1,  phi], [ 0, -1, -phi], [ 0,  1, -phi],
            [ phi,  0, -1], [ phi,  0,  1], [-phi,  0, -1], [-phi,  0,  1]
        ], dtype=np.float32)
        vertices /= np.linalg.norm(vertices, axis=1, keepdims=True)
        hull = ConvexHull(vertices)
        return vertices, hull.simplices

    @classmethod
    def subdivide_mesh(cls, vertices: np.ndarray, faces: np.ndarray, level: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Recursively subdivides spherical triangular faces.
        Level 4: 2,562 vertices (≈200 km spacing)
        Level 5: 10,242 vertices (≈50 km spacing)
        """
        v_list = list(vertices)
        f_list = list(faces)

        for _ in range(level):
            midpoint_cache: Dict[Tuple[int, int], int] = {}
            new_faces = []

            def get_midpoint(i1: int, i2: int) -> int:
                edge = tuple(sorted((i1, i2)))
                if edge in midpoint_cache:
                    return midpoint_cache[edge]
                mid = (v_list[i1] + v_list[i2]) / 2.0
                mid /= np.linalg.norm(mid)
                v_list.append(mid)
                new_idx = len(v_list) - 1
                midpoint_cache[edge] = new_idx
                return new_idx

            for tri in f_list:
                v1, v2, v3 = tri[0], tri[1], tri[2]
                a = get_midpoint(v1, v2)
                b = get_midpoint(v2, v3)
                c = get_midpoint(v3, v1)
                new_faces.extend([
                    [v1, a, c],
                    [v2, b, a],
                    [v3, c, b],
                    [a, b, c]
                ])
            f_list = new_faces

        return np.array(v_list, dtype=np.float32), np.array(f_list, dtype=np.int64)

    @classmethod
    def build_graph(cls, level: int = 4) -> Data:
        """
        Builds a PyTorch Geometric Graph containing node coordinates,
        undirected neighbor edges, and 3D relative displacement edge attributes.
        """
        v, f = cls.generate_icosahedron()
        vertices, faces = cls.subdivide_mesh(v, f, level=level)

        edges = set()
        for tri in faces:
            for i1, i2 in [(tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])]:
                edges.add((i1, i2))
                edges.add((i2, i1))

        edge_list = list(edges)
        src = [e[0] for e in edge_list]
        dst = [e[1] for e in edge_list]
        edge_index = torch.tensor([src, dst], dtype=torch.long)

        pos = torch.tensor(vertices, dtype=torch.float32)
        # Compute relative displacement vectors: pos_dst - pos_src
        pos_src = pos[edge_index[0]]
        pos_dst = pos[edge_index[1]]
        edge_attr = pos_dst - pos_src

        graph = Data(pos=pos, edge_index=edge_index, edge_attr=edge_attr)
        return graph

    @classmethod
    def interpolate_grid_to_mesh(
        cls,
        grid_lats: np.ndarray,
        grid_lons: np.ndarray,
        grid_data: np.ndarray,
        mesh_pos: np.ndarray
    ) -> np.ndarray:
        """
        Projects planar (lat, lon) atmospheric variables onto the spherical icosahedral mesh.
        grid_data: [Variables, Height, Width]
        Returns: [Num_Mesh_Nodes, Variables]
        """
        mesh_lats, mesh_lons = cls.cartesian_to_latlon(mesh_pos)
        lon_grid, lat_grid = np.meshgrid(grid_lons, grid_lats)

        flat_pts = np.column_stack([lat_grid.flatten(), lon_grid.flatten()])
        query_pts = np.column_stack([mesh_lats, mesh_lons])

        num_vars = grid_data.shape[0]
        mesh_features = np.zeros((len(mesh_pos), num_vars), dtype=np.float32)

        for v_idx in range(num_vars):
            values = grid_data[v_idx].flatten()
            interp = NearestNDInterpolator(flat_pts, values)
            mesh_features[:, v_idx] = interp(query_pts)

        return mesh_features
