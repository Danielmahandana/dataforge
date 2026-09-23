from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.activity import ActivityLog
from backend.app.schemas.activity import ActivityResponse

router = APIRouter(prefix="/activity", tags=["Activity"])

@router.get("", response_model=List[ActivityResponse])
def list_activity(
    project_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ActivityLog)
    if project_id:
        query = query.filter(ActivityLog.project_id == project_id)
    return query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
