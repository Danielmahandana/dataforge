import pytest
from backend.app.curation.policy import get_builtin_policies, get_policy_by_id
from backend.app.curation.classification_resolver import ClassificationResolver
from backend.app.curation.rule_engine import RuleEngine
from backend.app.curation.decision_engine import DecisionEngine
from backend.app.curation.evidence_builder import EvidenceBuilder
from backend.app.curation.deduplicator import SemanticDeduplicator
from backend.app.curation.quality_engine import QualityEngine


def test_builtin_policies():
    policies = get_builtin_policies()
    assert len(policies) >= 4
    policy_ids = [p.id for p in policies]
    assert "merseta_ofo_relevance" in policy_ids
    assert "dhet_tvet_priority" in policy_ids
    assert "green_skills_priority" in policy_ids
    assert "universal_curation_policy" in policy_ids

    merseta_policy = get_policy_by_id("merseta_ofo_relevance")
    assert merseta_policy.include_threshold == 0.85
    assert merseta_policy.review_threshold == 0.55
    assert len(merseta_policy.chambers_or_domains) >= 6


def test_classification_resolver_ofo():
    # OFO code 311501: Mechanical Engineering Technician
    res = ClassificationResolver.resolve_ofo_hierarchy("311501")
    assert res["valid_format"] is True
    assert res["levels"]["major"]["code"] == "3"
    assert "Technicians" in res["levels"]["major"]["title"]
    assert res["levels"]["sub_major"]["code"] == "31"
    assert res["levels"]["unit"]["code"] == "3115"
    assert "Mechanical Engineering Technicians" in res["levels"]["unit"]["title"]
    assert res["sector_affinity"] >= 0.90
    assert any("Metal & Engineering" in c for c in res["matched_chambers"])


def test_rule_engine_relevance():
    policy = get_policy_by_id("merseta_ofo_relevance")

    # Record 1: Mechanical Engineering Technician
    rec_tech = {"ofo_code": "311501", "occupation_title": "Mechanical Engineering Technician"}
    hier_tech = ClassificationResolver.resolve_ofo_hierarchy("311501")
    eval_tech = RuleEngine.evaluate(rec_tech, hier_tech, policy)
    assert eval_tech.suggested_decision == "INCLUDE"
    assert eval_tech.total_score >= 0.85
    assert not eval_tech.strong_exclusion

    # Record 2: Primary School Teacher (Non-industrial exclusion)
    rec_teacher = {"ofo_code": "234101", "occupation_title": "Primary School Teacher"}
    hier_teacher = ClassificationResolver.resolve_ofo_hierarchy("234101")
    eval_teacher = RuleEngine.evaluate(rec_teacher, hier_teacher, policy)
    assert eval_teacher.strong_exclusion is True
    assert eval_teacher.suggested_decision == "EXCLUDE"
    assert eval_teacher.total_score <= 0.25

    # Record 3: Borderline record (e.g. general clerk in retail)
    rec_clerk = {"ofo_code": "411001", "occupation_title": "General Office Clerk"}
    hier_clerk = ClassificationResolver.resolve_ofo_hierarchy("411001")
    eval_clerk = RuleEngine.evaluate(rec_clerk, hier_clerk, policy)
    assert eval_clerk.suggested_decision in ["EXCLUDE", "REVIEW"]


def test_decision_engine_three_states():
    policy = get_policy_by_id("merseta_ofo_relevance")

    # Simulate strong include
    rec = {"ofo_code": "311501", "occupation_title": "Mechanical Engineering Technician"}
    hier = ClassificationResolver.resolve_ofo_hierarchy("311501")
    rule_res = RuleEngine.evaluate(rec, hier, policy)
    dec = DecisionEngine.resolve_decision(rule_res, policy, extraction_conf=0.98)
    assert dec.decision == "INCLUDE"
    assert dec.confidence >= 0.85
    assert dec.multi_confidence["extraction"] == 0.98
    assert dec.multi_confidence["curation"] >= 0.85

    # Simulate schema error -> must force REVIEW state with critical priority
    dec_err = DecisionEngine.resolve_decision(rule_res, policy, extraction_conf=0.98, has_validation_error=True)
    assert dec_err.decision == "REVIEW"
    assert dec_err.priority == "critical"
    assert dec_err.reason_code == "validation_error"


def test_evidence_builder():
    rec = {"ofo_code": "311501", "occupation_title": "Mechanical Engineering Technician"}
    prov = {"document_id": "doc_123", "document_name": "OFO_2024.pdf", "page_number": 42, "table_index": 1}
    hier = ClassificationResolver.resolve_ofo_hierarchy("311501")
    policy = get_policy_by_id("merseta_ofo_relevance")
    rule_res = RuleEngine.evaluate(rec, hier, policy)

    ev_list = EvidenceBuilder.build_evidence_set(
        record_data=rec,
        raw_data={"occupation_title": "Mechanical Enginering Technican"},
        provenance=prov,
        row_index=1,
        hierarchy_info=hier,
        rule_assertions=rule_res.assertions,
        chambers=["Metal & Engineering"],
    )
    assert len(ev_list) >= 3
    ev_types = [e.evidence_type for e in ev_list]
    assert "SOURCE_FACT" in ev_types
    assert "DERIVED_CLASSIFICATION" in ev_types
    assert "RULE_INFERENCE" in ev_types


def test_semantic_deduplication():
    records = [
        {"id": "rec_1", "data": {"ofo_code": "311501", "occupation_title": "Mechanical Engineering Technician"}},
        {"id": "rec_2", "data": {"ofo_code": "311501", "occupation_title": "Mechanical Engineering Tech"}},
        {"id": "rec_3", "data": {"ofo_code": "652201", "occupation_title": "Motor Vehicle Mechanic"}},
    ]
    flags = SemanticDeduplicator.analyze_dataset_duplicates(records)
    assert len(flags) >= 1
    flag_types = [f.duplicate_type for f in flags]
    assert "STRUCTURAL_DUPLICATE" in flag_types or "POSSIBLE_SEMANTIC_DUPLICATE" in flag_types


def test_quality_engine_dimensions_and_gates():
    res = QualityEngine.evaluate(
        total_records=100,
        valid_records=95,
        error_records=1,
        warning_records=4,
        review_required_count=5,
        duplicate_count=2,
    )
    assert res.overall_score > 80.0
    assert res.dimensions.extraction >= 90.0
    assert res.dimensions.validation >= 90.0
    assert "extraction_gate" in res.gates
    assert "validation_gate" in res.gates
    assert "export_gate" in res.gates
    assert res.critical_issues_count == 1
