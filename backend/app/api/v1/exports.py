import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.activity import ActivityLog
from backend.app.schemas.export import ExportRequest, ExportResponse
from backend.app.pipeline.exporter import DatasetExporter
from backend.app.storage.local import storage_manager

router = APIRouter(tags=["Exports"])

@router.post("/datasets/{dataset_id}/export", response_model=ExportResponse)
def export_dataset(
    dataset_id: str,
    payload: ExportRequest,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    query = db.query(Record).filter(Record.dataset_id == dataset_id)
    if payload.only_valid_records:
        query = query.filter(Record.status.in_(["valid", "human_reviewed"]))

    records = query.order_by(Record.row_index.asc()).all()

    record_dicts = [
        {
            "data": r.data,
            "raw_data": r.raw_data,
            "provenance": r.provenance,
            "confidence_score": r.confidence_score,
            "status": r.status,
        }
        for r in records
    ]

    export_bytes = DatasetExporter.export(
        records=record_dicts,
        format=payload.format,
        include_provenance=payload.include_provenance,
        selected_columns=payload.selected_columns,
    )

    clean_name = re.sub(r"[^\w\-_\.]", "_", dataset.name).strip("_")
    fmt = payload.format.lower().strip()
    ext = "xlsx" if fmt in ["xlsx", "excel"] else fmt
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

@router.get("/exports/download/{filename}")
def download_export_file(filename: str):
    target_path = storage_manager.exports_dir / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
