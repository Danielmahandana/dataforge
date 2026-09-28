from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.app.curation.policy import CurationPolicyConfig
from backend.app.curation.classification_resolver import ClassificationResolver
from backend.app.curation.conflict_detector import ConflictDetector, ConflictItem
from backend.app.curation.rule_engine import RuleEngine, RuleEvaluationResult
from backend.app.curation.evidence_builder import EvidenceBuilder, EvidenceDraft
from backend.app.curation.decision_engine import DecisionEngine, CurationDecisionResult


class RecordEvaluationPackage(BaseModel):
    decision_result: CurationDecisionResult
    rule_result: RuleEvaluationResult
    hierarchy_info: Dict[str, Any]
    evidence_items: List[EvidenceDraft]
    conflicts: List[ConflictItem] = Field(default_factory=list)


class RelevanceEvaluator:
    """Coordinates tiered relevance evaluation, contextual classification resolution,
    conflict detection, and traceable evidence generation."""

    @classmethod
    def evaluate_record(
        cls,
        record_data: Dict[str, Any],
        raw_data: Optional[Dict[str, Any]],
        provenance: Dict[str, Any],
        row_index: int,
        policy: CurationPolicyConfig,
        scope_domains: Optional[List[str]] = None,
        exclude_criteria: Optional[List[str]] = None,
        has_validation_error: bool = False,
        has_validation_warning: bool = False,
        duplicate_flag: Optional[str] = None,
        llm_decision: Optional[Dict[str, Any]] = None,
    ) -> RecordEvaluationPackage:
        # 1. Resolve Classification Hierarchy Context (Tier 2)
        ofo_code = record_data.get("ofo_code") or record_data.get("code") or ""
        hierarchy_info = ClassificationResolver.resolve_ofo_hierarchy(str(ofo_code))

        # 2. Evaluate Rule Engine Assertions (Tier 1)
        rule_result = RuleEngine.evaluate(
            record_data=record_data,
            hierarchy_info=hierarchy_info,
            policy=policy,
            scope_domains=scope_domains,
            exclude_criteria=exclude_criteria,
        )

        # 3. Detect Source Conflicts & Contradictions (Zero Blind Trust)
        conflicts = ConflictDetector.detect_conflicts(
            record_data=record_data,
            raw_data=raw_data,
            provenance=provenance,
            hierarchy_info=hierarchy_info,
            matched_chambers=rule_result.suggested_chambers,
        )

        # 4. Resolve Decision, Interpretable Confidence, and Explanation Contract
        extraction_conf = float(provenance.get("confidence") or 1.0)
        decision_result = DecisionEngine.resolve_decision(
            rule_result=rule_result,
            policy=policy,
            extraction_conf=extraction_conf,
            has_validation_error=has_validation_error,
            has_validation_warning=has_validation_warning,
            duplicate_flag=duplicate_flag,
            conflicts=conflicts,
            llm_decision=llm_decision,
            hierarchy_info=hierarchy_info,
        )

        # 5. Build Structured Evidence Items
        semantic_notes = None
        if llm_decision and llm_decision.get("reason"):
            semantic_notes = f"LLM reasoning: {llm_decision['reason']}"

        evidence_items = EvidenceBuilder.build_evidence_set(
            record_data=record_data,
            raw_data=raw_data,
            provenance=provenance,
            row_index=row_index,
            hierarchy_info=hierarchy_info,
            rule_assertions=rule_result.assertions,
            chambers=rule_result.suggested_chambers,
            semantic_notes=semantic_notes,
            conflicts=conflicts,
        )

        return RecordEvaluationPackage(
            decision_result=decision_result,
            rule_result=rule_result,
            hierarchy_info=hierarchy_info,
            evidence_items=evidence_items,
            conflicts=conflicts,
        )
