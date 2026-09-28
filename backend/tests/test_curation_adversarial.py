import pytest
from backend.app.curation.policy import get_policy_by_id
from backend.app.curation.classification_resolver import ClassificationResolver
from backend.app.curation.conflict_detector import ConflictDetector
from backend.app.curation.rule_engine import RuleEngine
from backend.app.curation.decision_engine import DecisionEngine
from backend.app.curation.relevance_evaluator import RelevanceEvaluator
from backend.app.curation.deduplicator import SemanticDeduplicator
from backend.app.curation.manifest import ManifestBuilder


def test_adversarial_example_a_accountant_in_automotive_firm():
    """Example A:
    Occupation: Accountant
    Company: Automotive Manufacturer
    Expected: EXCLUDE from manufacturing technical core (company employment != occupational domain relevance).
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    record_data = {
        "occupation_title": "Accountant",
        "company_name": "Toyota Automotive Manufacturing SA",
        "ofo_code": "2411",  # OFO Major 24: Business and Administration Professionals
    }
    raw_data = {"occupation_title": "Accountant", "company_name": "Toyota Automotive Manufacturing SA"}
    provenance = {"document_id": "doc_1", "document_name": "Auto_Report.pdf", "page_number": 42}

    pkg = RelevanceEvaluator.evaluate_record(
        record_data=record_data,
        raw_data=raw_data,
        provenance=provenance,
        row_index=1,
        policy=policy,
    )

    # Must be EXCLUDED or at minimum REVIEW with why_not explanation; MUST NOT be INCLUDE
    assert pkg.decision_result.decision == "EXCLUDE"
    assert "enterprise-support function" in (pkg.decision_result.reason or "")
    assert pkg.decision_result.why_not is not None
    assert "manufacturing and engineering capabilities" in pkg.decision_result.why_not
    # Evidence must flag support role
    evidence_types = [e.evidence_type for e in pkg.evidence_items]
    assert "SOURCE_FACT" in evidence_types


def test_adversarial_example_b_mechanical_engineering_technician():
    """Example B:
    Occupation: Mechanical Engineering Technician
    Expected: Strong inclusion based on classification and occupational evidence.
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    record_data = {
        "occupation_title": "Mechanical Engineering Technician",
        "ofo_code": "3115",  # Unit Group 3115
    }
    raw_data = {"occupation_title": "Mechanical Engineering Technician"}
    provenance = {"document_id": "doc_2", "document_name": "OFO_Gazette.pdf", "page_number": 137}

    pkg = RelevanceEvaluator.evaluate_record(
        record_data=record_data,
        raw_data=raw_data,
        provenance=provenance,
        row_index=1,
        policy=policy,
    )

    assert pkg.decision_result.decision == "INCLUDE"
    assert pkg.decision_result.confidence >= 0.85
    assert "Metal & Engineering" in pkg.rule_result.suggested_chambers
    # Verifiable evidence items generated
    assert any(e.evidence_type == "DERIVED_CLASSIFICATION" and not e.is_inherited for e in pkg.evidence_items)


def test_adversarial_example_c_operations_manager_broad_scope():
    """Example C:
    Occupation: Operations Manager
    Expected: Potential REVIEW if evidence is broad; must not automatically include or exclude.
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    record_data = {
        "occupation_title": "Operations Manager",
        "ofo_code": "1219",  # General managers
    }
    raw_data = {"occupation_title": "Operations Manager"}
    provenance = {"document_id": "doc_3", "document_name": "Staff_List.pdf", "page_number": 5}

    pkg = RelevanceEvaluator.evaluate_record(
        record_data=record_data,
        raw_data=raw_data,
        provenance=provenance,
        row_index=1,
        policy=policy,
    )

    assert pkg.decision_result.decision == "REVIEW"
    assert pkg.decision_result.reason_code in ["ambiguous_evidence", "low_confidence"]
    assert "broad operations or general plant management" in pkg.decision_result.reason.lower()


def test_adversarial_example_d_automotive_assembly_technician():
    """Example D:
    Occupation: Automotive Assembly Technician
    Expected: Strong occupational relevance if source evidence supports it.
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    record_data = {
        "occupation_title": "Automotive Assembly Technician",
        "ofo_code": "7211",  # Mechanical Machinery Assemblers
    }
    raw_data = {"occupation_title": "Automotive Assembly Technician"}
    provenance = {"document_id": "doc_4", "document_name": "Production_Trades.pdf", "page_number": 88}

    pkg = RelevanceEvaluator.evaluate_record(
        record_data=record_data,
        raw_data=raw_data,
        provenance=provenance,
        row_index=1,
        policy=policy,
    )

    assert pkg.decision_result.decision == "INCLUDE"
    assert "Automotive Manufacturing" in pkg.rule_result.suggested_chambers


def test_adversarial_example_e_cleaner_in_tyre_firm():
    """Example E:
    Occupation: Cleaner
    Company: Dunlop Tyre Manufacturer
    Expected: Do not include simply because the company operates in a merSETA sector.
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    record_data = {
        "occupation_title": "Cleaner",
        "company_name": "Dunlop Tyre Manufacturing Co",
        "ofo_code": "8112",  # Cleaners and Helpers in Offices
    }
    raw_data = {"occupation_title": "Cleaner", "company_name": "Dunlop Tyre Manufacturing Co"}
    provenance = {"document_id": "doc_5", "document_name": "Factory_Roll.pdf", "page_number": 12}

    pkg = RelevanceEvaluator.evaluate_record(
        record_data=record_data,
        raw_data=raw_data,
        provenance=provenance,
        row_index=1,
        policy=policy,
    )

    assert pkg.decision_result.decision == "EXCLUDE"
    assert pkg.decision_result.why_not is not None
    assert "manufacturing" in pkg.decision_result.why_not.lower()


def test_adversarial_example_f_distinct_professional_tiers_not_merged():
    """Example F:
    Two semantically similar occupation names:
    Mechanical Engineering Technician
    Mechanical Engineering Technologist
    Expected: Potentially related, but NOT automatically merged (KEEP_SEPARATE).
    """
    records = [
        {"id": "rec_tech", "data": {"occupation_title": "Mechanical Engineering Technician", "ofo_code": "3115"}},
        {"id": "rec_technologist", "data": {"occupation_title": "Mechanical Engineering Technologist", "ofo_code": "2144"}},
    ]

    flags = SemanticDeduplicator.analyze_dataset_duplicates(records)
    assert len(flags) > 0
    # Must be categorized as LEGITIMATE_RELATED_RECORD and recommended to KEEP_SEPARATE
    flag = flags[0]
    assert flag.duplicate_type == "LEGITIMATE_RELATED_RECORD"
    assert flag.recommendation == "KEEP_SEPARATE"
    assert "Distinct professional" in flag.reason


def test_adversarial_example_g_conflicting_evidence_routes_to_review():
    """Example G:
    Conflicting evidence:
    Hierarchy: Engineering (Major 2)
    Occupation title: Financial Bookkeeper
    Expected: CONFLICT -> REVIEW, not silent inclusion or silent averaging.
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    record_data = {
        "occupation_title": "Financial Bookkeeper",
        "ofo_code": "2144",  # Mechanical Engineer code wrongly attached to a bookkeeper
    }
    raw_data = {"occupation_title": "Financial Bookkeeper"}
    provenance = {"document_id": "doc_6", "document_name": "Corrupted_Roll.pdf", "page_number": 3}

    pkg = RelevanceEvaluator.evaluate_record(
        record_data=record_data,
        raw_data=raw_data,
        provenance=provenance,
        row_index=1,
        policy=policy,
    )

    assert pkg.decision_result.decision == "REVIEW"
    assert len(pkg.conflicts) > 0
    assert pkg.decision_result.reason_code == "classification_conflict"
    assert any(c.conflict_type == "CLASSIFICATION_VS_TITLE" for c in pkg.conflicts)
    assert "contradiction" in pkg.decision_result.reason.lower() or "disagree" in pkg.decision_result.reason.lower()


def test_reproducibility_deterministic_manifest():
    """Reproducibility Test:
    Processing the exact same deterministic input twice must produce identical decisions,
    scores, reasons, and verifiable manifest structure.
    """
    policy = get_policy_by_id("merseta_ofo_relevance")
    rec = {
        "occupation_title": "Toolmaker",
        "ofo_code": "6512",
    }
    prov = {"document_id": "doc_x", "document_name": "Tooling.pdf", "page_number": 10}

    run_1 = RelevanceEvaluator.evaluate_record(
        record_data=rec, raw_data=rec, provenance=prov, row_index=1, policy=policy
    )
    run_2 = RelevanceEvaluator.evaluate_record(
        record_data=rec, raw_data=rec, provenance=prov, row_index=1, policy=policy
    )

    assert run_1.decision_result.decision == run_2.decision_result.decision
    assert run_1.decision_result.confidence == run_2.decision_result.confidence
    assert run_1.rule_result.total_score == run_2.rule_result.total_score
    assert len(run_1.evidence_items) == len(run_2.evidence_items)

    manifest = ManifestBuilder.generate_manifest(
        run_id="run_test",
        dataset_id="ds_test",
        dataset_name="Test Dataset",
        intent_data={"objective": "Test", "scope": ["Metal"]},
        policy_id=policy.id,
        policy_version="1.0.0",
        engine_version="2.2.0",
        ruleset_version="2024.1",
        source_documents=[{"document_id": "doc_x", "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}],
        record_counts=1,
        include_count=1,
        exclude_count=0,
        review_count=0,
        conflict_count=0,
        quality_metrics={"overall": 0.95},
    )

    assert manifest.engine_version == "2.2.0"
    assert manifest.ruleset_version == "2024.1"
    assert len(manifest.source_documents) == 1
    assert manifest.source_documents[0]["sha256_hash"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
