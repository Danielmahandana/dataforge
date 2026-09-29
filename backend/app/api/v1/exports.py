import re
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.document import Document
from backend.app.models.activity import ActivityLog
from backend.app.schemas.export import ExportRequest, ExportResponse, DomainKnowledgeResponse
from backend.app.pipeline.exporter import DatasetExporter
from backend.app.knowledge.domain_knowledge_generator import DomainKnowledgeGenerator
from backend.app.storage.local import storage_manager

router = APIRouter(tags=["Exports"])

@router.post("/datasets/{dataset_id}/export", response_model=ExportResponse)
def export_dataset(
    dataset_id: str,
    payload: ExportRequest,
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    dataset_query = db.query(Dataset).filter(Dataset.id == dataset_id)
    if project_id:
        dataset_query = dataset_query.filter(Dataset.project_id == project_id)
    dataset = dataset_query.first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or does not belong to specified project")

    query = db.query(Record).filter(Record.dataset_id == dataset_id)
    if payload.only_valid_records:
        query = query.filter(Record.status.in_(["valid", "human_reviewed"]))
    if payload.curation_filter:
        query = query.filter(Record.curation_decision == payload.curation_filter.upper())

    records = query.order_by(Record.row_index.asc()).all()

    record_dicts = [
        {
            "data": r.data,
            "raw_data": r.raw_data,
            "provenance": r.provenance,
            "confidence_score": r.confidence_score,
            "status": r.status,
            "curation_decision": r.curation_decision,
            "curation_reason": r.curation_reason,
            "multi_confidence": r.multi_confidence,
            "derived_data": r.derived_data,
        }
        for r in records
    ]

    export_bytes = DatasetExporter.export(
        records=record_dicts,
        format=payload.format,
        include_provenance=payload.include_provenance,
        include_curation=payload.include_curation,
        selected_columns=payload.selected_columns,
    )

    clean_name = re.sub(r"[^\w\-_\.]", "_", dataset.name).strip("_")
    fmt = payload.format.lower().strip()
    ext = "xlsx" if fmt in ["xlsx", "excel"] else fmt

    # Optional Domain Knowledge Text Artifact & Download Bundle
    if payload.include_domain_knowledge:
        document = None
        if dataset.document_id:
            document = db.query(Document).filter(Document.id == dataset.document_id).first()

        artifact = DomainKnowledgeGenerator.generate(
            dataset=dataset,
            records=records,
            document=document,
        )

        # Save standalone domain knowledge text file
        storage_manager.save_export_file(artifact.filename, artifact.content.encode("utf-8"))

        # Package into ZIP bundle
        dataset_in_bundle_name = f"{clean_name}.{ext}"
        bundle_bytes = DatasetExporter.create_export_bundle(
            dataset_bytes=export_bytes,
            dataset_filename=dataset_in_bundle_name,
            knowledge_text=artifact.content,
            knowledge_filename=artifact.filename,
        )

        zip_filename = f"{clean_name}_Export_{dataset.id[:8]}.zip"
        storage_manager.save_export_file(zip_filename, bundle_bytes)

        activity = ActivityLog(
            project_id=dataset.project_id,
            entity_type="dataset",
            entity_id=dataset.id,
            action="exported",
            description=f"Exported dataset '{dataset.name}' with Domain Knowledge Bundle ({fmt.upper()} + .TXT) ({len(records)} records).",
            user="Researcher",
            details={
                "format": "zip",
                "filename": zip_filename,
                "bytes": len(bundle_bytes),
                "knowledge_artifact": artifact.filename,
                "knowledge_hash": artifact.content_hash,
            },
        )
        db.add(activity)
        db.commit()

        return ExportResponse(
            download_url=f"/api/v1/exports/download/{zip_filename}",
            filename=zip_filename,
            format="zip",
            record_count=len(records),
            file_size_bytes=len(bundle_bytes),
            domain_knowledge_filename=artifact.filename,
            domain_knowledge_hash=artifact.content_hash,
        )

    # Standard direct export (no bundle)
    export_filename = f"{clean_name}_{dataset.id[:8]}.{ext}"
    storage_manager.save_export_file(export_filename, export_bytes)

    activity = ActivityLog(
        project_id=dataset.project_id,
        entity_type="dataset",
        entity_id=dataset.id,
        action="exported",
        description=f"Exported dataset '{dataset.name}' to {fmt.upper()} ({len(records)} records).",
        user="Researcher",
        details={"format": fmt, "filename": export_filename, "bytes": len(export_bytes)},
    )
    db.add(activity)
    db.commit()

    return ExportResponse(
        download_url=f"/api/v1/exports/download/{export_filename}",
        filename=export_filename,
        format=fmt,
        record_count=len(records),
        file_size_bytes=len(export_bytes),
    )


@router.get("/datasets/{dataset_id}/domain-knowledge")
def get_dataset_domain_knowledge(
    dataset_id: str,
    preview: bool = Query(False),
    download: bool = Query(False),
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Generates and returns the domain knowledge text artifact for preview or download."""
    dataset_query = db.query(Dataset).filter(Dataset.id == dataset_id)
    if project_id:
        dataset_query = dataset_query.filter(Dataset.project_id == project_id)
    dataset = dataset_query.first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or does not belong to specified project")

    records = db.query(Record).filter(Record.dataset_id == dataset_id).order_by(Record.row_index.asc()).all()
    document = None
    if dataset.document_id:
        document = db.query(Document).filter(Document.id == dataset.document_id).first()

    artifact = DomainKnowledgeGenerator.generate(
        dataset=dataset,
        records=records,
        document=document,
    )

    # Save artifact to export directory
    storage_manager.save_export_file(artifact.filename, artifact.content.encode("utf-8"))

    if download:
        target_path = storage_manager.exports_dir / artifact.filename
        return FileResponse(
            path=target_path,
            media_type="text/plain; charset=utf-8",
            filename=artifact.filename,
        )

    return DomainKnowledgeResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        filename=artifact.filename,
        content=artifact.content,
        content_hash=artifact.content_hash,
        record_count=artifact.record_count,
        generator_version=artifact.generator_version,
        generated_at=artifact.generated_at,
        download_url=f"/api/v1/exports/download/{artifact.filename}",
    )


@router.get("/exports/download/{filename}")
def download_export_file(filename: str):
    target_path = storage_manager.exports_dir / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip": "application/zip",
        "txt": "text/plain; charset=utf-8",
    }
    ext = target_path.suffix.lstrip(".").lower()
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=target_path,
        media_type=media_type,
        filename=filename,
    )



@router.post("/datasets/{dataset_id}/relational-export")
def export_relational_package(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Generates Palantir-style relational tables (qualifications, colleges, qualification_colleges, dspp, metadata artifacts)."""
    from backend.app.pipeline.relational_decomposer import RelationalDecomposer
    from backend.app.models.document import Document

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = db.query(Record).filter(Record.dataset_id == dataset_id).order_by(Record.row_index.asc()).all()
    record_dicts = [r.data for r in records if r.data]

    # Run Relational Decomposition
    relational = RelationalDecomposer.decompose_tvet_qualifications(record_dicts)

    # Save artifacts to exports dir
    clean_name = re.sub(r"[^\w\-_\.]", "_", dataset.name).strip("_")
    
    quals_bytes = DatasetExporter.export_raw_dicts(relational["qualifications"])
    colleges_bytes = DatasetExporter.export_raw_dicts(relational["colleges"])
    junction_bytes = DatasetExporter.export_raw_dicts(relational["qualification_colleges"])
    dspp_bytes = DatasetExporter.export_raw_dicts(relational["dspp_centres_of_specialisation"])
    review_bytes = DatasetExporter.export_raw_dicts(relational["review_required"])
    data_dict_bytes = DatasetExporter.generate_data_dictionary(dataset.schema_columns or [])

    quals_fn = f"{clean_name}_qualifications.csv"
    colleges_fn = f"{clean_name}_colleges.csv"
    junction_fn = f"{clean_name}_qualification_colleges.csv"
    dspp_fn = f"{clean_name}_dspp_centres.csv"
    review_fn = f"{clean_name}_review_required.csv"
    dict_fn = f"{clean_name}_data_dictionary.csv"

    storage_manager.save_export_file(quals_fn, quals_bytes)
    storage_manager.save_export_file(colleges_fn, colleges_bytes)
    storage_manager.save_export_file(junction_fn, junction_bytes)
    storage_manager.save_export_file(dspp_fn, dspp_bytes)
    storage_manager.save_export_file(review_fn, review_bytes)
    storage_manager.save_export_file(dict_fn, data_dict_bytes)

    return {
        "status": "success",
        "dataset_id": dataset.id,
        "tables": {
            "qualifications": {"filename": quals_fn, "records": len(relational["qualifications"]), "download_url": f"/api/v1/exports/download/{quals_fn}"},
            "colleges": {"filename": colleges_fn, "records": len(relational["colleges"]), "download_url": f"/api/v1/exports/download/{colleges_fn}"},
            "qualification_colleges": {"filename": junction_fn, "records": len(relational["qualification_colleges"]), "download_url": f"/api/v1/exports/download/{junction_fn}"},
            "dspp_centres_of_specialisation": {"filename": dspp_fn, "records": len(relational["dspp_centres_of_specialisation"]), "download_url": f"/api/v1/exports/download/{dspp_fn}"},
            "review_required": {"filename": review_fn, "records": len(relational["review_required"]), "download_url": f"/api/v1/exports/download/{review_fn}"},
            "data_dictionary": {"filename": dict_fn, "records": len(dataset.schema_columns or []), "download_url": f"/api/v1/exports/download/{dict_fn}"},
        }
    }
