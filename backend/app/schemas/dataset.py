from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ColumnDefinition(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: Optional[str] = None

class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema_name: Optional[str] = "generic"

class DatasetCreate(DatasetBase):
    project_id: str
    document_id: Optional[str] = None
    schema_columns: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class DatasetResponse(DatasetBase):
    id: str
    project_id: str
    document_id: Optional[str] = None
    schema_columns: List[Dict[str, Any]]
    record_count: int
    valid_record_count: int
    warning_record_count: int
    error_record_count: int
    quality_score: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
