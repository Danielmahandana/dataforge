from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models.record import Record
from backend.app.models.dataset import Dataset
from backend.app.models.review import ReviewAudit
from backend.app.schemas.record import RecordResponse, RecordUpdate, RecordListResponse

router = APIRouter(tags=["Records"])

@router.get("/datasets/{dataset_id}/records", response_model=RecordListResponse)
def list_dataset_records(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    query = db.query(Record).filter(Record.dataset_id == dataset_id)

    if status_filter:
        query = query.filter(Record.status == status_filter)

    total = query.count()
    records = query.order_by(Record.row_index.asc()).offset((page - 1) * page_size).limit(page_size).all()

    # If search string provided, filter in-memory if needed
    if search:
        s_lower = search.lower()
        records = [
            r for r in records
            if any(s_lower in str(v).lower() for v in r.data.values())
        ]

    return RecordListResponse(
        total=total,
        page=page,
        page_size=page_size,
        records=records,
    )

@router.get("/records/{record_id}", response_model=RecordResponse)
def get_record(record_id: str, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@router.patch("/records/{record_id}", response_model=RecordResponse)
def update_record(record_id: str, payload: RecordUpdate, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if payload.data is not None:
        has_field_change = False
        for k, new_v in payload.data.items():
            old_v = record.data.get(k)
            if old_v != new_v:
                audit = ReviewAudit(
                    dataset_id=record.dataset_id,
                    record_id=record.id,
                    action="edit_field",
                    field_name=k,
                    old_value=str(old_v),
                    new_value=str(new_v),
                    reason=payload.review_notes or "Manual record edit",
                    reviewed_by="Researcher",
                )
                db.add(audit)
                has_field_change = True

        if not has_field_change:
            audit = ReviewAudit(
                dataset_id=record.dataset_id,
                record_id=record.id,
                action="update_record",
                reason=payload.review_notes or "Manual review update",
                reviewed_by="Researcher",
            )
            db.add(audit)

        record.data = {**record.data, **payload.data}
        record.status = "human_reviewed"

    if payload.status is not None:
        record.status = payload.status
    if payload.review_notes is not None:
        record.review_notes = payload.review_notes

    db.commit()
    db.refresh(record)
    return record

@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: str, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    dataset = db.query(Dataset).filter(Dataset.id == record.dataset_id).first()
    if dataset and dataset.record_count > 0:
        dataset.record_count -= 1

    db.delete(record)
    db.commit()
    return None
