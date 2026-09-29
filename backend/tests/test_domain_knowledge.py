import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import init_db
from backend.app.knowledge.domain_knowledge_generator import DomainKnowledgeGenerator, DomainKnowledgeArtifact
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.document import Document


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Test 1: Mpumalanga OIHD Domain Knowledge Generation
# ---------------------------------------------------------------------------
def test_mpumalanga_oihd_domain_knowledge():
    """Verifies that an OIHD dataset generates all 16 sections, infers Occupation unit,
    extracts OFO codes, minimum qualifications, and produces a valid deterministic hash."""
    dataset = {
        "id": "ds-mpumalanga-oihd-001",
        "name": "Mpumalanga Final List of Occupations in High Demand (2024)",
        "description": "Consolidated authoritative list of 167 occupations in high demand in Mpumalanga Province.",
        "version_label": "v1.0",
        "schema_name": "occupations",
        "schema_columns": [
            {"name": "ofo_code", "type": "string", "required": True, "description": "6-digit OFO occupation code"},
            {"name": "occupation_title", "type": "string", "required": True, "description": "Authoritative occupational title"},
            {"name": "minimum_qualification_required", "type": "string", "required": False, "description": "Minimum NQF qualification"},
            {"name": "employment_demand_indicator", "type": "string", "required": False, "description": "Provincial labour demand rating"},
        ],
        "quality_score": 98.5,
        "quality_dimensions": {"extraction": 100.0, "curation": 98.0, "provenance": 100.0},
        "curation_summary": {"included": 2, "excluded": 0, "review_required": 0, "unprocessed": 0},
    }

    doc = {
        "id": "doc-mpumalanga-report",
        "original_name": "Mpumalanga-Occupations in High Demand List-April 2024.pdf",
        "file_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
        "page_count": 72,
        "doc_metadata": {
            "profile_summary": {
                "title": "Mpumalanga List of Occupations in High Demand: A Technical Research Report",
                "publisher": "Mpumalanga Provincial Government / DHET",
                "publication_date": "April 2024",
                "document_type": "Research Publication / Policy Report",
            }
        },
    }

    records = [
        {
            "id": "rec-1",
            "row_index": 1,
            "data": {
                "ofo_code": "2021-112101",
                "occupation_title": "Director",
                "minimum_qualification_required": "Bachelor Degree (NQF 7)",
                "employment_demand_indicator": "High Demand",
            },
            "raw_data": {
                "ofo_code": "2021-112101",
                "occupation_title": "Director",
                "minimum_qualification_required": "Bachelor Degree",
            },
            "provenance": {
                "document_name": "Mpumalanga-Occupations in High Demand List-April 2024.pdf",
                "page_number": 31,
                "source_section": "PART 5: CONSOLIDATION OF EVIDENCE",
                "source_table": "Table 4",
            },
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "Identified as provincial high-demand priority in Table 4",
            "multi_confidence": {"extraction": 0.99, "curation": 0.98},
            "derived_data": {"derived_chambers": ["Manufacturing", "Services"]},
        },
        {
            "id": "rec-2",
            "row_index": 2,
            "data": {
                "ofo_code": "2021-214401",
                "occupation_title": "Mechanical Engineer",
                "minimum_qualification_required": "Bachelor of Science in Engineering (NQF 8)",
                "employment_demand_indicator": "Critical Scarcity",
            },
            "raw_data": {
                "ofo_code": "2021-214401",
                "occupation_title": "Mechanical Engineer",
                "minimum_qualification_required": "BSc Eng",
            },
            "provenance": {
                "document_name": "Mpumalanga-Occupations in High Demand List-April 2024.pdf",
                "page_number": 32,
                "source_section": "PART 5: CONSOLIDATION OF EVIDENCE",
                "source_table": "Table 4",
            },
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "High demand engineering priority occupation",
            "multi_confidence": {"extraction": 0.99, "curation": 0.99},
            "derived_data": {"derived_chambers": ["Metal & Engineering"]},
        },
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records, document=doc)

    assert isinstance(artifact, DomainKnowledgeArtifact)
    assert artifact.record_count == 2
    assert len(artifact.content_hash) == 64
    assert artifact.filename.endswith("_domain_knowledge.txt")

    content = artifact.content

    # Verify all 16 core sections are present
    assert "1. DATASET IDENTITY" in content
    assert "2. SOURCE DOCUMENT" in content
    assert "3. DATASET DESCRIPTION" in content
    assert "4. UNIT OF OBSERVATION" in content
    assert "5. DATASET STATISTICS" in content
    assert "6. SCHEMA KNOWLEDGE" in content
    assert "7. DOMAIN ENTITIES" in content
    assert "8. DOMAIN VOCABULARY & NORMALIZATION AUDIT" in content
    assert "9. DIRECT FACTUAL RELATIONSHIPS" in content
    assert "10. DERIVED RESEARCH DATA POINTS" in content
    assert "11. RECORD-LEVEL KNOWLEDGE (CURATED & AUDITED)" in content
    assert "12. CURATION GOVERNANCE STATUS" in content
    assert "13. VALIDATION STATUS" in content
    assert "14. RESEARCH QUALITY GATES" in content
    assert "15. PROVENANCE & LINEAGE TRACEABILITY" in content
    assert "16. RESEARCH NOTES & METHODOLOGICAL CONTEXT" in content

    # Verify Unit of Observation is Occupation
    assert "Primary Entity: Occupation" in content

    # Verify entities and identifiers
    assert "2021-112101" in content
    assert "2021-214401" in content
    assert "Director" in content
    assert "Mechanical Engineer" in content
    assert "Bachelor Degree (NQF 7)" in content

    # Verify reproducibility metadata manifest
    assert "REPRODUCIBILITY METADATA MANIFEST" in content
    assert f"Content SHA-256 Hash:        {artifact.content_hash}" in content


# ---------------------------------------------------------------------------
# Test 2: Generic Dataset Domain Knowledge Generation
# ---------------------------------------------------------------------------
def test_generic_dataset_domain_knowledge():
    """Verifies that a non-occupational dataset does NOT assume OFO or Occupations."""
    dataset = {
        "id": "ds-company-001",
        "name": "Mpumalanga Agro-Processing Enterprises",
        "description": "Register of registered agro-processing enterprises in the Ehlanzeni district.",
        "version_label": "v1.0",
        "schema_name": "generic",
        "schema_columns": [
            {"name": "company_name", "type": "string", "required": True},
            {"name": "enterprise_reg_no", "type": "string", "required": True},
            {"name": "annual_turnover_zar", "type": "float", "required": False},
            {"name": "district_municipality", "type": "string", "required": False},
        ],
    }

    records = [
        {
            "id": "r1",
            "row_index": 1,
            "data": {
                "company_name": "Lowveld Citrus Processors Pty Ltd",
                "enterprise_reg_no": "2018/123456/07",
                "annual_turnover_zar": "45000000",
                "district_municipality": "Ehlanzeni",
            },
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "Verified active enterprise in target district",
        }
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records)
    content = artifact.content

    # Should detect company/enterprise, NOT occupation
    assert "Primary Entity: Company / Enterprise" in content
    assert "Organising Framework for Occupations" not in content

    # Identifier categorization
    assert "enterprise_reg_no" in content
    assert "Lowveld Citrus Processors Pty Ltd" in content


# ---------------------------------------------------------------------------
# Test 3: Qualification Dataset Domain Knowledge Generation
# ---------------------------------------------------------------------------
def test_qualification_dataset_domain_knowledge():
    """Verifies that a TVET qualification dataset infers Qualification unit of observation."""
    dataset = {
        "id": "ds-tvet-001",
        "name": "TVET Accredited Occupational Qualifications",
        "schema_name": "qualifications",
        "schema_columns": [
            {"name": "saqa_id", "type": "string", "required": True},
            {"name": "qualification_title", "type": "string", "required": True},
            {"name": "nqf_level", "type": "integer", "required": True},
            {"name": "subframework", "type": "string", "required": False},
        ],
    }

    records = [
        {
            "id": "r1",
            "row_index": 1,
            "data": {
                "saqa_id": "67491",
                "qualification_title": "National Certificate: Mechatronics",
                "nqf_level": "Level 4",
                "subframework": "OQSF",
            },
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "Accredited TVET offering",
        }
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records)
    content = artifact.content

    assert "Primary Entity: Qualification" in content
    assert "67491" in content
    assert "National Certificate: Mechatronics" in content
    assert "Level 4" in content


# ---------------------------------------------------------------------------
# Test 4: Missing Values Handling (Zero Blind Trust)
# ---------------------------------------------------------------------------
def test_missing_values_zero_blind_trust():
    """Verifies that empty/null fields are not fabricated into imaginary statements."""
    dataset = {
        "id": "ds-missing-001",
        "name": "Sample With Missing Fields",
        "schema_name": "generic",
        "schema_columns": [
            {"name": "item_code", "type": "string", "required": True},
            {"name": "optional_metric", "type": "string", "required": False},
        ],
    }

    records = [
        {
            "id": "r1",
            "row_index": 1,
            "data": {
                "item_code": "ITEM-A",
                "optional_metric": None,
            },
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "Included without optional metric",
        }
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records)
    content = artifact.content

    # Coverage should show 0 populated
    assert "optional_metric: 0/1 populated (0.0%)" in content
    # Item A should be present
    assert "ITEM-A" in content


# ---------------------------------------------------------------------------
# Test 5: Excluded Records Segregation into Audit Log
# ---------------------------------------------------------------------------
def test_excluded_records_segregated_to_audit_log():
    """Verifies that EXCLUDED records are separated from primary entities into the audit section."""
    dataset = {
        "id": "ds-curation-tier-001",
        "name": "Curation Tier Dataset",
        "schema_name": "occupations",
        "schema_columns": [
            {"name": "ofo_code", "type": "string", "required": True},
            {"name": "occupation_title", "type": "string", "required": True},
        ],
    }

    records = [
        {
            "id": "r1",
            "row_index": 1,
            "data": {"ofo_code": "2021-111101", "occupation_title": "Legislator"},
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "Authoritative occupational listing",
        },
        {
            "id": "r2",
            "row_index": 2,
            "data": {"ofo_code": "2021-999999", "occupation_title": "Irrelevant Out-of-Scope Job"},
            "status": "valid",
            "curation_decision": "EXCLUDE",
            "curation_reason": "Not within provincial economic target scope",
        },
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records)
    content = artifact.content

    # Primary entities section must include the included record
    assert "Legislator" in content

    # Excluded record must appear in Exclusion Audit Log
    assert "EXCLUDED RECORDS (AUDIT LOG" in content
    assert "2021-999999" in content
    assert "Not within provincial economic target scope" in content


# ---------------------------------------------------------------------------
# Test 6: Review Records Segregation into Pending Research Review
# ---------------------------------------------------------------------------
def test_review_records_segregated_to_pending_review():
    """Verifies that REVIEW records are isolated in Pending Research Review."""
    dataset = {
        "id": "ds-review-tier-001",
        "name": "Review Tier Dataset",
        "schema_name": "occupations",
        "schema_columns": [
            {"name": "ofo_code", "type": "string", "required": True},
            {"name": "occupation_title", "type": "string", "required": True},
        ],
    }

    records = [
        {
            "id": "r1",
            "row_index": 1,
            "data": {"ofo_code": "2021-214401", "occupation_title": "Mechanical Engineer"},
            "status": "valid",
            "curation_decision": "INCLUDE",
            "curation_reason": "Confirmed match",
        },
        {
            "id": "r2",
            "row_index": 2,
            "data": {"ofo_code": "2021-2144", "occupation_title": "Ambiguous Engineering Role"},
            "status": "warning",
            "curation_decision": "REVIEW",
            "curation_reason": "Unit group code provided instead of 6-digit occupation specialization",
        },
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records)
    content = artifact.content

    assert "PENDING REVIEW RECORDS" in content
    assert "Ambiguous Engineering Role" in content
    assert "Unit group code provided instead of 6-digit occupation specialization" in content


# ---------------------------------------------------------------------------
# Test 7: Provenance & Lineage Retention
# ---------------------------------------------------------------------------
def test_provenance_and_lineage_retention():
    """Verifies that source document name, page numbers, sections, and hashes are preserved."""
    dataset = {
        "id": "ds-prov-001",
        "name": "Provenance Retention Dataset",
        "schema_name": "generic",
        "schema_columns": [{"name": "item", "type": "string", "required": True}],
    }

    doc = {
        "id": "doc-abc-123",
        "original_name": "Provincial_Gazette_Vol_45.pdf",
        "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "page_count": 45,
    }

    records = [
        {
            "id": "r1",
            "row_index": 1,
            "data": {"item": "Sample Item"},
            "provenance": {
                "document_name": "Provincial_Gazette_Vol_45.pdf",
                "page_number": 42,
                "source_section": "Schedule 3: Tariffs",
                "source_table": "Table 12",
            },
            "status": "valid",
            "curation_decision": "INCLUDE",
        }
    ]

    artifact = DomainKnowledgeGenerator.generate(dataset, records, document=doc)
    content = artifact.content

    assert "Provincial_Gazette_Vol_45.pdf" in content
    assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in content
    assert "Schedule 3: Tariffs" in content
    assert "Table 12" in content
    assert "Source Page Numbers: 42" in content


# ---------------------------------------------------------------------------
# Test 8: Determinism & Hash Reproducibility
# ---------------------------------------------------------------------------
def test_determinism_and_hash_reproducibility():
    """Verifies that generating the artifact twice produces the exact same hash and content."""
    dataset = {
        "id": "ds-det-001",
        "name": "Deterministic Hash Dataset",
        "schema_name": "generic",
        "schema_columns": [{"name": "code", "type": "string", "required": True}],
    }

    records = [
        {"id": "r1", "row_index": 1, "data": {"code": "ALPHA"}, "status": "valid", "curation_decision": "INCLUDE"},
        {"id": "r2", "row_index": 2, "data": {"code": "BETA"}, "status": "valid", "curation_decision": "INCLUDE"},
    ]

    artifact1 = DomainKnowledgeGenerator.generate(dataset, records)
    artifact2 = DomainKnowledgeGenerator.generate(dataset, records)

    # Hashes must be identical
    assert artifact1.content_hash == artifact2.content_hash

    # Body lines (excluding generated_at timestamp) must be identical
    lines1 = [l for l in artifact1.content.splitlines() if not l.startswith("Generated At:") and not l.startswith("Generated At (UTC):")]
    lines2 = [l for l in artifact2.content.splitlines() if not l.startswith("Generated At:") and not l.startswith("Generated At (UTC):")]
    assert lines1 == lines2

    # Mutating a record must change the hash
    records_mutated = [
        {"id": "r1", "row_index": 1, "data": {"code": "GAMMA"}, "status": "valid", "curation_decision": "INCLUDE"},
        {"id": "r2", "row_index": 2, "data": {"code": "BETA"}, "status": "valid", "curation_decision": "INCLUDE"},
    ]
    artifact3 = DomainKnowledgeGenerator.generate(dataset, records_mutated)
    assert artifact3.content_hash != artifact1.content_hash


# ---------------------------------------------------------------------------
# Test 9: Export API Endpoint & ZIP Bundle Integration
# ---------------------------------------------------------------------------
def test_export_api_with_bundle_and_regression(client):
    """Tests POST /datasets/{id}/export:
    1. include_domain_knowledge=True produces a ZIP bundle with dataset and .txt artifact.
    2. include_domain_knowledge=False produces direct CSV with format='csv' (100% backward compatible)."""
    # Create Project
    proj_res = client.post("/api/v1/projects", json={
        "name": "Export Bundle Test Project",
        "description": "Integration test for domain knowledge export bundle"
    })
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # Create Dataset directly
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        ds = Dataset(
            project_id=project_id,
            name="Bundle_Test_Dataset",
            schema_name="occupations",
            schema_columns=[
                {"name": "ofo_code", "type": "string", "required": True},
                {"name": "occupation_title", "type": "string", "required": True},
            ],
            record_count=2,
            valid_record_count=2,
            status="validated",
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)
        ds_id = ds.id

        r1 = Record(
            dataset_id=ds_id,
            row_index=1,
            data={"ofo_code": "2021-112101", "occupation_title": "Director"},
            raw_data={"ofo_code": "2021-112101", "occupation_title": "Director"},
            provenance={"document_name": "Test.pdf", "page_number": 1},
            status="valid",
            curation_decision="INCLUDE",
            curation_reason="Validated",
        )
        r2 = Record(
            dataset_id=ds_id,
            row_index=2,
            data={"ofo_code": "2021-214401", "occupation_title": "Mechanical Engineer"},
            raw_data={"ofo_code": "2021-214401", "occupation_title": "Mechanical Engineer"},
            provenance={"document_name": "Test.pdf", "page_number": 2},
            status="valid",
            curation_decision="INCLUDE",
            curation_reason="Validated",
        )
        db.add_all([r1, r2])
        db.commit()
    finally:
        db.close()

    # Case A: include_domain_knowledge = True -> ZIP bundle
    bundle_res = client.post(f"/api/v1/datasets/{ds_id}/export", json={
        "format": "csv",
        "include_domain_knowledge": True,
        "include_provenance": True,
    })
    assert bundle_res.status_code == 200
    bundle_data = bundle_res.json()
    assert bundle_data["format"] == "zip"
    assert bundle_data["filename"].endswith(".zip")
    assert bundle_data["domain_knowledge_filename"].endswith("_domain_knowledge.txt")
    assert len(bundle_data["domain_knowledge_hash"]) == 64

    # Download ZIP bundle and inspect contents
    dl_res = client.get(bundle_data["download_url"])
    assert dl_res.status_code == 200
    zip_bytes = io.BytesIO(dl_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert any(n.endswith(".csv") for n in namelist)
        assert any(n.endswith("_domain_knowledge.txt") for n in namelist)

        # Inspect the txt inside the zip
        txt_name = [n for n in namelist if n.endswith("_domain_knowledge.txt")][0]
        txt_content = zf.read(txt_name).decode("utf-8")
        assert "1. DATASET IDENTITY" in txt_content
        assert "2021-112101" in txt_content

    # Case B: include_domain_knowledge = False -> Direct CSV (Zero Regression)
    direct_res = client.post(f"/api/v1/datasets/{ds_id}/export", json={
        "format": "csv",
        "include_domain_knowledge": False,
        "include_provenance": True,
    })
    assert direct_res.status_code == 200
    direct_data = direct_res.json()
    assert direct_data["format"] == "csv"
    assert direct_data["filename"].endswith(".csv")

    # Download CSV directly
    dl_direct = client.get(direct_data["download_url"])
    assert dl_direct.status_code == 200
    csv_text = dl_direct.content.decode("utf-8")
    assert "2021-112101" in csv_text
    assert "Director" in csv_text


# ---------------------------------------------------------------------------
# Test 10: GET Domain Knowledge Endpoints (Preview & Download)
# ---------------------------------------------------------------------------
def test_get_domain_knowledge_endpoints(client):
    """Tests GET /api/v1/datasets/{id}/domain-knowledge for preview and download."""
    # Create Project & Dataset
    proj_res = client.post("/api/v1/projects", json={"name": "Preview Test Project"})
    project_id = proj_res.json()["id"]

    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        ds = Dataset(
            project_id=project_id,
            name="Preview_Dataset",
            schema_name="occupations",
            schema_columns=[
                {"name": "ofo_code", "type": "string", "required": True},
                {"name": "occupation_title", "type": "string", "required": True},
            ],
            record_count=1,
            valid_record_count=1,
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)
        ds_id = ds.id

        r = Record(
            dataset_id=ds_id,
            row_index=1,
            data={"ofo_code": "2021-653306", "occupation_title": "Diesel Mechanic"},
            status="valid",
            curation_decision="INCLUDE",
        )
        db.add(r)
        db.commit()
    finally:
        db.close()

    # 1. Preview endpoint (JSON)
    prev_res = client.get(f"/api/v1/datasets/{ds_id}/domain-knowledge")
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["dataset_id"] == ds_id
    assert prev_data["record_count"] == 1
    assert "Diesel Mechanic" in prev_data["content"]
    assert len(prev_data["content_hash"]) == 64
    assert prev_data["filename"].endswith("_domain_knowledge.txt")

    # 2. Download endpoint (FileResponse text/plain)
    dl_res = client.get(f"/api/v1/datasets/{ds_id}/domain-knowledge?download=true")
    assert dl_res.status_code == 200
    assert "text/plain" in dl_res.headers["content-type"]
    text_content = dl_res.content.decode("utf-8")
    assert "2021-653306" in text_content
    assert "Diesel Mechanic" in text_content
