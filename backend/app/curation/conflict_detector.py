from __future__ import annotations
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ConflictItem(BaseModel):
    conflict_type: str  # CLASSIFICATION_VS_TITLE, COMPANY_VS_OCCUPATION, RULE_VS_TAXONOMY, SEMANTIC_CONTRADICTION
    severity: str = "high"  # critical, high, medium
    claim_a: str
    claim_b: str
    source_a: Dict[str, Any]
    source_b: Dict[str, Any]
    recommended_action: str = "ROUTE_TO_HUMAN_REVIEW"
    details: Optional[str] = None


class ConflictDetector:
    """Detects contradictions between source content, taxonomy classifications, company context, and rules.
    Under Zero Blind Trust, conflicting evidence MUST NOT be silently resolved by averaging or overriding;
    it must be explicitly flagged and routed to Human Review."""

    NON_TECHNICAL_TITLES = [
        "accountant", "bookkeeper", "auditor", "financial officer", "payroll clerk",
        "cleaner", "sweeper", "office cleaner", "janitor", "tea lady", "cook",
        "receptionist", "secretary", "filing clerk", "switchboard operator",
        "lawyer", "attorney", "paralegal", "legal advisor",
        "nurse", "clinic sister", "paramedic",
        "security guard", "caretaker"
    ]

    CORE_TECHNICAL_MAJORS = ["2", "3", "6", "7"]  # Professionals, Technicians, Craft/Artisans, Machine Operators
    NON_TECHNICAL_MAJORS = ["1", "4", "5", "8"]    # Managers, Clerical, Service/Sales, Elementary

    @classmethod
    def detect_conflicts(
        cls,
        record_data: Dict[str, Any],
        raw_data: Optional[Dict[str, Any]],
        provenance: Dict[str, Any],
        hierarchy_info: Dict[str, Any],
        matched_chambers: List[str],
    ) -> List[ConflictItem]:
        conflicts: List[ConflictItem] = []

        title = str(
            record_data.get("occupation_title")
            or record_data.get("occupation")
            or record_data.get("qualification")
            or record_data.get("title")
            or ""
        ).strip().lower()

        ofo_code = str(record_data.get("ofo_code") or record_data.get("code") or "").strip()
        major_code = hierarchy_info.get("levels", {}).get("major", {}).get("code")
        major_title = hierarchy_info.get("levels", {}).get("major", {}).get("title")

        # Contextual company / organization fields if present
        company_name = str(
            record_data.get("company_name")
            or record_data.get("employer")
            or record_data.get("organization")
            or record_data.get("enterprise")
            or ""
        ).strip().lower()

        # 1. Classification vs Title Contradiction
        # If taxonomy indicates technical engineering/trades, but title is clearly financial, clerical, or legal
        is_non_tech_title = any(re.search(rf"\b{re.escape(nt)}\b", title) for nt in cls.NON_TECHNICAL_TITLES)
        sub_major_code = hierarchy_info.get("levels", {}).get("sub_major", {}).get("code") or (ofo_code[:2] if len(ofo_code) >= 2 else "")
        is_tech_ofo = (major_code in ["6", "7"]) or (sub_major_code in ["21", "31"])

        if is_non_tech_title and is_tech_ofo:
            conflicts.append(
                ConflictItem(
                    conflict_type="CLASSIFICATION_VS_TITLE",
                    severity="critical",
                    claim_a=f"OFO Taxonomy classifies record under Technical Group {sub_major_code or major_code}: '{major_title}'",
                    claim_b=f"Occupational title '{title}' represents a general non-technical enterprise function",
                    source_a={"type": "OFO_TAXONOMY", "code": ofo_code, "level": "major", "value": major_title},
                    source_b={"type": "SOURCE_TEXT", "field": "title", "value": title},
                    recommended_action="ROUTE_TO_HUMAN_REVIEW",
                    details="Taxonomy classification code directly conflicts with observed occupational title.",
                )
            )

        # Conversely, title says Engineer / Artisan, but OFO says Clerical / Elementary / Non-technical
        is_tech_title = any(tech in title for tech in ["engineer", "technician", "artisan", "fitter", "welder", "machinist", "toolmaker"])
        is_non_tech_ofo = (major_code in ["4", "5", "8"]) or (sub_major_code in ["22", "23", "24", "26"])
        if is_tech_title and is_non_tech_ofo:
            conflicts.append(
                ConflictItem(
                    conflict_type="CLASSIFICATION_VS_TITLE",
                    severity="high",
                    claim_a=f"Occupational title '{title}' claims technical engineering/artisan status",
                    claim_b=f"OFO Taxonomy classifies record under non-technical Group {sub_major_code or major_code}: '{major_title}'",
                    source_a={"type": "SOURCE_TEXT", "field": "title", "value": title},
                    source_b={"type": "OFO_TAXONOMY", "code": ofo_code, "level": "major", "value": major_title},
                    recommended_action="ROUTE_TO_HUMAN_REVIEW",
                    details="Observed engineering title claims higher technical qualification than recorded taxonomy group.",
                )
            )

        # 2. Company Employment vs Occupational Function Divergence (The Accountant / Cleaner Fallacy)
        # If employer name has strong manufacturing/tyre/auto indicators, but occupation is an enterprise-support role
        industrial_company_terms = ["motor", "automotive", "tyre", "rubber", "plastics", "metal", "engineering", "foundry"]
        has_industrial_employer = any(term in company_name for term in industrial_company_terms)

        if has_industrial_employer and is_non_tech_title:
            conflicts.append(
                ConflictItem(
                    conflict_type="COMPANY_VS_OCCUPATION",
                    severity="medium",
                    claim_a=f"Employer '{company_name}' operates within industrial manufacturing sector",
                    claim_b=f"Occupation '{title}' is an enterprise support role without manufacturing domain core",
                    source_a={"type": "EMPLOYER_CONTEXT", "field": "company_name", "value": company_name},
                    source_b={"type": "OCCUPATIONAL_CORE", "field": "title", "value": title},
                    recommended_action="EXCLUDE_OR_CONFIRM_SUPPORT_ROLE",
                    details="Company employment must not be conflated with occupational domain relevance.",
                )
            )

        return conflicts
