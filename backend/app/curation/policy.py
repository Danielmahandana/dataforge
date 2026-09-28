from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CurationPolicyConfig(BaseModel):
    id: str
    name: str
    description: str
    dimensions: Dict[str, str] = Field(default_factory=dict)
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    include_threshold: float = 0.85
    review_threshold: float = 0.55
    exclude_threshold: float = 0.55
    is_builtin: bool = True
    chambers_or_domains: List[str] = Field(default_factory=list)


BUILTIN_CURATION_POLICIES: Dict[str, CurationPolicyConfig] = {
    "merseta_ofo_relevance": CurationPolicyConfig(
        id="merseta_ofo_relevance",
        name="merSETA OFO Occupational Relevance Policy",
        description="Evaluates occupational relevance to merSETA manufacturing, engineering, automotive, plastics, tyre, and related industrial chambers.",
        dimensions={
            "occupational_relevance": "required",
            "sector_relevance": "required",
            "classification_evidence": "preferred",
            "textual_evidence": "preferred",
        },
        include_threshold=0.85,
        review_threshold=0.55,
        exclude_threshold=0.55,
        chambers_or_domains=[
            "Metal & Engineering",
            "Automotive Manufacturing",
            "Tyre Manufacturing",
            "Plastics Manufacturing",
            "Motor Retail",
            "Components Manufacturing",
            "Cross-Chamber Technical Trades",
        ],
        rules=[
            {
                "id": "direct_sector_match",
                "weight": 0.30,
                "description": "Explicit match to manufacturing, engineering, tooling, automotive, or industrial processes.",
            },
            {
                "id": "occupational_classification",
                "weight": 0.25,
                "description": "OFO Major/Minor group belongs to Engineering, Technicians, Artisans, or Plant/Machine Operators.",
            },
            {
                "id": "manufacturing_context",
                "weight": 0.20,
                "description": "Occupation operates within factory, workshop, plant, assembly line, or technical trade context.",
            },
            {
                "id": "technical_process_relevance",
                "weight": 0.15,
                "description": "Occupation requires technical machinery, design, maintenance, CAD, robotics, or quality assurance skills.",
            },
            {
                "id": "source_document_evidence",
                "weight": 0.10,
                "description": "Source text contains authoritative sector indicators or SETA classification references.",
            },
        ],
    ),
    "dhet_tvet_priority": CurationPolicyConfig(
        id="dhet_tvet_priority",
        name="DHET TVET College Occupational Qualifications Policy",
        description="Curates public TVET college programmes aligned with artisan development and national scarce skills.",
        dimensions={
            "qualification_validity": "required",
            "artisan_trade_relevance": "required",
            "institutional_offering": "preferred",
        },
        include_threshold=0.80,
        review_threshold=0.50,
        exclude_threshold=0.50,
        chambers_or_domains=[
            "Engineering & Related Design",
            "Electrical Infrastructure",
            "Civil Engineering & Building",
            "Mechatronics & Robotics",
            "Information Technology",
        ],
        rules=[
            {"id": "saqa_registration", "weight": 0.35, "description": "Valid SAQA ID with active accreditation."},
            {"id": "artisan_pathway", "weight": 0.35, "description": "Leads to designated trade test qualification."},
            {"id": "college_delivery", "weight": 0.30, "description": "Verified delivery across accredited TVET colleges."},
        ],
    ),
    "green_skills_priority": CurationPolicyConfig(
        id="green_skills_priority",
        name="Green Skills & Just Transition Priority Policy",
        description="Identifies occupations and qualifications driving renewable energy, circular economy, and environmental sustainability.",
        dimensions={
            "sustainability_alignment": "required",
            "technical_competence": "preferred",
        },
        include_threshold=0.80,
        review_threshold=0.50,
        exclude_threshold=0.50,
        chambers_or_domains=[
            "Renewable Energy",
            "Solar & Wind Installation",
            "Electric Vehicle Maintenance",
            "Circular Economy & Recycling",
            "Green Hydrogen",
        ],
        rules=[
            {"id": "clean_tech_match", "weight": 0.40, "description": "Direct involvement in clean energy, PV, or battery technology."},
            {"id": "resource_efficiency", "weight": 0.35, "description": "Waste reduction, recycling, or emissions monitoring."},
            {"id": "environmental_compliance", "weight": 0.25, "description": "Environmental management and auditing."},
        ],
    ),
    "universal_curation_policy": CurationPolicyConfig(
        id="universal_curation_policy",
        name="Universal Evidence-Driven Curation Policy",
        description="Dynamic curation policy adapting to user-defined Dataset Intent scope, inclusion, and exclusion criteria.",
        dimensions={
            "intent_alignment": "required",
            "source_grounding": "preferred",
        },
        include_threshold=0.80,
        review_threshold=0.50,
        exclude_threshold=0.50,
        chambers_or_domains=["General Domain"],
        rules=[
            {"id": "scope_match", "weight": 0.40, "description": "Matches declared Dataset Intent scope concepts."},
            {"id": "inclusion_criteria", "weight": 0.40, "description": "Satisfies declared inclusion criteria."},
            {"id": "exclusion_guard", "weight": 0.20, "description": "Absence of declared exclusion patterns."},
        ],
    ),
}


def get_builtin_policies() -> List[CurationPolicyConfig]:
    return list(BUILTIN_CURATION_POLICIES.values())


def get_policy_by_id(policy_id: str) -> CurationPolicyConfig:
    return BUILTIN_CURATION_POLICIES.get(policy_id) or BUILTIN_CURATION_POLICIES["universal_curation_policy"]
