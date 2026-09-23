from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ExtractionJobCreate(BaseModel):
    project_id: str
    document_ids: List[str] = Field(..., min_length=1)
    pipeline_type: str = "auto"  # qualifications, occupations, codebook, pdf_tables, auto
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    target_dataset_name: Optional[str] = None

class ExtractionJobResponse(BaseModel):
    id: str
    project_id: str
    document_id: str
    dataset_id: Optional[str] = None
    pipeline_type: str
    status: str
    parameters: Dict[str, Any]
    progress: int
    metrics: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
