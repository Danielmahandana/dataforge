import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    file_hash = Column(String(64), nullable=True, index=True)
    mime_type = Column(String(100), default="application/pdf")
    page_count = Column(Integer, default=0)
    doc_type = Column(String(50), default="unclassified", index=True)  # qualifications, occupations, codebook, general_table, unclassified
    doc_metadata = Column(JSON, default=dict)  # extracted author, title, creation_date, text_layer, scan_quality, page_dims
    status = Column(String(50), default="uploaded", index=True)  # uploaded, inspected, processing, extracted, failed
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="documents")
    jobs = relationship("ExtractionJob", back_populates="document", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="document")
