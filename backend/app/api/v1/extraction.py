import uuid
import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, SessionLocal
from backend.app.models.document import Document
from backend.app.models.project import Project
from backend.app.models.extraction_job import ExtractionJob
from backend.app.models.activity import ActivityLog
from backend.app.schemas.extraction import ExtractionJobCreate, ExtractionJobResponse
from backend.app.pipeline.engine import PipelineEngine

router = APIRouter(prefix="/extraction", tags=["Extraction"])

def run_extraction_worker(job_id: str, document_ids: List[str], pipeline_type: str, parameters: dict, target_dataset_name: Optional[str]):
    db = SessionLocal()
    try:
        PipelineEngine.run_pipeline(
            db=db,
            job_id=job_id,
            document_ids=document_ids,
            pipeline_type=pipeline_type,
            parameters=parameters,
            target_dataset_name=target_dataset_name,
        )
    finally:
        db.close()

@router.get("/jobs", response_model=List[ExtractionJobResponse])
def list_jobs(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ExtractionJob)
    if project_id:
        query = query.filter(ExtractionJob.project_id == project_id)
    return query.order_by(ExtractionJob.created_at.desc()).all()

@router.post("/jobs", response_model=ExtractionJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_extraction_job(
    payload: ExtractionJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = db.query(Document).filter(Document.id.in_(payload.document_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="No valid documents selected")

    job_id = str(uuid.uuid4())
    job = ExtractionJob(
        id=job_id,
        project_id=payload.project_id,
        document_id=docs[0].id,
        pipeline_type=payload.pipeline_type,
        status="pending",
        parameters=payload.parameters or {},
        progress=0,
        metrics={},
    )
    db.add(job)

    activity = ActivityLog(
        project_id=payload.project_id,
        entity_type="job",
        entity_id=job_id,
        action="extracted",
        description=f"Queued extraction job for {len(docs)} document(s) using {payload.pipeline_type} pipeline.",
        user="Researcher",
    )
    db.add(activity)
    db.commit()
    db.refresh(job)

    # Launch worker in background thread (reliable in local dev and production)
    background_tasks.add_task(
        run_extraction_worker,
        job_id=job.id,
        document_ids=payload.document_ids,
        pipeline_type=payload.pipeline_type,
        parameters=payload.parameters or {},
        target_dataset_name=payload.target_dataset_name,
    )

    return job

@router.get("/jobs/{job_id}", response_model=ExtractionJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    return job
