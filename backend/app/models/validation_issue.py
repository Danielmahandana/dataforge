import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    record_id = Column(String(36), ForeignKey("records.id", ondelete="CASCADE"), nullable=True, index=True)
    row_index = Column(Integer, nullable=True, index=True)
    column_name = Column(String(100), nullable=True, index=True)
    rule_name = Column(String(100), nullable=False)
    severity = Column(String(20), default="error", index=True)  # error, warning, info
    message = Column(Text, nullable=False)
    raw_value = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    dataset = relationship("Dataset", back_populates="validation_issues")
    record = relationship("Record", back_populates="validation_issues")
