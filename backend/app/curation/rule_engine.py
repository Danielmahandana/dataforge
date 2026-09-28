from __future__ import annotations
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.curation.policy import CurationPolicyConfig


class RuleAssertion(BaseModel):
    rule_id: str
    description: str
    weight: float
    satisfied: bool
    score_contribution: float
    claim: str
    evidence_type: str = "RULE_INFERENCE"
    confidence: float = 1.0


class RuleEvaluationResult(BaseModel):
    total_score: float
    assertions: List[RuleAssertion]
    suggested_decision: str  # INCLUDE, EXCLUDE, REVIEW
    suggested_chambers: List[str]
    strong_exclusion: bool = False
    exclusion_reason: Optional[str] = None
    why_not: Optional[str] = None
    is_ambiguous_role: bool = False
    is_support_role_in_industrial_firm: bool = False


class RuleEngine:
    """Evaluates deterministic domain rules and structural criteria with strict separation of
    occupational capability from employer context.
    Under Zero Blind Trust, an Accountant or Cleaner working at an Automotive or Tyre plant
    is NOT classified as a manufacturing technical trade."""

    # Explicit occupational capabilities that indicate technical/industrial core trade
    TECHNICAL_OCCUPATIONAL_CORE = [
        "engineering", "mechanic", "mechanical", "electrical", "electronic",
        "metal", "machinist", "toolmaker", "fitter", "welder", "boiler",
        "turner", "automotive", "diesel", "panelbeater", "spraypainter",
        "plastics", "polymer", "injection", "moulding", "tyre", "rubber",
        "vulcanis", "assembler", "fabricat", "artisan", "instrumentation",
        "mechatronic", "robotics", "automation", "cad", "draughting",
        "metallurg", "foundry", "casting"
    ]

    # Enterprise-support occupations (Administrative, Financial, Legal, Hospitality, Elementary)
    # These roles occur across all industries but do NOT constitute manufacturing domain core capabilities.
    ENTERPRISE_SUPPORT_ROLES = [
        "accountant", "bookkeeper", "auditor", "financial controller", "payroll clerk",
        "cleaner", "sweeper", "office cleaner", "janitor", "tea lady", "cook", "kitchen hand",
        "receptionist", "secretary", "switchboard", "filing clerk",
        "lawyer", "attorney", "paralegal", "legal advisor",
        "nurse", "clinic sister", "doctor",
        "travel agent", "hotel receptionist", "waiter", "bartender"
    ]

    NON_INDUSTRIAL_EXCLUSIONS = [
        "teacher", "primary school teacher", "kindergarten", "beautician", "hairdresser",
        "librarian", "hotel receptionist", "waiter", "bartender", "flight attendant",
        "travel agent", "actuary", "lawyer", "judge", "paralegal", "dentist", "surgeon",
        "pharmacist", "physician", "nurse", "midwife"
    ]

    # Broad, ambiguous leadership roles requiring human context review
    AMBIGUOUS_LEADERSHIP_ROLES = [
        "operations manager", "general manager", "production manager",
        "shift supervisor", "factory manager", "plant coordinator"
    ]

    @classmethod
    def evaluate(
        cls,
        record_data: Dict[str, Any],
        hierarchy_info: Dict[str, Any],
        policy: CurationPolicyConfig,
        scope_domains: Optional[List[str]] = None,
        exclude_criteria: Optional[List[str]] = None,
    ) -> RuleEvaluationResult:
        # Separate occupational title from company/employer context
        title = str(
            record_data.get("occupation_title")
            or record_data.get("occupation")
            or record_data.get("qualification")
            or record_data.get("qualification_name")
            or record_data.get("title")
            or ""
        ).strip().lower()

        company_context = str(
            record_data.get("company_name")
            or record_data.get("employer")
            or record_data.get("organization")
            or record_data.get("enterprise")
            or ""
        ).strip().lower()

        full_corpus = " ".join(str(v).lower() for v in record_data.values() if v is not None)

        assertions: List[RuleAssertion] = []
        total_score = 0.0
        strong_exclusion = False
        exclusion_reason = None
        why_not = None
        is_ambiguous = False
        is_support_role = False

        # 1. Check Non-Industrial Exclusions
        for excl in cls.NON_INDUSTRIAL_EXCLUSIONS:
            if re.search(rf"\b{re.escape(excl)}\b", title):
                if not any(ind in title for ind in ["industrial", "automotive", "engineering"]):
                    strong_exclusion = True
                    exclusion_reason = f"Matches non-industrial exclusion profile: '{excl}'"
                    why_not = f"The dataset objective concerns manufacturing/engineering capabilities. Occupation '{title}' belongs to the non-industrial exclusion profile ('{excl}')."
                    break

        # 2. Check for Enterprise Support Role (Company != Occupation Guard)
        if not strong_exclusion:
            is_support_match = any(re.search(rf"\b{re.escape(role)}\b", title) for role in cls.ENTERPRISE_SUPPORT_ROLES)
            if is_support_match:
                is_support_role = True
                strong_exclusion = True
                exclusion_reason = f"Identified as enterprise-support function ('{title}')"
                why_not = (
                    f"The dataset objective concerns occupationally connected manufacturing and engineering capabilities. "
                    f"Although '{title}' may be employed within an industrial enterprise ('{company_context or 'industrial firm'}'), "
                    f"no sufficient evidence establishes this occupation as part of the core manufacturing or engineering trade domain."
                )

        # 2. Check for Explicit Declared Exclusions
        if not strong_exclusion and exclude_criteria:
            for crit in exclude_criteria:
                crit_clean = crit.strip().lower()
                if crit_clean and re.search(rf"\b{re.escape(crit_clean)}\b", title):
                    strong_exclusion = True
                    exclusion_reason = f"Matches declared exclusion criteria: '{crit}'"
                    why_not = f"Record title matches dataset intent exclusion condition: '{crit}'."
                    break

        # 3. Check for Ambiguous Leadership / Broad Scope
        if not strong_exclusion:
            for amb in cls.AMBIGUOUS_LEADERSHIP_ROLES:
                if re.search(rf"\b{re.escape(amb)}\b", title):
                    # If it has a specific technical qualifier (e.g. 'operations manager: tool & die'), it's less ambiguous
                    has_tech_spec = any(tech in title for tech in ["die", "mould", "tool", "mechanical", "electrical", "welding"])
                    if not has_tech_spec:
                        is_ambiguous = True
                        break

        # 4. Evaluate Technical Core & Taxonomy Evidence
        major_code = hierarchy_info.get("levels", {}).get("major", {}).get("code")
        unit_code = hierarchy_info.get("levels", {}).get("unit", {}).get("code")
        has_direct_unit = hierarchy_info.get("direct_unit_match", False)
        matched_chambers = list(hierarchy_info.get("matched_chambers", []))

        # Check title token technical core (NOT from company name)
        has_technical_title = any(term in title for term in cls.TECHNICAL_OCCUPATIONAL_CORE)

        # Add explicit chambers ONLY when supported by occupational title or unit group taxonomy
        if "motor" in title or "vehicle" in title or "auto" in title:
            if "Automotive Manufacturing" not in matched_chambers:
                matched_chambers.append("Automotive Manufacturing")
        if "metal" in title or "weld" in title or "fitter" in title or "tool" in title:
            if "Metal & Engineering" not in matched_chambers:
                matched_chambers.append("Metal & Engineering")
        if "plastic" in title or "polymer" in title or "mould" in title:
            if "Plastics Manufacturing" not in matched_chambers:
                matched_chambers.append("Plastics Manufacturing")
        if "tyre" in title or "rubber" in title:
            if "Tyre Manufacturing" not in matched_chambers:
                matched_chambers.append("Tyre Manufacturing")

        # 5. Evaluate Policy Rules
        for r in policy.rules:
            rule_id = r.get("id")
            weight = float(r.get("weight", 0.2))
            satisfied = False
            claim = ""
            conf = 1.0

            if strong_exclusion:
                satisfied = False
                claim = f"Rule negated by exclusion: {exclusion_reason}"
                conf = 0.95
            elif rule_id in ["direct_sector_match", "clean_tech_match", "scope_match"]:
                if has_technical_title and (has_direct_unit or matched_chambers):
                    satisfied = True
                    chambers_str = ", ".join(matched_chambers[:2]) if matched_chambers else "Manufacturing Core"
                    claim = f"Direct occupational match to technical manufacturing core: {chambers_str}"
                    conf = 0.95
                elif has_technical_title:
                    satisfied = True
                    claim = "Technical occupational indicators verified in occupational title"
                    conf = 0.85
                else:
                    claim = "No occupational technical keywords identified in title"
                    conf = 0.70

            elif rule_id in ["occupational_classification", "artisan_pathway"]:
                if major_code in ["2", "3", "6", "7"]:
                    satisfied = True
                    level_name = "Unit Group" if has_direct_unit else "Major Group"
                    code_val = unit_code if has_direct_unit else major_code
                    claim = f"OFO Taxonomy classifies record under technical group ({level_name} {code_val})"
                    conf = 0.95 if has_direct_unit else 0.75
                elif major_code:
                    claim = f"OFO Taxonomy indicates non-technical Major Group {major_code}"
                    conf = 0.80
                else:
                    claim = "Taxonomy unclassified (no valid OFO code)"
                    conf = 0.50

            elif rule_id in ["manufacturing_context", "resource_efficiency", "college_delivery"]:
                if has_technical_title or (major_code in ["6", "7"]):
                    satisfied = True
                    claim = "Contextual alignment with workshop/plant manufacturing trade environment"
                    conf = 0.85
                else:
                    claim = "No direct industrial/manufacturing trade context verified"
                    conf = 0.60

            elif rule_id in ["technical_process_relevance", "environmental_compliance"]:
                if any(k in title for k in ["machin", "technic", "artisan", "fitter", "welder", "operator", "assembler"]):
                    satisfied = True
                    claim = "Technical machinery, tooling, or assembly process competence verified"
                    conf = 0.90
                else:
                    claim = "No specialized machinery or tooling processes indicated"
                    conf = 0.60

            elif rule_id in ["source_document_evidence", "saqa_registration", "exclusion_guard"]:
                doc_name = record_data.get("document_name") or record_data.get("_prov_doc")
                if doc_name:
                    satisfied = True
                    claim = f"Grounding established via source document: '{doc_name}'"
                    conf = 0.90
                else:
                    claim = "General tabular extraction without explicit document attribution"
                    conf = 0.60

            contribution = weight if satisfied else 0.0
            total_score += contribution

            assertions.append(
                RuleAssertion(
                    rule_id=rule_id,
                    description=r.get("description", ""),
                    weight=weight,
                    satisfied=satisfied,
                    score_contribution=round(contribution, 3),
                    claim=claim,
                    confidence=conf,
                )
            )

        # Determine Suggested Decision
        if strong_exclusion:
            suggested_decision = "EXCLUDE"
        elif is_ambiguous:
            suggested_decision = "REVIEW"
        elif total_score >= policy.include_threshold:
            suggested_decision = "INCLUDE"
        elif total_score < policy.exclude_threshold:
            suggested_decision = "EXCLUDE"
            if not why_not:
                why_not = (
                    f"The dataset objective concerns manufacturing/engineering capabilities. "
                    f"Record score ({int(total_score*100)}%) did not meet the required inclusion threshold "
                    f"({int(policy.include_threshold*100)}%) and lacked sufficient technical trade evidence."
                )
        else:
            suggested_decision = "REVIEW"

        return RuleEvaluationResult(
            total_score=round(total_score, 3),
            assertions=assertions,
            suggested_decision=suggested_decision,
            suggested_chambers=matched_chambers,
            strong_exclusion=strong_exclusion,
            exclusion_reason=exclusion_reason,
            why_not=why_not,
            is_ambiguous_role=is_ambiguous,
            is_support_role_in_industrial_firm=is_support_role,
        )
