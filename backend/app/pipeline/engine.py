import time
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.validation_issue import ValidationIssue
from backend.app.models.extraction_job import ExtractionJob
from backend.app.models.activity import ActivityLog
from backend.app.extractors import (
    QualificationsExtractor,
    OccupationsExtractor,
    CodebookExtractor,
    PdfTablesExtractor,
    LLMExtractor,
    BaseExtractor,
)
from backend.app.pipeline.normalizer import Normalizer
from backend.app.pipeline.schema_detector import SchemaDetector
from backend.app.pipeline.validator import Validator
from backend.app.pipeline.table_healer import TableHealer

logger = logging.getLogger("dataforge.pipeline")

class PipelineEngine:
    """Orchestrates document extraction, normalization, validation, and dataset generation."""

    @classmethod
    def select_extractor(cls, doc_type: str, pipeline_type: str) -> BaseExtractor:
        target = pipeline_type if pipeline_type != "auto" else doc_type
        target = target.lower()

        if "llm" in target or "ai" in target:
            return LLMExtractor()
        elif "qual" in target or "tvet" in target:
            return QualificationsExtractor()
        elif "occup" in target or "oihd" in target or "ofo" in target:
            return OccupationsExtractor()
        elif "codebook" in target or "qlfs" in target or "survey" in target:
            return CodebookExtractor()
        else:
            return PdfTablesExtractor()

    @classmethod
    def map_table_row_to_schema(
        cls, tab_headers: List[str], row_cells: List[str], col_names: List[str]
    ) -> Dict[str, Any]:
        raw_dict = {col: "" for col in col_names}
        if not tab_headers:
            for c_idx, col_name in enumerate(col_names):
                if c_idx < len(row_cells):
                    raw_dict[col_name] = row_cells[c_idx]
            return raw_dict

        used_targets = set()
        col_mapping = {}

        for idx, h in enumerate(tab_headers):
            if not h:
                continue
            h_str = str(h).strip()
            h_snake = SchemaDetector.to_snake_case(h_str)

            matched_col = None
            for c in col_names:
                if c not in used_targets and (h_snake == c or h_snake.startswith(c) or c.startswith(h_snake)):
                    matched_col = c
                    break

            if not matched_col:
                h_lower = h_str.lower()
                if "saqa" in h_lower:
                    matched_col = next((c for c in col_names if "saqa" in c and c not in used_targets), None)
                elif any(k in h_lower for k in ["sub_frame", "subframe", "nqf sub"]):
                    matched_col = next((c for c in col_names if any(k in c for k in ["sub", "frame"]) and c not in used_targets), None)
                elif any(k in h_lower for k in ["qual", "title", "programme"]) and "sub" not in h_lower:
                    matched_col = next((c for c in col_names if any(k in c for k in ["qual", "title", "prog"]) and c not in used_targets), None)
                elif any(k in h_lower for k in ["number", "code", "curriculum"]) and "saqa" not in h_lower:
                    matched_col = next((c for c in col_names if any(k in c for k in ["number", "code"]) and "saqa" not in c and c not in used_targets), None)
                elif any(k in h_lower for k in ["nsfas", "allowan", "bursary", "fund"]):
                    matched_col = next((c for c in col_names if any(k in c for k in ["nsfas", "allow"]) and c not in used_targets), None)
                elif any(k in h_lower for k in ["college", "campus", "institution", "provider"]):
                    matched_col = next((c for c in col_names if any(k in c for k in ["college", "campus", "inst"]) and c not in used_targets), None)

            if matched_col:
                col_mapping[idx] = matched_col
                used_targets.add(matched_col)

        if len(col_mapping) < 2:
            for c_idx, col_name in enumerate(col_names):
                if c_idx < len(row_cells):
                    raw_dict[col_name] = row_cells[c_idx]
        else:
            for idx, col_name in col_mapping.items():
                if idx < len(row_cells):
                    raw_dict[col_name] = row_cells[idx]
            unmapped_targets = [c for c in col_names if c not in used_targets]
            unmapped_indices = [i for i in range(len(row_cells)) if i not in col_mapping]
            for t_col, s_idx in zip(unmapped_targets, unmapped_indices):
                raw_dict[t_col] = row_cells[s_idx]

        return raw_dict

    @classmethod
    def run_pipeline(
        cls,
        db: Session,
        job_id: str,
        document_ids: List[str],
        pipeline_type: str = "auto",
        parameters: Optional[Dict[str, Any]] = None,
        target_dataset_name: Optional[str] = None,
    ) -> Optional[Dataset]:
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        if not job:
            logger.error(f"Extraction job {job_id} not found.")
            return None

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 10
        db.commit()

        start_time = time.time()
        parameters = parameters or {}
        pages = parameters.get("pages")  # e.g. [1, 2, 3]

        try:
            documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
            if not documents:
                raise ValueError("No valid documents found for extraction.")

            primary_doc = documents[0]
            extractor = cls.select_extractor(primary_doc.doc_type, pipeline_type)

            all_raw_tables = []
            doc_provenance_map = {}

            total_docs = len(documents)
            for idx, doc in enumerate(documents):
                logger.info(f"Processing document {doc.filename} with {extractor.name}...")
                res = extractor.extract(doc.file_path, pages=pages)
                for tab in res.tables:
                    all_raw_tables.append((doc, tab))
                
                # Update progress
                job.progress = 10 + int(40 * (idx + 1) / total_docs)
                db.commit()

            if not all_raw_tables:
                # Try fallback to generic table extractor if specific extractor found 0 tables
                if not isinstance(extractor, PdfTablesExtractor):
                    logger.info("Specialized extractor found 0 tables. Falling back to PdfTablesExtractor.")
                    fallback_extractor = PdfTablesExtractor()
                    for doc in documents:
                        res = fallback_extractor.extract(doc.file_path, pages=pages)
                        for tab in res.tables:
                            all_raw_tables.append((doc, tab))

            if not all_raw_tables:
                # Try AI LLM Extractor fallback if native table detection yielded 0 tables
                logger.info("Native table extractors found 0 tables. Triggering LLMExtractor AI fallback.")
                llm_extractor = LLMExtractor()
                for doc in documents:
                    res = llm_extractor.extract(doc.file_path, pages=pages)
                    for tab in res.tables:
                        all_raw_tables.append((doc, tab))

            if not all_raw_tables:
                raise ValueError("No tabular data or structured records could be detected in the selected document(s).")

            # Table Healing: Header deduplication & multi-line continuation row stitching
            raw_tabs_only = [t for _, t in all_raw_tables]
            healed_tabs = TableHealer.clean_header_repeats(raw_tabs_only)
            healed_tabs = TableHealer.heal_continuation_rows(healed_tabs)

            healed_pairs = []
            for idx, (doc, _) in enumerate(all_raw_tables):
                healed_pairs.append((doc, healed_tabs[idx]))
            all_raw_tables = healed_pairs

            # Determine headers and schema columns
            first_doc, first_table = all_raw_tables[0]
            raw_headers = first_table.headers
            sample_data = first_table.rows[:20]

            schema_columns = SchemaDetector.detect_columns(raw_headers, sample_data)
            col_names = [c["name"] for c in schema_columns]

            # Determine dataset name
            ds_name = target_dataset_name
            if not ds_name:
                base_name = primary_doc.original_name.rsplit(".", 1)[0]
                ds_name = f"{base_name} - {extractor.name.capitalize()} Dataset"

            # Create Dataset entity
            dataset = Dataset(
                project_id=job.project_id,
                document_id=primary_doc.id,
                name=ds_name,
                description=f"Generated via {extractor.name} extraction pipeline from {len(documents)} document(s).",
                schema_name=extractor.name,
                schema_columns=schema_columns,
                status="normalized",
            )
            db.add(dataset)
            db.flush()

            job.dataset_id = dataset.id
            job.progress = 60
            db.commit()

            # Process rows into Records with Normalization, Provenance, and Validation
            created_records = []
            all_issues = []
            row_counter = 0

            error_records_count = 0
            warning_records_count = 0

            for doc, tab in all_raw_tables:
                for row_cells in tab.rows:
                    row_counter += 1
                    # Dynamically pair row cells with column names aligned to table headers
                    raw_dict = cls.map_table_row_to_schema(tab.headers, row_cells, col_names)

                    # Normalization
                    norm_data, raw_data = Normalizer.normalize_record(raw_dict)

                    # Provenance tracking
                    prov = {
                        "document_id": doc.id,
                        "document_name": doc.original_name,
                        "page_number": tab.page_number,
                        "table_index": tab.table_index,
                        "method": tab.extraction_method,
                    }

                    # Validation
                    issues = Validator.validate_record(norm_data, schema_columns, row_counter)
                    rec_status = "valid"
                    has_error = any(i["severity"] == "error" for i in issues)
                    has_warning = any(i["severity"] == "warning" for i in issues)

                    if has_error:
                        rec_status = "error"
                        error_records_count += 1
                    elif has_warning:
                        rec_status = "warning"
                        warning_records_count += 1

                    rec = Record(
                        dataset_id=dataset.id,
                        row_index=row_counter,
                        data=norm_data,
                        raw_data=raw_data,
                        confidence_score=tab.confidence,
                        provenance=prov,
                        status=rec_status,
                    )
                    db.add(rec)
                    db.flush()

                    for issue in issues:
                        v_issue = ValidationIssue(
                            dataset_id=dataset.id,
                            record_id=rec.id,
                            row_index=row_counter,
                            column_name=issue["column_name"],
                            rule_name=issue["rule_name"],
                            severity=issue["severity"],
                            message=issue["message"],
                            raw_value=issue.get("raw_value"),
                        )
                        db.add(v_issue)

            # Calculate metrics
            total_records = row_counter
            valid_records_count = total_records - error_records_count - warning_records_count
            quality_score = Validator.calculate_quality_score(
                total_records, error_records_count, warning_records_count
            )

            dataset.record_count = total_records
            dataset.valid_record_count = valid_records_count
            dataset.warning_record_count = warning_records_count
            dataset.error_record_count = error_records_count
            dataset.quality_score = quality_score
            dataset.status = "validated"

            # Update document status
            for doc in documents:
                doc.status = "extracted"

            # Finish job
            duration_ms = int((time.time() - start_time) * 1000)
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.metrics = {
                "total_documents": len(documents),
                "total_tables": len(all_raw_tables),
                "records_extracted": total_records,
                "valid_records": valid_records_count,
                "errors_count": error_records_count,
                "warnings_count": warning_records_count,
                "quality_score": quality_score,
                "duration_ms": duration_ms,
            }

            # Log activity
            activity = ActivityLog(
                project_id=job.project_id,
                entity_type="dataset",
                entity_id=dataset.id,
                action="extracted",
                description=f"Generated dataset '{dataset.name}' with {total_records} records ({quality_score}% quality).",
                user="Pipeline Engine",
                details=job.metrics,
            )
            db.add(activity)

            db.commit()
            return dataset

        except Exception as e:
            logger.exception("Pipeline execution failed")
            db.rollback()
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return None
