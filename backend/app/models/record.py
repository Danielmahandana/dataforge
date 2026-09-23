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
    confidence_score = Column(Float, default=1.0)
    provenance = Column(JSON, default=dict)  # {document_id, document_name, page_number, table_index, bbox, method}
    status = Column(String(50), default="valid", index=True)  # valid, warning, error, human_reviewed
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    dataset = relationship("Dataset", back_populates="records")
    validation_issues = relationship("ValidationIssue", back_populates="record", cascade="all, delete-orphan")
