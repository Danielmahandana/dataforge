import os
import pytest
from pathlib import Path
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

def test_full_pipeline_flow(client, tmp_path):
    # 1. Generate realistic TVET sample PDF
    sample_pdf_path = tmp_path / "test_tvet_doc.pdf"
    SampleGenerator.generate_tvet_qualifications_pdf(str(sample_pdf_path))
    assert sample_pdf_path.exists()

    # 2. Create Project
    proj_res = client.post("/api/v1/projects", json={
        "name": "E2E Pipeline Test Project",
        "description": "Integration test for extraction pipeline",
        "tags": ["Integration", "Test"]
    })
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 3. Upload Document
    with open(sample_pdf_path, "rb") as f:
        upload_res = client.post(
            "/api/v1/documents/upload",
            data={"project_id": project_id, "doc_type": "qualifications"},
            files={"files": ("test_tvet_doc.pdf", f, "application/pdf")}
        )
    assert upload_res.status_code == 201
    uploaded_docs = upload_res.json()
    assert len(uploaded_docs) == 1
    doc_id = uploaded_docs[0]["id"]
    assert uploaded_docs[0]["doc_type"] == "qualifications"
    assert uploaded_docs[0]["page_count"] >= 1

    # 4. Inspect Document
    inspect_res = client.get(f"/api/v1/documents/{doc_id}/inspect")
    assert inspect_res.status_code == 200
    inspect_data = inspect_res.json()
    assert inspect_data["page_count"] >= 1
    assert len(inspect_data["pages_sample"]) >= 1

    # 5. Run Extraction Job
    job_res = client.post("/api/v1/extraction/jobs", json={
        "project_id": project_id,
        "document_ids": [doc_id],
        "pipeline_type": "qualifications",
        "target_dataset_name": "E2E TVET Dataset"
    })
    assert job_res.status_code == 202
    job_id = job_res.json()["id"]

    # Poll / wait for job completion
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

    assert completed_job is not None, "Extraction job timed out"
    assert completed_job["status"] == "completed", f"Job failed: {completed_job.get('error_message')}"
    dataset_id = completed_job["dataset_id"]
    assert dataset_id is not None

    # 6. Verify Dataset
    ds_res = client.get(f"/api/v1/datasets/{dataset_id}")
    assert ds_res.status_code == 200
    ds_data = ds_res.json()
    assert ds_data["record_count"] > 0
    assert ds_data["quality_score"] > 0

    # 7. Check Records and Provenance
    rec_res = client.get(f"/api/v1/datasets/{dataset_id}/records?page=1&page_size=20")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["total"] > 0
    first_rec = rec_data["records"][0]
    assert "provenance" in first_rec
    assert first_rec["provenance"]["document_id"] == doc_id
    assert first_rec["provenance"]["page_number"] >= 1

    # 8. Check Validation
    val_res = client.get(f"/api/v1/validation/datasets/{dataset_id}")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert "quality_score" in val_data

    # 9. Test Record Editing with Audit Trail
    first_rec_id = first_rec["id"]
    patch_res = client.patch(f"/api/v1/records/{first_rec_id}", json={
        "data": {**first_rec["data"], "qualification": "Advanced Occupational Certificate in Mechatronics"},
        "review_notes": "Verified against DHET Bursary Gazette 2026"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "human_reviewed"

    # Check Review Audit Trail
    review_res = client.get(f"/api/v1/review/datasets/{dataset_id}")
    assert review_res.status_code == 200
    reviews = review_res.json()
    assert len(reviews) >= 1
    assert reviews[0]["field_name"] == "qualification"

    # 10. Test Exports (CSV, JSON, XLSX)
    for fmt in ["csv", "json", "xlsx"]:
        exp_res = client.post(f"/api/v1/datasets/{dataset_id}/export", json={
            "format": fmt,
            "include_provenance": True
        })
        assert exp_res.status_code == 200
        exp_data = exp_res.json()
        assert exp_data["format"] == fmt
        assert exp_data["file_size_bytes"] > 0

        # Test download
        dl_res = client.get(exp_data["download_url"])
        assert dl_res.status_code == 200
        assert len(dl_res.content) == exp_data["file_size_bytes"]

    # 11. Delete dataset and document
    del_ds = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert del_ds.status_code == 204
    del_doc = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_doc.status_code == 204
