from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.review import ReviewAudit
from backend.app.schemas.review import ReviewAuditCreate, ReviewAuditResponse

router = APIRouter(prefix="/review", tags=["Review"])

@router.post("/audit", response_model=ReviewAuditResponse, status_code=status.HTTP_201_CREATED)
def create_review_audit(payload: ReviewAuditCreate, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == payload.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    audit = ReviewAudit(
        dataset_id=record.dataset_id,
        record_id=payload.record_id,
        action=payload.action,
        field_name=payload.field_name,
        old_value=payload.old_value,
        new_value=payload.new_value,
        reason=payload.reason,
        reviewed_by=payload.reviewed_by or "Researcher",
    )
    db.add(audit)

    # Update record status based on action
    if payload.action == "approve_record":
        record.status = "human_reviewed"
    elif payload.action == "reject_record":
        record.status = "error"
    elif payload.action == "flag_record":
        record.status = "warning"

    db.commit()
    db.refresh(audit)
    return audit

@router.get("/datasets/{dataset_id}", response_model=List[ReviewAuditResponse])
def get_dataset_reviews(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    reviews = (
        db.query(ReviewAudit)
        .filter(ReviewAudit.dataset_id == dataset_id)
        .order_by(ReviewAudit.created_at.desc())
        .all()
    )
    return reviews
