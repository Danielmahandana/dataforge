from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ValidationIssueResponse(BaseModel):
    id: str
    dataset_id: str
    record_id: Optional[str] = None
    row_index: Optional[int] = None
    column_name: Optional[str] = None
    rule_name: str
    severity: str
    message: str
    raw_value: Optional[str] = None
    is_resolved: bool
    resolved_by: Optional[str] = None
    resolution_comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ValidationResolveRequest(BaseModel):
    is_resolved: bool = True
    resolved_by: Optional[str] = "Researcher"
    resolution_comment: Optional[str] = None
    corrected_value: Optional[str] = None

class ValidationSummaryResponse(BaseModel):
    dataset_id: str
    quality_score: float
    total_records: int
    valid_records: int
    warning_records: int
    error_records: int
    issues_by_severity: dict
    issues_by_column: dict
    issues: List[ValidationIssueResponse]
