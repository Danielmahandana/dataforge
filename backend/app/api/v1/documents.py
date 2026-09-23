import os
import uuid
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import pymupdf
import pdfplumber

from backend.app.database import get_db
from backend.app.models.document import Document
from backend.app.models.project import Project
from backend.app.models.activity import ActivityLog
from backend.app.schemas.document import DocumentResponse, DocumentUpdate, DocumentInspectResponse
from backend.app.storage.local import storage_manager

router = APIRouter(prefix="/documents", tags=["Documents"])

def classify_document(text: str, filename: str) -> str:
    combined = f"{filename} {text}".lower()
    if any(k in combined for k in ["saqa", "tvet", "occupational qualification", "learning programme", "nqf level"]):
        return "qualifications"
    if any(k in combined for k in ["oihd", "ofo", "occupations in high demand", "occupation code", "unit group"]):
        return "occupations"
    if any(k in combined for k in ["codebook", "qlfs", "survey", "variable label", "questionnaire"]):
        return "codebook"
    return "general_table"

@router.get("", response_model=List[DocumentResponse])
def list_documents(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Document)
    if project_id:
        query = query.filter(Document.project_id == project_id)
    return query.order_by(Document.created_at.desc()).all()

@router.post("/upload", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    project_id: str = Form(...),
    doc_type: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    saved_docs = []

    for file in files:
        doc_id = str(uuid.uuid4())
        file_path, original_name, file_size, file_hash = await storage_manager.save_upload(file, doc_id)

        # Inspect PDF metadata & page count
        page_count = 0
        has_text_layer = False
        first_page_text = ""
        doc_metadata = {}

        try:
            pdf_doc = pymupdf.open(file_path)
            page_count = len(pdf_doc)
            doc_metadata = dict(pdf_doc.metadata or {})
            if page_count > 0:
                first_page_text = pdf_doc[0].get_text("text")[:2000]
                has_text_layer = bool(first_page_text.strip())
            pdf_doc.close()
        except Exception:
            pass

        # Classify document
        inferred_type = doc_type if doc_type and doc_type != "auto" else classify_document(first_page_text, original_name)
        doc_metadata["has_text_layer"] = has_text_layer
        doc_metadata["first_page_preview"] = first_page_text[:400]

        doc = Document(
            id=doc_id,
            project_id=project_id,
            filename=Path(file_path).name,
            original_name=original_name,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            mime_type="application/pdf",
            page_count=page_count,
            doc_type=inferred_type,
            doc_metadata=doc_metadata,
            status="inspected",
        )
        db.add(doc)
        saved_docs.append(doc)

        activity = ActivityLog(
            project_id=project_id,
            entity_type="document",
            entity_id=doc.id,
            action="created",
            description=f"Uploaded document '{original_name}' ({page_count} pages, classified as {inferred_type}).",
            user="Researcher",
        )
        db.add(activity)

    db.commit()
    for doc in saved_docs:
        db.refresh(doc)

    return saved_docs

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/{document_id}/file")
def stream_document_file(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    path = Path(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on storage")

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=doc.original_name,
    )

@router.get("/{document_id}/inspect", response_model=DocumentInspectResponse)
def inspect_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    pages_sample = []
    detected_tables_count = 0
    has_text_layer = False

    try:
        with pdfplumber.open(doc.file_path) as pdf:
            max_sample = min(5, len(pdf.pages))
            for i in range(max_sample):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                detected_tables_count += len(tables)
                if text.strip():
                    has_text_layer = True

                pages_sample.append({
                    "page_number": i + 1,
                    "width": float(page.width),
                    "height": float(page.height),
                    "text_preview": text[:300],
                    "table_count": len(tables),
                })
    except Exception as e:
        pages_sample.append({"error": str(e)})

    return DocumentInspectResponse(
        id=doc.id,
        filename=doc.original_name,
        page_count=doc.page_count,
        doc_type=doc.doc_type,
        doc_metadata=doc.doc_metadata or {},
        pages_sample=pages_sample,
        detected_tables_count=detected_tables_count,
        has_text_layer=has_text_layer,
    )

@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(document_id: str, payload: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if payload.doc_type is not None:
        doc.doc_type = payload.doc_type
    if payload.status is not None:
        doc.status = payload.status
    if payload.doc_metadata is not None:
        doc.doc_metadata = {**(doc.doc_metadata or {}), **payload.doc_metadata}

    db.commit()
    db.refresh(doc)
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_manager.delete_file(doc.file_path)
    db.delete(doc)
    db.commit()
    return None
