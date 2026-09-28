from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models.record import Record
from backend.app.models.dataset import Dataset
from backend.app.models.document import Document
from backend.app.models.curation import DecisionLedger, EvidenceItem, CurationDecision


class LineageBuilder:
    """Builds comprehensive, auditable end-to-end provenance graphs for any record."""

    @classmethod
    def get_record_lineage(cls, db: Session, record_id: str) -> Dict[str, Any]:
        record = db.query(Record).filter(Record.id == record_id).first()
        if not record:
            return {"error": "Record not found"}

        dataset = db.query(Dataset).filter(Dataset.id == record.dataset_id).first()
        doc = db.query(Document).filter(Document.id == dataset.document_id).first() if dataset and dataset.document_id else None

        prov = record.provenance or {}
        doc_name = prov.get("document_name") or (doc.original_name if doc else "Source Document")
        doc_hash = getattr(doc, "sha256_hash", None) or getattr(doc, "file_hash", None) or "N/A"
        page_num = prov.get("page_number", 1)
        tab_idx = prov.get("table_index", 0)
        method = prov.get("method", "table_extractor")

        # 1. Source Document Node
        source_doc = {
            "document_id": prov.get("document_id") or (doc.id if doc else "unknown"),
            "document_name": doc_name,
            "sha256_hash": doc_hash,
            "page_number": page_num,
            "table_index": tab_idx,
            "extraction_method": method,
            "bounding_box": prov.get("bounding_box"),
        }

        # 2. Ordered Pipeline Transformation Steps
        steps = []

        # Step 1: Extraction
        steps.append({
            "stage": "EXTRACTION",
            "title": "Raw Document Extraction",
            "description": f"Extracted raw cell tokens from page {page_num} using {method}.",
            "timestamp": record.created_at.isoformat() if record.created_at else None,
            "actor": f"Extractor ({method})",
            "status": "completed",
            "data_snapshot": record.raw_data or {},
            "provenance": prov,
        })

        # Step 2: Normalization
        has_modified = bool(record.raw_data and record.raw_data != record.data)
        steps.append({
            "stage": "NORMALIZATION",
            "title": "Data Normalization & Cleaning",
            "description": "Cleaned ligatures, whitespace, null tokens, and standardized geographic references." if has_modified else "Values verified against standard formatting without modification.",
            "timestamp": record.created_at.isoformat() if record.created_at else None,
            "actor": "Normalizer Engine",
            "status": "completed",
            "data_snapshot": record.data or {},
        })

        # Step 3: Curation Decision
        cur_dec = record.curation_decision or "unprocessed"
        steps.append({
            "stage": "CURATION",
            "title": f"Semantic Curation: {cur_dec.upper()}",
            "description": record.curation_reason or "Assessed against Dataset Intent and Curation Policy.",
            "timestamp": record.updated_at.isoformat() if record.updated_at else None,
            "actor": "Curation Engine",
            "status": cur_dec.lower(),
            "data_snapshot": {
                "decision": cur_dec,
                "multi_confidence": record.multi_confidence or {},
                "derived_data": record.derived_data or {},
            },
        })

        # Step 4: Validation
        val_status = record.status or "valid"
        issues_count = len(record.validation_issues) if record.validation_issues else 0
        steps.append({
            "stage": "VALIDATION",
            "title": f"Schema Validation: {val_status.upper()}",
            "description": f"{issues_count} validation exception(s) detected." if issues_count > 0 else "Satisfies schema constraints and domain business rules.",
            "timestamp": record.created_at.isoformat() if record.created_at else None,
            "actor": "Validator Engine",
            "status": "warning" if issues_count > 0 else "passed",
            "data_snapshot": {
                "issues": [
                    {"column": i.column_name, "rule": i.rule_name, "severity": i.severity, "message": i.message}
                    for i in (record.validation_issues or [])
                ]
            },
        })

        # Step 5: Human Review (if any)
        if record.status == "human_reviewed" or record.review_notes:
            steps.append({
                "stage": "HUMAN_REVIEW",
                "title": "Human-in-the-Loop Audit",
                "description": f"Verified by researcher: {record.review_notes or 'Decision confirmed.'}",
                "timestamp": record.updated_at.isoformat() if record.updated_at else None,
                "actor": "Human Operator",
                "status": "approved",
                "data_snapshot": {"review_notes": record.review_notes},
            })

        # Fetch Decision Ledger Entries
        ledger_entries = (
            db.query(DecisionLedger)
            .filter(DecisionLedger.record_id == record_id)
            .order_by(DecisionLedger.created_at.asc())
            .all()
        )
        ledger_data = [
            {
                "id": entry.id,
                "record_id": entry.record_id,
                "dataset_id": entry.dataset_id,
                "stage": entry.stage,
                "field_name": entry.field_name,
                "previous_value": entry.previous_value,
                "new_value": entry.new_value,
                "decision": entry.decision,
                "reason": entry.reason,
                "actor": entry.actor,
                "actor_id": entry.actor_id,
                "metadata_snapshot": entry.metadata_snapshot or {},
                "created_at": entry.created_at,
            }
            for entry in ledger_entries
        ]

        return {
            "record_id": record.id,
            "dataset_id": record.dataset_id,
            "source_document": source_doc,
            "steps": steps,
            "ledger": ledger_data,
        }
