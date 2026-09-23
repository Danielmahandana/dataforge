from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.validation_issue import ValidationIssue
from backend.app.models.review import ReviewAudit
from backend.app.schemas.validation import (
    ValidationSummaryResponse,
    ValidationIssueResponse,
    ValidationResolveRequest,
)

router = APIRouter(prefix="/validation", tags=["Validation"])

@router.get("/datasets/{dataset_id}", response_model=ValidationSummaryResponse)
def get_dataset_validation(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    issues = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.dataset_id == dataset_id)
        .order_by(ValidationIssue.row_index.asc())
        .all()
    )

    issues_by_severity = {"error": 0, "warning": 0, "info": 0}
    issues_by_column = {}

    for iss in issues:
        if not iss.is_resolved:
            sev = iss.severity.lower()
            issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1
            if iss.column_name:
                issues_by_column[iss.column_name] = issues_by_column.get(iss.column_name, 0) + 1

    return ValidationSummaryResponse(
        dataset_id=dataset.id,
        quality_score=dataset.quality_score,
        total_records=dataset.record_count,
        valid_records=dataset.valid_record_count,
        warning_records=dataset.warning_record_count,
        error_records=dataset.error_record_count,
        issues_by_severity=issues_by_severity,
        issues_by_column=issues_by_column,
        issues=issues,
    )

@router.patch("/issues/{issue_id}/resolve", response_model=ValidationIssueResponse)
def resolve_validation_issue(
    issue_id: str,
    payload: ValidationResolveRequest,
    db: Session = Depends(get_db),
):
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found")

    issue.is_resolved = payload.is_resolved
    issue.resolved_by = payload.resolved_by or "Researcher"
    issue.resolution_comment = payload.resolution_comment

    # If corrected_value provided and issue has record_id & column_name, apply fix
    if payload.corrected_value is not None and issue.record_id and issue.column_name:
        record = db.query(Record).filter(Record.id == issue.record_id).first()
        if record:
            old_val = record.data.get(issue.column_name)
            record.data = {**record.data, issue.column_name: payload.corrected_value}
            record.status = "human_reviewed"

            audit = ReviewAudit(
                dataset_id=issue.dataset_id,
                record_id=record.id,
                action="resolve_issue",
                field_name=issue.column_name,
                old_value=str(old_val),
                new_value=payload.corrected_value,
                reason=f"Resolved issue '{issue.rule_name}': {payload.resolution_comment or ''}",
                reviewed_by=payload.resolved_by or "Researcher",
            )
            db.add(audit)

    db.commit()
    db.refresh(issue)
    return issue
