from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DatasetIntent(Base):
    __tablename__ = "dataset_intents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), default="1.0.0")
    description = Column(Text, nullable=True)
    objective = Column(Text, nullable=False)
    scope = Column(JSON, default=list)  # list of target sectors / chambers / domains
    include_criteria = Column(JSON, default=list)  # list of inclusion rules / concepts
    exclude_criteria = Column(JSON, default=list)  # list of exclusion rules / concepts
    authoritative_sources = Column(JSON, default=list)  # list of source documents / official codes
    classification_system = Column(String(100), default="OFO_2024")
    target_entities = Column(JSON, default=list)
    target_relationships = Column(JSON, default=list)
    review_threshold = Column(Float, default=0.70)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    datasets = relationship("Dataset", back_populates="intent")
    curation_runs = relationship("CurationRun", back_populates="intent")


class CurationPolicy(Base):
    __tablename__ = "curation_policies"

    id = Column(String(100), primary_key=True)  # slug identifier (e.g. merseta_ofo_relevance) or UUID
    name = Column(String(255), nullable=False)
    version = Column(String(50), default="1.0.0")
    description = Column(Text, nullable=True)
    dimensions = Column(JSON, default=dict)  # dimension settings {occupational_relevance: required, ...}
    rules = Column(JSON, default=list)  # list of {id, weight, description, condition}
    include_threshold = Column(Float, default=0.85)
    review_threshold = Column(Float, default=0.55)
    exclude_threshold = Column(Float, default=0.55)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    datasets = relationship("Dataset", back_populates="policy")
    curation_runs = relationship("CurationRun", back_populates="policy")


class CurationRun(Base):
    __tablename__ = "curation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    intent_id = Column(String(36), ForeignKey("dataset_intents.id", ondelete="SET NULL"), nullable=True, index=True)
    policy_id = Column(String(100), ForeignKey("curation_policies.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="queued", index=True)  # queued, running, completed, failed
    progress = Column(Integer, default=0)
    total_records = Column(Integer, default=0)
    included_count = Column(Integer, default=0)
    excluded_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    engine_version = Column(String(50), default="2.2.0")
    ruleset_version = Column(String(50), default="2024.1")
    manifest = Column(JSON, default=dict)  # Complete Curation Manifest for reproducibility
    metrics = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    dataset = relationship("Dataset", back_populates="curation_runs")
    intent = relationship("DatasetIntent", back_populates="curation_runs")
    policy = relationship("CurationPolicy", back_populates="curation_runs")
    decisions = relationship("CurationDecision", back_populates="run", cascade="all, delete-orphan")


class CurationDecision(Base):
    __tablename__ = "curation_decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    record_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("curation_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    decision = Column(String(50), nullable=False, index=True)  # INCLUDE, EXCLUDE, REVIEW
    confidence = Column(Float, default=1.0)
    multi_confidence = Column(JSON, default=dict)  # {extraction, normalization, validation, curation, overall}
    primary_claim = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    why_not = Column(Text, nullable=True)  # Structured domain rationale for exclusion
    decision_method = Column(String(100), default="DETERMINISTIC_RULES")  # DETERMINISTIC_RULES, TAXONOMY_EVIDENCE, LLM_ASSISTED_BORDERLINE, HUMAN_OVERRIDE
    uncertainties = Column(JSON, default=list)
    derived_fields = Column(JSON, default=dict)  # {derived_chamber, derived_relevance, ...}
    explanation_contract = Column(JSON, default=dict)  # {decision, confidence, confidence_basis, basis, conflicts, method, requires_review, why_not}
    conflict_ids = Column(JSON, default=list)
    model_used = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    record = relationship("Record", back_populates="curation_decision_rel")
    run = relationship("CurationRun", back_populates="decisions")
    evidence_items = relationship("EvidenceItem", back_populates="decision_rel", cascade="all, delete-orphan")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    record_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    decision_id = Column(String(36), ForeignKey("curation_decisions.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_type = Column(String(50), nullable=False, index=True)  # SOURCE_FACT, DERIVED_CLASSIFICATION, RULE_INFERENCE, SEMANTIC_INFERENCE, LLM_INFERENCE, HUMAN_DECISION
    document_id = Column(String(36), nullable=True, index=True)
    document_name = Column(String(255), nullable=True)
    page_number = Column(Integer, nullable=True)
    table_index = Column(Integer, nullable=True)
    row_index = Column(Integer, nullable=True)
    cell_key = Column(String(100), nullable=True)
    source_text = Column(Text, nullable=True)
    observed_source_value = Column(Text, nullable=True)
    relation_nature = Column("relationship", String(255), nullable=True)  # belongs_to_unit_group, technical_craft_skill, enterprise_employment
    interpretation = Column(Text, nullable=True)  # Meaning of fact within dataset intent
    strength = Column(String(50), default="STRONG")  # STRONG, MEDIUM, WEAK
    is_inherited = Column(Boolean, default=False)
    inherited_from = Column(String(100), nullable=True)
    claim = Column(Text, nullable=False)
    rule_id = Column(String(100), nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    record = relationship("Record", back_populates="evidence_items")
    decision_rel = relationship("CurationDecision", back_populates="evidence_items")


class DecisionLedger(Base):
    __tablename__ = "decision_ledger"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    record_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=False, index=True)  # EXTRACTION, NORMALIZATION, CURATION, CLASSIFICATION, VALIDATION, HUMAN_REVIEW
    field_name = Column(String(100), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    decision = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    actor = Column(String(50), default="system")  # rule, llm, user
    actor_id = Column(String(100), default="system")
    metadata_snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    record = relationship("Record", back_populates="ledger_entries")


class ClassificationNode(Base):
    __tablename__ = "classification_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    framework = Column(String(50), default="OFO", index=True)  # OFO, ISCO, SAQA, etc.
    code = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    level = Column(String(50), nullable=False, index=True)  # major, sub_major, minor, unit, occupation
    parent_code = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)


class SemanticRelationship(Base):
    __tablename__ = "semantic_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_entity_type = Column(String(50), nullable=False, index=True)  # occupation, qualification, skill
    source_entity_id = Column(String(100), nullable=False, index=True)
    target_entity_type = Column(String(50), nullable=False, index=True)  # sector, chamber, skill, qualification
    target_entity_id = Column(String(100), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, index=True)  # belongs_to, related_to_chamber, requires_skill, offered_by
    confidence = Column(Float, default=1.0)
    evidence_claim = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class SourceConflict(Base):
    __tablename__ = "source_conflicts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    record_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=True, index=True)
    conflict_type = Column(String(50), nullable=False)  # value_mismatch, classification_conflict, duplicate_conflict
    source_a = Column(JSON, nullable=False)  # {document_id, document_name, page, value}
    source_b = Column(JSON, nullable=False)  # {document_id, document_name, page, value}
    field_name = Column(String(100), nullable=True)
    claims = Column(JSON, default=list)  # List of conflicting claims
    severity = Column(String(50), default="high")  # critical, high, medium
    recommended_action = Column(Text, nullable=True)  # ROUTE_TO_HUMAN_REVIEW, KEEP_SOURCE_A, etc.
    resolution_status = Column(String(50), default="UNRESOLVED", index=True)  # UNRESOLVED, HUMAN_RESOLVED, SOURCE_CONFIRMED
    resolved_value = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label = Column(String(50), nullable=False)  # v1.0, v1.1, v2.0
    status = Column(String(50), default="draft", index=True)  # draft, processing, review, approved, published, archived
    record_count = Column(Integer, default=0)
    included_count = Column(Integer, default=0)
    excluded_count = Column(Integer, default=0)
    quality_score = Column(Float, default=100.0)
    quality_dimensions = Column(JSON, default=dict)
    pipeline_version = Column(String(50), default="2.1.0")
    created_by = Column(String(100), default="System")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
