from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DocumentBase(BaseModel):
    project_id: str
    doc_type: Optional[str] = "unclassified"

class DocumentUpdate(BaseModel):
    doc_type: Optional[str] = None
    status: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    original_name: str
    file_path: str
    file_size: int
    file_hash: Optional[str] = None
    mime_type: str
    page_count: int
    doc_type: str
    doc_metadata: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentInspectResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    doc_type: str
    doc_metadata: Dict[str, Any]
    pages_sample: List[Dict[str, Any]]
    detected_tables_count: int
    has_text_layer: bool
