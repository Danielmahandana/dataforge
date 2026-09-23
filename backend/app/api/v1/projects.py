from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models.project import Project
from backend.app.models.document import Document
from backend.app.models.dataset import Dataset
from backend.app.models.activity import ActivityLog
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    results = []
    for p in projects:
        doc_count = db.query(func.count(Document.id)).filter(Document.project_id == p.id).scalar() or 0
        ds_count = db.query(func.count(Dataset.id)).filter(Dataset.project_id == p.id).scalar() or 0
        p_dict = {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "tags": p.tags or [],
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "document_count": doc_count,
            "dataset_count": ds_count,
        }
        results.append(ProjectResponse(**p_dict))
    return results

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=payload.name,
        description=payload.description,
        tags=payload.tags,
    )
    db.add(project)
    db.flush()

    activity = ActivityLog(
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="created",
        description=f"Created project '{project.name}'.",
        user="Researcher",
    )
    db.add(activity)
    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=0,
        dataset_count=0,
    )

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    doc_count = db.query(func.count(Document.id)).filter(Document.project_id == project.id).scalar() or 0
    ds_count = db.query(func.count(Dataset.id)).filter(Dataset.project_id == project.id).scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=doc_count,
        dataset_count=ds_count,
    )

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.tags is not None:
        project.tags = payload.tags

    db.commit()
    db.refresh(project)

    doc_count = db.query(func.count(Document.id)).filter(Document.project_id == project.id).scalar() or 0
    ds_count = db.query(func.count(Dataset.id)).filter(Dataset.project_id == project.id).scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=doc_count,
        dataset_count=ds_count,
    )

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return None
