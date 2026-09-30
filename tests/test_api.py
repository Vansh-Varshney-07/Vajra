from fastapi.testclient import TestClient
from vajra.api.main import app

client = TestClient(app)

def test_root_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

def test_get_events():
    response = client.get("/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert events[0]["event_id"] == "BOB-CYC-2026-001"

def test_get_trajectory():
    response = client.get("/events/BOB-CYC-2026-001/trajectory")
    assert response.status_code == 200
    data = response.json()
    assert "consensus_path" in data
    assert "ensemble_tracks" in data
    assert len(data["ensemble_tracks"]) > 0

def test_get_impact_zone():
    response = client.get("/events/BOB-CYC-2026-001/impact")
    assert response.status_code == 200
    data = response.json()
    assert "impact_zone_geojson" in data
    assert data["impact_zone_geojson"]["geometry"]["type"] == "Polygon"

def test_downscale_endpoint():
    response = client.post(
        "/events/BOB-CYC-2026-001/downscale",
        json={"event_id": "BOB-CYC-2026-001", "target_lead_time_hr": 72, "num_samples": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grid_resolution_km"] == 5.0
    assert "statistics" in data
