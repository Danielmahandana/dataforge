from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ProvenanceInfo(BaseModel):
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    table_index: Optional[int] = None
    bounding_box: Optional[List[float]] = None
    method: Optional[str] = None

class RecordBase(BaseModel):
    row_index: int
    data: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    confidence_score: Optional[float] = 1.0
    provenance: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: Optional[str] = "valid"
    review_notes: Optional[str] = None

class RecordCreate(RecordBase):
    dataset_id: str

class RecordUpdate(BaseModel):
    data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    review_notes: Optional[str] = None

class RecordResponse(RecordBase):
    id: str
    dataset_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecordListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    records: List[RecordResponse]
