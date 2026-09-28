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

from backend.app.document_intelligence.profiler import DocumentProfiler
from backend.app.document_intelligence.table_reconstructor import TableReconstructor
from backend.app.document_intelligence.section_detector import SectionDetector
from backend.app.curation.quality_engine import QualityEngine
import pdfplumber

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

            # Phase 1: Universal Document Understanding & Dataset Discovery
            doc_profile = None
            target_candidate = None
            is_pdf = primary_doc.file_path.lower().endswith(".pdf")

            if is_pdf:
                try:
                    logger.info(f"Running Document Intelligence Profiler on {primary_doc.original_name}...")
                    doc_profile = DocumentProfiler.profile_document(primary_doc.file_path, primary_doc.id)

                    # Cache profile summary and discovery report on Document
                    primary_doc.doc_metadata = {
                        **(primary_doc.doc_metadata or {}),
                        "profile_summary": {
                            "title": doc_profile.title,
                            "publisher": doc_profile.publisher,
                            "publication_date": doc_profile.publication_date,
                            "document_type": doc_profile.document_type.value,
                            "page_count": doc_profile.page_count,
                            "sections_count": len(doc_profile.sections),
                            "tables_count": len(doc_profile.tables),
                            "candidates_count": len(doc_profile.dataset_candidates),
                            "authoritative_dataset_id": doc_profile.authoritative_dataset_id,
                        },
                    }
                    if doc_profile.discovery_report:
                        primary_doc.doc_metadata["discovery_report"] = doc_profile.discovery_report.model_dump()
                    db.commit()

                    # Resolve Target Candidate
                    req_cand_id = parameters.get("candidate_id") or parameters.get("target_candidate_id")
                    if req_cand_id:
                        target_candidate = next((c for c in doc_profile.dataset_candidates if c.candidate_id == req_cand_id), None)
                    elif doc_profile.authoritative_dataset_id:
                        target_candidate = next((c for c in doc_profile.dataset_candidates if c.candidate_id == doc_profile.authoritative_dataset_id), None)
                    elif doc_profile.dataset_candidates:
                        top_cand = sorted(doc_profile.dataset_candidates, key=lambda c: c.score, reverse=True)[0]
                        if top_cand.score >= 0.75:
                            target_candidate = top_cand

                except Exception as prof_err:
                    logger.warning(f"Document profiler failed or skipped: {prof_err}. Falling back to standard extraction.")

            records_to_create = []  # list of tuples (norm_data, raw_data, confidence, prov, issues)
            schema_columns = []
            col_names = []
            ds_name = target_dataset_name
            ds_schema_name = extractor.name
            ds_description = ""

            # Phase 2: Targeted Reconstruction OR Standard Healed Extraction
            if target_candidate and is_pdf and not pages:
                logger.info(
                    f"Targeting discovered authoritative candidate '{target_candidate.name}' "
                    f"(pages {target_candidate.page_start}–{target_candidate.page_end}, unit={target_candidate.unit_of_observation.value})..."
                )

                candidate_raw_tables = []
                pages_text = []
                with pdfplumber.open(primary_doc.file_path) as pdf:
                    for p_num in range(target_candidate.page_start, target_candidate.page_end + 1):
                        if 1 <= p_num <= len(pdf.pages):
                            p = pdf.pages[p_num - 1]
                            t = p.extract_text() or ""
                            pages_text.append((p_num, t))
                            p_tables = p.extract_tables() or []
                            for t_idx, tab in enumerate(p_tables):
                                if tab and len(tab) > 0:
                                    headers = [str(c).replace("\n", " ").strip() if c else f"Col_{i+1}" for i, c in enumerate(tab[0])]
                                    data_rows = tab[1:] if len(tab) > 1 else tab
                                    candidate_raw_tables.append({
                                        "page_number": p_num,
                                        "table_index": t_idx,
                                        "headers": headers,
                                        "rows": data_rows,
                                    })

                reconstructed = TableReconstructor.reconstruct_table(
                    raw_tables=candidate_raw_tables,
                    target_caption=target_candidate.name,
                    pages_text=pages_text,
                    unit_of_observation=target_candidate.unit_of_observation.value,
                )

                raw_headers = reconstructed.headers
                sample_data = reconstructed.rows[:20]
                schema_columns = SchemaDetector.detect_columns(raw_headers, sample_data)
                col_names = [c["name"] for c in schema_columns]

                if not ds_name:
                    ds_name = target_candidate.name
                ds_schema_name = target_candidate.unit_of_observation.value
                ds_description = (
                    f"Authoritative research dataset '{target_candidate.name}' reconstructed from "
                    f"pages {target_candidate.page_start}–{target_candidate.page_end} of {primary_doc.original_name}. "
                    f"Unit of observation: {target_candidate.unit_of_observation.value}."
                )

                job.progress = 50
                db.commit()

                # Process reconstructed rows
                for r_idx, row_cells in enumerate(reconstructed.rows):
                    row_counter = r_idx + 1
                    raw_dict = cls.map_table_row_to_schema(raw_headers, row_cells, col_names)
                    norm_data, raw_data = Normalizer.normalize_record(raw_dict)

                    prov_info = reconstructed.row_provenance[r_idx] if r_idx < len(reconstructed.row_provenance) else {}
                    source_page = prov_info.get("page_number", target_candidate.page_start)
                    matched_sec = SectionDetector.find_section_for_page(doc_profile.sections, source_page) if doc_profile else None
                    source_section_title = matched_sec.title if matched_sec else None

                    prov = {
                        "document_id": primary_doc.id,
                        "document_name": primary_doc.original_name,
                        "page_number": source_page,
                        "source_table": target_candidate.name,
                        "source_section": source_section_title,
                        "source_row": r_idx + 1,
                        "method": "reconstructed_table",
                    }

                    issues = Validator.validate_record(norm_data, schema_columns, row_counter)
                    records_to_create.append((norm_data, raw_data, reconstructed.confidence, prov, issues))

            else:
                # Fallback to standard multi-table extractor
                all_raw_tables = []
                total_docs = len(documents)
                for idx, doc in enumerate(documents):
                    logger.info(f"Processing document {doc.filename} with {extractor.name}...")
                    res = extractor.extract(doc.file_path, pages=pages)
                    for tab in res.tables:
                        all_raw_tables.append((doc, tab))
                    job.progress = 10 + int(30 * (idx + 1) / total_docs)
                    db.commit()

                if not all_raw_tables and not isinstance(extractor, PdfTablesExtractor):
                    logger.info("Specialized extractor found 0 tables. Falling back to PdfTablesExtractor.")
                    fallback_extractor = PdfTablesExtractor()
                    for doc in documents:
                        res = fallback_extractor.extract(doc.file_path, pages=pages)
                        for tab in res.tables:
                            all_raw_tables.append((doc, tab))

                if not all_raw_tables:
                    logger.info("Native table extractors found 0 tables. Triggering LLMExtractor AI fallback.")
                    llm_extractor = LLMExtractor()
                    for doc in documents:
                        res = llm_extractor.extract(doc.file_path, pages=pages)
                        for tab in res.tables:
                            all_raw_tables.append((doc, tab))

                if not all_raw_tables:
                    raise ValueError("No tabular data or structured records could be detected in the selected document(s).")

                # Table Healing: Header deduplication & continuation row stitching
                raw_tabs_only = [t for _, t in all_raw_tables]
                healed_tabs = TableHealer.clean_header_repeats(raw_tabs_only)
                healed_tabs = TableHealer.heal_continuation_rows(healed_tabs)

                healed_pairs = []
                for idx, (doc, _) in enumerate(all_raw_tables):
                    healed_pairs.append((doc, healed_tabs[idx]))
                all_raw_tables = healed_pairs

                first_doc, first_table = all_raw_tables[0]
                raw_headers = first_table.headers
                sample_data = first_table.rows[:20]

                schema_columns = SchemaDetector.detect_columns(raw_headers, sample_data)
                col_names = [c["name"] for c in schema_columns]

                if not ds_name:
                    base_name = primary_doc.original_name.rsplit(".", 1)[0]
                    ds_name = f"{base_name} - {extractor.name.capitalize()} Dataset"
                ds_schema_name = extractor.name
                ds_description = f"Generated via {extractor.name} extraction pipeline from {len(documents)} document(s)."

                row_idx = 0
                for doc, tab in all_raw_tables:
                    for row_cells in tab.rows:
                        row_idx += 1
                        raw_dict = cls.map_table_row_to_schema(tab.headers, row_cells, col_names)
                        norm_data, raw_data = Normalizer.normalize_record(raw_dict)

                        matched_sec = SectionDetector.find_section_for_page(doc_profile.sections, tab.page_number) if doc_profile else None
                        source_section_title = matched_sec.title if matched_sec else None

                        prov = {
                            "document_id": doc.id,
                            "document_name": doc.original_name,
                            "page_number": tab.page_number,
                            "table_index": tab.table_index,
                            "source_table": f"Table p.{tab.page_number} #{tab.table_index + 1}",
                            "source_section": source_section_title,
                            "source_row": row_idx,
                            "method": tab.extraction_method,
                        }
                        issues = Validator.validate_record(norm_data, schema_columns, row_idx)
                        records_to_create.append((norm_data, raw_data, tab.confidence, prov, issues))

            # Phase 3: Create Dataset Entity
            dataset = Dataset(
                project_id=job.project_id,
                document_id=primary_doc.id,
                name=ds_name,
                description=ds_description,
                schema_name=ds_schema_name,
                schema_columns=schema_columns,
                status="normalized",
            )
            db.add(dataset)
            db.flush()

            job.dataset_id = dataset.id
            job.progress = 60
            db.commit()

            # Phase 4: Save Records, Field Authorities, and Multi-Confidence
            total_records = len(records_to_create)
            error_records_count = 0
            warning_records_count = 0
            field_authorities = {col: "SOURCE_FACT" for col in col_names}

            for r_counter, (norm_data, raw_data, ext_conf, prov, issues) in enumerate(records_to_create, start=1):
                rec_status = "valid"
                val_conf = 1.0
                if any(i["severity"] == "error" for i in issues):
                    rec_status = "error"
                    val_conf = 0.50
                    error_records_count += 1
                elif any(i["severity"] == "warning" for i in issues):
                    rec_status = "warning"
                    val_conf = 0.85
                    warning_records_count += 1

                # Zero blind trust: Curation confidence is None until an explicit curation policy runs
                multi_conf = {
                    "extraction": ext_conf,
                    "normalization": 0.95,
                    "validation": val_conf,
                    "curation": None,
                }

                rec = Record(
                    dataset_id=dataset.id,
                    row_index=r_counter,
                    data=norm_data,
                    raw_data=raw_data,
                    confidence_score=ext_conf,
                    multi_confidence=multi_conf,
                    source_table=prov.get("source_table"),
                    source_section=prov.get("source_section"),
                    source_row=prov.get("source_row", r_counter),
                    field_authorities=field_authorities,
                    curation_decision="unprocessed",
                    curation_reason=None,
                    provenance=prov,
                    status=rec_status,
                )
                db.add(rec)
                db.flush()

                for issue in issues:
                    v_issue = ValidationIssue(
                        dataset_id=dataset.id,
                        record_id=rec.id,
                        row_index=r_counter,
                        column_name=issue["column_name"],
                        rule_name=issue["rule_name"],
                        severity=issue["severity"],
                        message=issue["message"],
                        raw_value=issue.get("raw_value"),
                    )
                    db.add(v_issue)

            # Phase 5: Evaluate 10 Universal Research Quality Gates
            valid_records_count = total_records - error_records_count - warning_records_count
            has_generic_columns = any(c.startswith("column_") for c in col_names) and len(col_names) <= 2
            null_cell_count = sum(1 for norm_d, _, _, _, _ in records_to_create for v in norm_d.values() if not v or str(v).strip() == "")
            total_cells = total_records * len(col_names) if total_records and col_names else 1

            quality_eval = QualityEngine.evaluate(
                total_records=total_records,
                valid_records=valid_records_count,
                error_records=error_records_count,
                warning_records=warning_records_count,
                review_required_count=0,
                duplicate_count=0,
                conflict_count=0,
                null_cell_count=null_cell_count,
                total_cells=total_cells,
                provenance_missing_count=0,
                curation_processed=False,  # Unprocessed before curation policies
                has_generic_columns=has_generic_columns,
                document_profile_valid=doc_profile is not None,
                dataset_identified=target_candidate is not None or not is_pdf,
            )

            dataset.record_count = total_records
            dataset.valid_record_count = valid_records_count
            dataset.warning_record_count = warning_records_count
            dataset.error_record_count = error_records_count
            dataset.quality_score = quality_eval.overall_score
            dataset.quality_dimensions = quality_eval.dimensions.model_dump()
            dataset.quality_gates_status = quality_eval.gates
            dataset.curation_summary = {
                "included": 0,
                "excluded": 0,
                "review_required": 0,
                "unprocessed": total_records,
            }
            dataset.status = "validated"

            for doc in documents:
                doc.status = "extracted"

            # Finish Job
            duration_ms = int((time.time() - start_time) * 1000)
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.metrics = {
                "total_documents": len(documents),
                "target_candidate": target_candidate.name if target_candidate else None,
                "unit_of_observation": target_candidate.unit_of_observation.value if target_candidate else None,
                "stated_record_count": target_candidate.stated_count if target_candidate else None,
                "records_extracted": total_records,
                "valid_records": valid_records_count,
                "errors_count": error_records_count,
                "warnings_count": warning_records_count,
                "quality_score": quality_eval.overall_score,
                "export_status": quality_eval.export_status,
                "gates": quality_eval.gates,
                "duration_ms": duration_ms,
            }

            activity = ActivityLog(
                project_id=job.project_id,
                entity_type="dataset",
                entity_id=dataset.id,
                action="extracted",
                description=f"Generated dataset '{dataset.name}' with {total_records} records ({quality_eval.overall_score}% quality).",
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
