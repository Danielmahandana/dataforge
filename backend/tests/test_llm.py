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

def test_llm_status_endpoint(client):
    res = client.get("/api/v1/llm/status")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "active_provider" in data
    assert "active_model" in data
    assert "supported_providers" in data

def test_llm_query_and_summarize(client):
    # 1. Create project & dataset
    proj_res = client.post("/api/v1/projects", json={
        "name": "LLM Test Project",
        "description": "Testing LLM Q&A endpoints"
    })
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 2. Test LLM query with non-existent dataset
    bad_res = client.post("/api/v1/llm/query-dataset", json={
        "dataset_id": "non-existent-id",
        "query": "What qualifications are listed?"
    })
    assert bad_res.status_code == 404
