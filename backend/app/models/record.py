import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Record(Base):
    __tablename__ = "records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False, index=True)
    data = Column(JSON, nullable=False, default=dict)  # normalized key-value data
    raw_data = Column(JSON, nullable=True, default=dict)  # raw un-normalized values
    derived_data = Column(JSON, nullable=True, default=dict)  # derived sector/chamber/classification fields
    confidence_score = Column(Float, default=0.85)
    multi_confidence = Column(JSON, default=lambda: {
        "extraction": 0.90,
        "normalization": 0.90,
        "validation": 1.0,
        "curation": None,
        "overall": 0.85
    })
    source_table = Column(String(255), nullable=True)  # e.g. "Table 4: The final list of OIHD"
    source_section = Column(String(255), nullable=True)  # e.g. "PART 5: Consolidation of Evidence"
    source_row = Column(Integer, nullable=True)
    field_authorities = Column(JSON, default=dict)  # {field_name: "SOURCE_FACT" | "DERIVED_VALUE" | "INFERENCE"}
    provenance = Column(JSON, default=dict)  # {document_id, document_name, page_number, table_index, bbox, method}
    status = Column(String(50), default="valid", index=True)  # valid, warning, error, human_reviewed
    curation_decision = Column(String(50), default="unprocessed", index=True)  # unprocessed, include, exclude, review
    curation_reason = Column(Text, nullable=True)
    duplicate_status = Column(String(50), default="none")  # none, exact, structural, semantic_candidate
    duplicate_of_id = Column(String(36), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    def __init__(self, **kwargs):
        if "multi_confidence" not in kwargs or kwargs["multi_confidence"] is None:
            kwargs["multi_confidence"] = {
                "extraction": kwargs.get("confidence_score", 0.90),
                "normalization": 0.90,
                "validation": 1.0,
                "curation": None,
                "overall": kwargs.get("confidence_score", 0.85),
            }
        super().__init__(**kwargs)

    @property
    def curation_confidence(self):
        if self.multi_confidence and isinstance(self.multi_confidence, dict):
            return self.multi_confidence.get("curation")
        return None

    # Relationships
    dataset = relationship("Dataset", back_populates="records")
    validation_issues = relationship("ValidationIssue", back_populates="record", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="record", cascade="all, delete-orphan")
    curation_decision_rel = relationship("CurationDecision", back_populates="record", cascade="all, delete-orphan", uselist=False)
    ledger_entries = relationship("DecisionLedger", back_populates="record", cascade="all, delete-orphan")
