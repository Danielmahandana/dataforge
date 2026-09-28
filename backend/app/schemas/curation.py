from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DatasetIntentBase(BaseModel):
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    objective: str
    scope: List[str] = Field(default_factory=list)
    include_criteria: List[str] = Field(default_factory=list)
    exclude_criteria: List[str] = Field(default_factory=list)
    authoritative_sources: List[str] = Field(default_factory=list)
    classification_system: str = "OFO_2024"
    target_entities: List[str] = Field(default_factory=list)
    target_relationships: List[str] = Field(default_factory=list)
    review_threshold: float = 0.70


class DatasetIntentCreate(DatasetIntentBase):
    project_id: Optional[str] = None


class DatasetIntentResponse(DatasetIntentBase):
    id: str
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurationPolicyBase(BaseModel):
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    include_threshold: float = 0.85
    review_threshold: float = 0.55
    exclude_threshold: float = 0.55


class CurationPolicyCreate(CurationPolicyBase):
    id: str  # slug or identifier


class CurationPolicyResponse(CurationPolicyBase):
    id: str
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurationRunCreate(BaseModel):
    dataset_id: str
    intent_id: Optional[str] = None
    policy_id: Optional[str] = "merseta_ofo_relevance"
    custom_policy: Optional[CurationPolicyBase] = None
    enable_llm_reasoning: bool = True
    llm_tier: str = "fast"  # fast or reasoning


class CurationRunResponse(BaseModel):
    id: str
    dataset_id: str
    intent_id: Optional[str] = None
    policy_id: Optional[str] = None
    status: str
    progress: int
    total_records: int
    included_count: int
    excluded_count: int
    review_count: int
    engine_version: str = "2.2.0"
    ruleset_version: str = "2024.1"
    manifest: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemResponse(BaseModel):
    id: str
    record_id: str
    decision_id: Optional[str] = None
    evidence_type: str  # SOURCE_FACT, DERIVED_CLASSIFICATION, RULE_INFERENCE, SEMANTIC_INFERENCE, LLM_INFERENCE, HUMAN_DECISION
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    cell_key: Optional[str] = None
    source_text: Optional[str] = None
    observed_source_value: Optional[str] = None
    relationship: Optional[str] = None
    interpretation: Optional[str] = None
    strength: str = "STRONG"
    is_inherited: bool = False
    inherited_from: Optional[str] = None
    claim: str
    rule_id: Optional[str] = None
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionLedgerResponse(BaseModel):
    id: str
    record_id: str
    dataset_id: str
    stage: str
    field_name: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    actor: str
    actor_id: str
    metadata_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurationDecisionResponse(BaseModel):
    id: str
    record_id: str
    dataset_id: str
    run_id: Optional[str] = None
    decision: str  # INCLUDE, EXCLUDE, REVIEW
    confidence: float
    multi_confidence: Dict[str, float] = Field(default_factory=dict)
    primary_claim: Optional[str] = None
    reason: Optional[str] = None
    why_not: Optional[str] = None
    decision_method: str = "DETERMINISTIC_RULES"
    uncertainties: List[str] = Field(default_factory=list)
    derived_fields: Dict[str, Any] = Field(default_factory=dict)
    explanation_contract: Dict[str, Any] = Field(default_factory=dict)
    conflict_ids: List[str] = Field(default_factory=list)
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None
    evidence_items: List[EvidenceItemResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordReviewRequest(BaseModel):
    decision: str  # INCLUDE, EXCLUDE, OVERRIDE
    notes: Optional[str] = None
    corrected_data: Optional[Dict[str, Any]] = None
    reviewer_name: Optional[str] = "Researcher"


class ReviewQueueItem(BaseModel):
    record_id: str
    dataset_id: str
    row_index: int
    primary_title: str
    identifier: Optional[str] = None
    decision: str  # REVIEW, EXCLUDE, INCLUDE
    priority: str  # critical, high, medium
    reason_code: str  # low_confidence, duplicate_risk, classification_conflict, validation_error, ambiguous_evidence
    reason_details: str
    overall_confidence: float
    multi_confidence: Dict[str, float]
    provenance: Dict[str, Any]
    data: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None
    derived_data: Optional[Dict[str, Any]] = None
    evidence_summary: List[str] = Field(default_factory=list)


class ReviewQueueResponse(BaseModel):
    dataset_id: str
    total_review_required: int
    critical_count: int
    high_count: int
    medium_count: int
    items: List[ReviewQueueItem]


class LineageStep(BaseModel):
    stage: str
    title: str
    description: str
    timestamp: Optional[datetime] = None
    actor: str
    status: str
    data_snapshot: Dict[str, Any] = Field(default_factory=dict)
    provenance: Optional[Dict[str, Any]] = None


class LineageGraphResponse(BaseModel):
    record_id: str
    dataset_id: str
    source_document: Dict[str, Any]
    steps: List[LineageStep]
    ledger: List[DecisionLedgerResponse]


class QualityDimensionsResponse(BaseModel):
    extraction: float
    structural: float
    normalization: float
    validation: float
    completeness: float
    consistency: float
    curation: float
    provenance: float
    overall: float


class QualityGatesResponse(BaseModel):
    overall_score: float
    dimensions: QualityDimensionsResponse
    gates: Dict[str, str]  # gate_name -> passed | failed | warning | pending
    critical_issues_count: int
    warning_count: int
    can_export_clean: bool
    can_export_research: bool
    reasons: List[str] = Field(default_factory=list)


class DeduplicationRunResponse(BaseModel):
    dataset_id: str
    total_records_analyzed: int
    exact_duplicates_count: int
    structural_duplicates_count: int
    semantic_candidates_count: int
    duplicates_flagged: List[Dict[str, Any]] = Field(default_factory=list)


class SourceConflictResponse(BaseModel):
    id: str
    dataset_id: str
    record_id: Optional[str] = None
    conflict_type: str
    source_a: Dict[str, Any]
    source_b: Dict[str, Any]
    field_name: Optional[str] = None
    severity: str
    resolution_status: str
    resolved_value: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
