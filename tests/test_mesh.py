import torch
import numpy as np
from vajra.tracking.mesh import SphericalMeshBuilder

def test_mesh_generation_and_subdivision():
    v, f = SphericalMeshBuilder.generate_icosahedron()
    assert len(v) == 12
    assert len(f) == 20

    # Level 1 subdivision: 12 + 30 = 42 vertices
    v1, f1 = SphericalMeshBuilder.subdivide_mesh(v, f, level=1)
    assert len(v1) == 42
    assert len(f1) == 80

    # Norm of all vertices must be strictly 1.0 (on the unit sphere)
    norms = np.linalg.norm(v1, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)

def test_graph_construction():
    graph = SphericalMeshBuilder.build_graph(level=2)
    assert graph.pos.shape[0] > 100
    assert graph.edge_index.shape[0] == 2
    assert graph.edge_attr.shape[0] == graph.edge_index.shape[1]
    assert graph.edge_attr.shape[1] == 3 # 3D vector displacement
