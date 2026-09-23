import os
import shutil
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.project import Project
from backend.app.models.document import Document
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.validation_issue import ValidationIssue
from backend.app.models.review import ReviewAudit
from backend.app.models.extraction_job import ExtractionJob
from backend.app.models.activity import ActivityLog
from backend.app.config import settings

logger = logging.getLogger("dataforge.api.system")

router = APIRouter(prefix="/system", tags=["System Maintenance"])

@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_system(db: Session = Depends(get_db)):
    """
    Completely resets the Darkroom DataForge platform for a fresh start.
    Clears all database tables (projects, documents, datasets, records, audit logs)
    and removes all uploaded/generated storage files.
    """
    try:
        logger.warning("Initiating full platform system reset...")

        # 1. Truncate / delete all database records in reverse dependency order
        db.query(ValidationIssue).delete()
        db.query(ReviewAudit).delete()
        db.query(Record).delete()
        db.query(Dataset).delete()
        db.query(Document).delete()
        db.query(ExtractionJob).delete()
        db.query(ActivityLog).delete()
        db.query(Project).delete()
        db.commit()

        # 2. Clean up storage directories
        storage_dirs = [
            settings.uploads_path,
            settings.exports_path,
            settings.temp_path,
            settings.raw_path,
            settings.processed_path,
        ]
        for dir_path in storage_dirs:
            if dir_path.exists():
                for item in dir_path.iterdir():
                    try:
                        if item.is_file() or item.is_symlink():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        logger.warning(f"Could not delete storage file {item}: {e}")
            else:
                dir_path.mkdir(parents=True, exist_ok=True)

        logger.info("System reset complete. All databases and storage cleared.")

        return {
            "status": "success",
            "message": "Platform reset successfully. All projects, documents, datasets, and storage files have been cleared for a fresh start."
        }

    except Exception as e:
        logger.exception("Failed to reset system")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset system: {str(e)}"
        )
