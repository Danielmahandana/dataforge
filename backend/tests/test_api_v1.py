import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "database" in data

def test_project_crud(client):
    # 1. Create Project
    create_res = client.post("/api/v1/projects", json={
        "name": "Wits DHET TVET Study 2026",
        "description": "Labour market research on vocational qualifications",
        "tags": ["DHET", "TVET", "merSETA"]
    })
    assert create_res.status_code == 201
    proj = create_res.json()
    proj_id = proj["id"]
    assert proj["name"] == "Wits DHET TVET Study 2026"
    assert proj["tags"] == ["DHET", "TVET", "merSETA"]

    # 2. Get Project
    get_res = client.get(f"/api/v1/projects/{proj_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == proj_id

    # 3. List Projects
    list_res = client.get("/api/v1/projects")
    assert list_res.status_code == 200
    assert any(p["id"] == proj_id for p in list_res.json())

    # 4. Update Project
    update_res = client.put(f"/api/v1/projects/{proj_id}", json={
        "description": "Updated research scope description"
    })
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated research scope description"

    # 5. Delete Project
    del_res = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_res.status_code == 204

    # 6. Verify deleted
    get_after = client.get(f"/api/v1/projects/{proj_id}")
    assert get_after.status_code == 404

def test_system_reset(client):
    # Create sample project first
    client.post("/api/v1/projects", json={"name": "Test Project For Reset"})
    
    # Reset system
    reset_res = client.post("/api/v1/system/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "success"

    # Verify projects are cleared
    projects_res = client.get("/api/v1/projects")
    assert len(projects_res.json()) == 0

