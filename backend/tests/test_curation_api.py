import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import init_db
from backend.demo.sample_generator import SampleGenerator


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_curation_api_workflow(client, tmp_path):
    # 1. Create a Project
    proj_res = client.post("/api/v1/projects", json={
        "name": "Curation API Test Project",
        "description": "Integration test for semantic curation"
    })
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Test Dataset Intent CRUD
    intent_res = client.post("/api/v1/curation/intents", json={
        "project_id": project_id,
        "name": "merSETA Target Occupations Intent",
        "objective": "Identify technical artisan and engineering occupations relevant to South African manufacturing",
        "scope": ["Metal & Engineering", "Automotive Manufacturing", "Components Manufacturing"],
        "include_criteria": ["engineering occupations", "artisan trades", "technicians"],
        "exclude_criteria": ["primary school teaching", "nursing", "general retail clerking"],
        "authoritative_sources": ["OFO 2024", "merSETA SSP 2025/2026"]
    })
    assert intent_res.status_code == 201
    intent = intent_res.json()
    intent_id = intent["id"]
    assert "merSETA" in intent["name"]

    # List intents
    list_intents = client.get(f"/api/v1/curation/intents?project_id={project_id}").json()
    assert len(list_intents) >= 1

    # 3. Test Curation Policies endpoint
    policies = client.get("/api/v1/curation/policies").json()
    assert len(policies) >= 4
    assert any(p["id"] == "merseta_ofo_relevance" for p in policies)

    # 4. Generate TVET Sample Document & Run Extraction
    sample_pdf = tmp_path / "curation_tvet_doc.pdf"
    SampleGenerator.generate_tvet_qualifications_pdf(str(sample_pdf))

    with open(sample_pdf, "rb") as f:
        up_res = client.post(
            "/api/v1/documents/upload",
            data={"project_id": project_id, "doc_type": "qualifications"},
            files={"files": ("curation_tvet_doc.pdf", f, "application/pdf")},
        )
    assert up_res.status_code == 201
    doc_id = up_res.json()[0]["id"]

    # Trigger extraction job
    job_res = client.post("/api/v1/extraction/jobs", json={
        "project_id": project_id,
        "document_ids": [doc_id],
        "pipeline_type": "qualifications",
        "target_dataset_name": "Curation TVET Test Dataset"
    })
    assert job_res.status_code == 202
    job_id = job_res.json()["id"]

    # Poll until extraction completes
    import time
    max_wait = 15
    start = time.time()
    completed_job = None
    while time.time() - start < max_wait:
        j_check = client.get(f"/api/v1/extraction/jobs/{job_id}").json()
        if j_check["status"] in ["completed", "failed"]:
            completed_job = j_check
            break
        time.sleep(0.5)

    assert completed_job is not None and completed_job["status"] == "completed"
    dataset_id = completed_job["dataset_id"]

    # 5. Launch Curation Run
    cur_res = client.post("/api/v1/curation/runs", json={
        "dataset_id": dataset_id,
        "intent_id": intent_id,
        "policy_id": "merseta_ofo_relevance",
    })
    assert cur_res.status_code == 202
    run_id = cur_res.json()["id"]

    # Wait for curation to complete
    start = time.time()
    completed_run = None
    while time.time() - start < max_wait:
        r_check = client.get(f"/api/v1/curation/runs/{run_id}").json()
        if r_check["status"] in ["completed", "failed"]:
            completed_run = r_check
            break
        time.sleep(0.5)

    assert completed_run is not None and completed_run["status"] == "completed"
    assert completed_run["total_records"] > 0

    # 6. Check Records with Curation Fields
    recs = client.get(f"/api/v1/datasets/{dataset_id}/records?page=1&page_size=10").json()
    assert len(recs["records"]) > 0
    first_record = recs["records"][0]
    first_rec_id = first_record["id"]

    # 7. Check Evidence Items for Record
    ev_res = client.get(f"/api/v1/curation/records/{first_rec_id}/evidence")
    assert ev_res.status_code == 200
    evidence_items = ev_res.json()
    assert len(evidence_items) >= 1

    # 8. Check Lineage Graph for Record
    lineage_res = client.get(f"/api/v1/curation/records/{first_rec_id}/lineage")
    assert lineage_res.status_code == 200
    lineage_data = lineage_res.json()
    assert "source_document" in lineage_data
    assert len(lineage_data["steps"]) >= 4
    assert len(lineage_data["ledger"]) >= 1

    # 9. Test Review Queue
    queue_res = client.get(f"/api/v1/curation/datasets/{dataset_id}/review-queue")
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert "total_review_required" in queue_data

    # 10. Test Review Decision Override
    rev_override = client.post(f"/api/v1/curation/records/{first_rec_id}/review", json={
        "decision": "INCLUDE",
        "notes": "Verified against DHET merSETA Skills Accord 2026",
        "reviewer_name": "Lead Researcher"
    })
    assert rev_override.status_code == 200
    assert rev_override.json()["decision"] == "INCLUDE"

    # 11. Test Semantic Deduplication Run
    dedup_res = client.post(f"/api/v1/curation/datasets/{dataset_id}/deduplicate")
    assert dedup_res.status_code == 200
    assert "total_records_analyzed" in dedup_res.json()

    # 12. Test Quality Gates Endpoint
    gates_res = client.get(f"/api/v1/curation/datasets/{dataset_id}/quality-gates")
    assert gates_res.status_code == 200
    gates_data = gates_res.json()
    assert "dimensions" in gates_data
    assert "gates" in gates_data
    assert "extraction" in gates_data["dimensions"]

    # 13. Test Export with Curation Metadata
    exp_res = client.post(f"/api/v1/datasets/{dataset_id}/export", json={
        "format": "csv",
        "include_provenance": True,
        "include_curation": True,
    })
    assert exp_res.status_code == 200
    assert exp_res.json()["file_size_bytes"] > 0

    # 14. Test Curation Run Manifest
    manifest_res = client.get(f"/api/v1/curation/runs/{run_id}/manifest")
    assert manifest_res.status_code == 200
    manifest_data = manifest_res.json()
    assert manifest_data["run_id"] == run_id
    assert manifest_data["engine_version"] == "2.2.0"
    assert manifest_data["ruleset_version"] == "2024.1"

    # 15. Test Project Isolation
    other_proj = client.post("/api/v1/projects", json={"name": "Isolated Project"}).json()
    other_proj_id = other_proj["id"]
    iso_res = client.get(f"/api/v1/curation/datasets/{dataset_id}/review-queue?project_id={other_proj_id}")
    assert iso_res.status_code == 404
