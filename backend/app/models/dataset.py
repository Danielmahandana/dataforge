import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    intent_id = Column(String(36), ForeignKey("dataset_intents.id", ondelete="SET NULL"), nullable=True, index=True)
    policy_id = Column(String(100), ForeignKey("curation_policies.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version_label = Column(String(50), default="v1.0")
    schema_name = Column(String(100), default="generic", index=True)  # qualifications, occupations, codebook, generic
    schema_columns = Column(JSON, default=list)  # list of {name, type, required, description}
    record_count = Column(Integer, default=0)
    valid_record_count = Column(Integer, default=0)
    warning_record_count = Column(Integer, default=0)
    error_record_count = Column(Integer, default=0)
    quality_score = Column(Float, default=100.0)  # 0.0 - 100.0 (overall composite)
    quality_dimensions = Column(JSON, default=lambda: {
        "extraction": 100.0,
        "structural": 100.0,
        "normalization": 100.0,
        "validation": 100.0,
        "completeness": 100.0,
        "consistency": 100.0,
        "curation": 100.0,
        "provenance": 100.0
    })
    quality_gates_status = Column(JSON, default=lambda: {
        "extraction_gate": "passed",
        "structural_gate": "passed",
        "normalization_gate": "passed",
        "curation_gate": "pending",
        "validation_gate": "passed",
        "review_gate": "pending",
        "export_gate": "ready"
    })
    curation_summary = Column(JSON, default=lambda: {
        "included": 0,
        "excluded": 0,
        "review_required": 0,
        "unprocessed": 0
    })
    status = Column(String(50), default="raw", index=True)  # raw, normalized, validated, reviewed, published
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="datasets")
    document = relationship("Document", back_populates="datasets")
    records = relationship("Record", back_populates="dataset", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="dataset", cascade="all, delete-orphan")
    jobs = relationship("ExtractionJob", back_populates="dataset")
    intent = relationship("DatasetIntent", back_populates="datasets")
    policy = relationship("CurationPolicy", back_populates="datasets")
    curation_runs = relationship("CurationRun", back_populates="dataset", cascade="all, delete-orphan")
