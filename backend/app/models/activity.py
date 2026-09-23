import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # project, document, job, dataset, record
    entity_id = Column(String(36), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)  # created, updated, deleted, extracted, validated, reviewed, exported
    description = Column(Text, nullable=False)
    user = Column(String(100), default="Researcher")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
