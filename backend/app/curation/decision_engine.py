from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.curation.rule_engine import RuleEvaluationResult
from backend.app.curation.policy import CurationPolicyConfig
from backend.app.curation.conflict_detector import ConflictItem


class CurationDecisionResult(BaseModel):
    decision: str  # INCLUDE, EXCLUDE, REVIEW
    confidence: float
    multi_confidence: Dict[str, float]  # {extraction, normalization, validation, curation, overall}
    confidence_basis: str
    primary_claim: str
    reason: str
    why_not: Optional[str] = None
    decision_method: str = "DETERMINISTIC_RULES"
    uncertainties: List[str] = Field(default_factory=list)
    derived_fields: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"  # critical, high, medium (for review queue)
    reason_code: Optional[str] = None  # low_confidence, duplicate_risk, classification_conflict, validation_error, ambiguous_evidence
    explanation_contract: Dict[str, Any] = Field(default_factory=dict)
    conflict_ids: List[str] = Field(default_factory=list)


class DecisionEngine:
    """Computes defensible 3-state decisions (INCLUDE, EXCLUDE, REVIEW) with interpretable,
    reproducible confidence formulations and structured explanation contracts."""

    @classmethod
    def resolve_decision(
        cls,
        rule_result: RuleEvaluationResult,
        policy: CurationPolicyConfig,
        extraction_conf: float = 1.0,
        has_validation_error: bool = False,
        has_validation_warning: bool = False,
        duplicate_flag: Optional[str] = None,
        conflicts: Optional[List[ConflictItem]] = None,
        llm_decision: Optional[Dict[str, Any]] = None,
        hierarchy_info: Optional[Dict[str, Any]] = None,
    ) -> CurationDecisionResult:
        score = rule_result.total_score
        chambers = rule_result.suggested_chambers
        uncertainties: List[str] = []
        conflicts = conflicts or []

        # Categorize conflicts
        hard_conflicts = [c for c in conflicts if c.conflict_type in ["CLASSIFICATION_VS_TITLE", "SEMANTIC_CONTRADICTION", "RULE_VS_TAXONOMY"]]

        # 1. Multi-dimensional confidence calculations
        ext_conf = round(float(extraction_conf or 1.0), 3)
        norm_conf = 0.95 if has_validation_warning else 0.99
        val_conf = 0.40 if has_validation_error else (0.85 if has_validation_warning else 1.0)
        
        # Taxonomic certainty based on hierarchy depth or score
        if hierarchy_info and hierarchy_info.get("direct_unit_match"):
            tax_certainty = 0.95
        elif hierarchy_info and hierarchy_info.get("levels"):
            tax_certainty = 0.85
        elif score >= 0.85:
            tax_certainty = 0.95
        else:
            tax_certainty = 0.60

        cur_conf = round(min(max((score * 0.70 + tax_certainty * 0.30), 0.40), 0.98), 3)

        # Apply conflict penalty to confidence if hard contradictions are present
        conflict_penalty = 0.25 if hard_conflicts else (0.05 if conflicts else 0.0)
        cur_conf = round(max(cur_conf - conflict_penalty, 0.20), 3)

        # Composite overall confidence
        overall_conf = round(
            ext_conf * 0.20 + norm_conf * 0.15 + val_conf * 0.25 + cur_conf * 0.40, 3
        )

        decision_method = "DETERMINISTIC_RULES"
        if llm_decision and not llm_decision.get("error"):
            decision_method = "LLM_ASSISTED_BORDERLINE"
            llm_conf = float(llm_decision.get("confidence", 0.8))
            cur_conf = round((cur_conf + llm_conf) / 2.0, 3)
            overall_conf = round((overall_conf + llm_conf) / 2.0, 3)
            if llm_decision.get("uncertainties"):
                uncertainties.extend(llm_decision["uncertainties"])

        # 2. Decision Logic with Zero Blind Trust Guardrails
        decision = "REVIEW"
        reason_code = None
        priority = "medium"
        primary_claim = ""
        reason = ""
        why_not = rule_result.why_not

        # Priority Check 1: Hard Source Conflicts (e.g. OFO code says Engineer, but title says Bookkeeper)
        if hard_conflicts:
            decision = "REVIEW"
            priority = "critical"
            reason_code = "classification_conflict"
            primary_claim = f"Contradictory evidence detected ({len(hard_conflicts)} conflict{'s' if len(hard_conflicts)>1 else ''})"
            conflict_descriptions = [f"{c.conflict_type}: {c.claim_a} vs {c.claim_b}" for c in hard_conflicts]
            reason = f"Evidence sources disagree. {'; '.join(conflict_descriptions)}. DataForge routes to Human Review to prevent corrupted dataset ingestion."
            uncertainties.append("Taxonomy, rule, or employer context contradiction detected.")

        # Priority Check 2: Explicit Domain Exclusion (e.g. Enterprise Support Role like Accountant / Cleaner)
        elif rule_result.strong_exclusion:
            decision = "EXCLUDE"
            primary_claim = "Excluded by domain relevance criteria"
            reason = rule_result.exclusion_reason or "Non-industrial domain exclusion criteria matched."
            why_not = rule_result.why_not or f"Record matches non-industrial exclusion condition: {rule_result.exclusion_reason}."
            cur_conf = 0.95

        # Priority Check 3: Schema Validation Errors
        elif has_validation_error:
            decision = "REVIEW"
            priority = "critical"
            reason_code = "validation_error"
            primary_claim = "Validation error prohibits automated inclusion"
            reason = "Record contains structural schema validation errors that must be resolved by an operator before inclusion."
            uncertainties.append("Schema constraint violation detected.")

        # Priority Check 4: Other Contextual Conflicts
        elif conflicts:
            decision = "REVIEW"
            priority = "high"
            reason_code = "classification_conflict"
            primary_claim = "Contextual conflict detected between employer and occupational scope"
            conflict_descriptions = [f"{c.conflict_type}: {c.claim_a} vs {c.claim_b}" for c in conflicts]
            reason = f"Contextual divergence: {'; '.join(conflict_descriptions)}."
            uncertainties.append("Employer context diverges from occupational core.")

        # Priority Check 5: Ambiguous Leadership / Broad Scope
        elif rule_result.is_ambiguous_role:
            decision = "REVIEW"
            priority = "high"
            reason_code = "ambiguous_evidence"
            primary_claim = "Broad leadership or general management scope"
            reason = "Occupation title indicates broad operations or general plant management without specialized technical trade demarcation. Human review required."
            uncertainties.append("Broad occupational scope without specific technical qualification.")

        # Priority Check 6: Score-based Decision
        elif score >= policy.include_threshold:
            decision = "INCLUDE"
            primary_claim = "Strong multi-factor evidence supporting inclusion"
            chambers_str = f" for {', '.join(chambers[:2])}" if chambers else ""
            reason = f"Relevance score ({int(score*100)}%) meets policy threshold (>= {int(policy.include_threshold*100)}%){chambers_str}."

        elif score < policy.exclude_threshold:
            decision = "EXCLUDE"
            primary_claim = "Insufficient sector and occupational relevance evidence"
            reason = f"Relevance score ({int(score*100)}%) below inclusion policy threshold (< {int(policy.exclude_threshold*100)}%)."
            if not why_not:
                why_not = (
                    f"The dataset objective concerns manufacturing/engineering capabilities. "
                    f"Record score ({int(score*100)}%) did not meet the required inclusion threshold "
                    f"({int(policy.include_threshold*100)}%) and lacked sufficient technical trade evidence."
                )

        else:
            decision = "REVIEW"
            priority = "high"
            reason_code = "low_confidence"
            primary_claim = "Borderline relevance evidence requiring human judgment"
            reason = f"Relevance score ({int(score*100)}%) falls in the ambiguous zone ({int(policy.review_threshold*100)}% - {int(policy.include_threshold*100)}%). DataForge recommends human review."
            uncertainties.append("Evidence is ambiguous or borderline.")

        # 3. Transparent Confidence Basis Formulation
        conf_basis = (
            f"Overall confidence {overall_conf} derived from: "
            f"Extraction fidelity {ext_conf} (20%), Normalization {norm_conf} (15%), "
            f"Validation {val_conf} (25%), Curation relevance {cur_conf} (40%). "
            f"Taxonomic certainty: {tax_certainty}."
        )
        if conflicts:
            conf_basis += f" Penalized by -{conflict_penalty} due to {len(conflicts)} detected conflict(s)."

        # 4. Structured Explanation Contract
        explanation_contract = {
            "decision": decision,
            "confidence": overall_conf,
            "confidence_basis": conf_basis,
            "decision_method": decision_method,
            "requires_review": decision == "REVIEW",
            "reason": reason,
            "why_not": why_not if decision == "EXCLUDE" else None,
            "conflicts_count": len(conflicts),
            "conflicts": [c.model_dump() for c in conflicts],
            "uncertainties": uncertainties,
            "policy_id": policy.id,
        }

        derived_fields = {
            "derived_relevance_score": score,
            "derived_decision": decision,
            "derived_chambers": chambers,
            "derived_policy": policy.id,
            "derived_relevance_basis": primary_claim,
            "derived_why_not": why_not if decision == "EXCLUDE" else None,
        }

        multi_conf = {
            "extraction": ext_conf,
            "normalization": norm_conf,
            "validation": val_conf,
            "curation": cur_conf,
            "overall": overall_conf,
        }

        return CurationDecisionResult(
            decision=decision,
            confidence=overall_conf,
            multi_confidence=multi_conf,
            confidence_basis=conf_basis,
            primary_claim=primary_claim,
            reason=reason,
            why_not=why_not,
            decision_method=decision_method,
            uncertainties=uncertainties,
            derived_fields=derived_fields,
            priority=priority,
            reason_code=reason_code,
            explanation_contract=explanation_contract,
            conflict_ids=[],
        )
