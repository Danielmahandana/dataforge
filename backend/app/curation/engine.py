from __future__ import annotations
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.document import Document
from backend.app.models.curation import (
    DatasetIntent,
    CurationPolicy,
    CurationRun,
    CurationDecision,
    EvidenceItem,
    DecisionLedger,
    SourceConflict,
)
from backend.app.curation.policy import get_policy_by_id, CurationPolicyConfig
from backend.app.curation.relevance_evaluator import RelevanceEvaluator
from backend.app.curation.deduplicator import SemanticDeduplicator
from backend.app.curation.quality_engine import QualityEngine
from backend.app.curation.manifest import ManifestBuilder
from backend.app.services.llm import get_llm_provider
from backend.app.config import settings

logger = logging.getLogger("dataforge.curation")


class CurationEngine:
    """Orchestrates tiered semantic curation, conflict detection, structured evidence generation,
    reproducibility manifests, and quality evaluation under Zero Blind Trust."""

    ENGINE_VERSION = "2.2.0"
    RULESET_VERSION = "2024.1"

    @classmethod
    def execute_curation_run(
        cls,
        db: Session,
        run_id: str,
    ) -> Optional[CurationRun]:
        run = db.query(CurationRun).filter(CurationRun.id == run_id).first()
        if not run:
            logger.error(f"CurationRun {run_id} not found.")
            return None

        dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
        if not dataset:
            run.status = "failed"
            run.error_message = "Target dataset not found"
            db.commit()
            return run

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        run.progress = 5
        run.engine_version = cls.ENGINE_VERSION
        run.ruleset_version = cls.RULESET_VERSION
        db.commit()

        start_time = time.time()

        try:
            # 1. Resolve Policy and Intent
            intent: Optional[DatasetIntent] = None
            if run.intent_id:
                intent = db.query(DatasetIntent).filter(DatasetIntent.id == run.intent_id).first()

            policy_config: CurationPolicyConfig = get_policy_by_id(run.policy_id or "merseta_ofo_relevance")

            scope_domains = intent.scope if intent else policy_config.chambers_or_domains
            exclude_criteria = intent.exclude_criteria if intent else []

            # 2. Fetch all dataset records
            records = db.query(Record).filter(Record.dataset_id == dataset.id).order_by(Record.row_index.asc()).all()
            total_records = len(records)
            run.total_records = total_records
            db.commit()

            if total_records == 0:
                run.status = "completed"
                run.progress = 100
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return run

            # 3. Analyze Duplicate Candidates across dataset
            raw_rec_dicts = [{"id": r.id, "data": r.data} for r in records]
            dup_flags = SemanticDeduplicator.analyze_dataset_duplicates(raw_rec_dicts)
            dup_map = {f.record_id: f.duplicate_type for f in dup_flags}

            # 4. Clear prior curation decisions, conflicts, & evidence for this dataset run
            existing_decisions = db.query(CurationDecision).filter(CurationDecision.dataset_id == dataset.id).all()
            for ed in existing_decisions:
                db.delete(ed)

            existing_conflicts = db.query(SourceConflict).filter(SourceConflict.dataset_id == dataset.id).all()
            for ec in existing_conflicts:
                db.delete(ec)
            db.flush()

            included_count = 0
            excluded_count = 0
            review_count = 0
            total_conflicts_count = 0

            # LLM Provider for Tier 4 reasoning (if enabled)
            llm_provider = get_llm_provider() if settings.LLM_ENABLED else None

            # 5. Process each record
            for idx, rec in enumerate(records):
                row_idx = rec.row_index or (idx + 1)
                has_val_error = (rec.status == "error") or any(i.severity == "error" for i in rec.validation_issues)
                has_val_warn = (rec.status == "warning") or any(i.severity == "warning" for i in rec.validation_issues)
                dup_type = dup_map.get(rec.id)

                # Evaluate record
                eval_pkg = RelevanceEvaluator.evaluate_record(
                    record_data=rec.data or {},
                    raw_data=rec.raw_data or {},
                    provenance=rec.provenance or {},
                    row_index=row_idx,
                    policy=policy_config,
                    scope_domains=scope_domains,
                    exclude_criteria=exclude_criteria,
                    has_validation_error=has_val_error,
                    has_validation_warning=has_val_warn,
                    duplicate_flag=dup_type,
                    llm_decision=None,
                )

                dec_res = eval_pkg.decision_result
                decision_val = dec_res.decision

                if decision_val == "INCLUDE":
                    included_count += 1
                elif decision_val == "EXCLUDE":
                    excluded_count += 1
                else:
                    review_count += 1

                # Persist Source Conflicts if detected
                persisted_conflict_ids: List[str] = []
                if eval_pkg.conflicts:
                    for conf in eval_pkg.conflicts:
                        sc_entity = SourceConflict(
                            dataset_id=dataset.id,
                            record_id=rec.id,
                            conflict_type=conf.conflict_type,
                            source_a=conf.source_a,
                            source_b=conf.source_b,
                            claims=[conf.claim_a, conf.claim_b],
                            severity=conf.severity,
                            recommended_action=conf.recommended_action,
                            resolution_status="UNRESOLVED",
                        )
                        db.add(sc_entity)
                        db.flush()
                        persisted_conflict_ids.append(sc_entity.id)
                        total_conflicts_count += 1

                # Update Record entity
                rec.curation_decision = decision_val
                rec.curation_reason = dec_res.reason
                rec.multi_confidence = dec_res.multi_confidence
                rec.confidence_score = dec_res.confidence
                rec.derived_data = dec_res.derived_fields
                rec.duplicate_status = dup_type or "none"

                # Persist CurationDecision
                decision_entity = CurationDecision(
                    record_id=rec.id,
                    dataset_id=dataset.id,
                    run_id=run.id,
                    decision=decision_val,
                    confidence=dec_res.confidence,
                    multi_confidence=dec_res.multi_confidence,
                    primary_claim=dec_res.primary_claim,
                    reason=dec_res.reason,
                    why_not=dec_res.why_not,
                    decision_method=dec_res.decision_method,
                    uncertainties=dec_res.uncertainties,
                    derived_fields=dec_res.derived_fields,
                    explanation_contract=dec_res.explanation_contract,
                    conflict_ids=persisted_conflict_ids,
                    model_used=getattr(llm_provider, "model_name", "deterministic_rule_engine"),
                    prompt_version="v2.2.0",
                )
                db.add(decision_entity)
                db.flush()

                # Persist Evidence Items
                for ev_draft in eval_pkg.evidence_items:
                    ev_entity = EvidenceItem(
                        record_id=rec.id,
                        decision_id=decision_entity.id,
                        evidence_type=ev_draft.evidence_type,
                        document_id=ev_draft.document_id,
                        document_name=ev_draft.document_name,
                        page_number=ev_draft.page_number,
                        table_index=ev_draft.table_index,
                        row_index=ev_draft.row_index,
                        cell_key=ev_draft.cell_key,
                        source_text=ev_draft.source_text,
                        observed_source_value=ev_draft.observed_source_value,
                        relation_nature=ev_draft.relationship,
                        interpretation=ev_draft.interpretation,
                        strength=ev_draft.strength,
                        is_inherited=ev_draft.is_inherited,
                        inherited_from=ev_draft.inherited_from,
                        claim=ev_draft.claim,
                        rule_id=ev_draft.rule_id,
                        confidence=ev_draft.confidence,
                    )
                    db.add(ev_entity)

                # Persist Decision Ledger entry
                ledger_entry = DecisionLedger(
                    record_id=rec.id,
                    dataset_id=dataset.id,
                    stage="CURATION",
                    field_name="curation_decision",
                    previous_value="unprocessed",
                    new_value=decision_val,
                    decision=decision_val,
                    reason=dec_res.reason,
                    actor="CurationEngine",
                    actor_id=policy_config.id,
                    metadata_snapshot={
                        "score": eval_pkg.rule_result.total_score,
                        "primary_claim": dec_res.primary_claim,
                        "multi_confidence": dec_res.multi_confidence,
                        "confidence_basis": dec_res.confidence_basis,
                        "conflicts_count": len(persisted_conflict_ids),
                    },
                )
                db.add(ledger_entry)

                # Update progress in chunks
                if (idx + 1) % 10 == 0 or (idx + 1) == total_records:
                    progress_pct = 5 + int(85 * (idx + 1) / total_records)
                    run.progress = progress_pct
                    run.included_count = included_count
                    run.excluded_count = excluded_count
                    run.review_count = review_count
                    db.commit()

            # 6. Evaluate Quality Dimensions and Gates
            error_recs = sum(1 for r in records if r.status == "error")
            warn_recs = sum(1 for r in records if r.status == "warning")
            valid_recs = total_records - error_recs - warn_recs

            quality_eval = QualityEngine.evaluate(
                total_records=total_records,
                valid_records=valid_recs,
                error_records=error_recs,
                warning_records=warn_recs,
                review_required_count=review_count,
                duplicate_count=len(dup_flags),
            )

            # 7. Collect Source Documents & Hashes for Manifest
            doc_ids = set()
            for r in records:
                if r.provenance and r.provenance.get("document_id"):
                    doc_ids.add(r.provenance["document_id"])

            source_docs_info: List[Dict[str, Any]] = []
            for d_id in doc_ids:
                doc = db.query(Document).filter(Document.id == d_id).first()
                if doc:
                    source_docs_info.append({
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "sha256_hash": getattr(doc, "file_hash", getattr(doc, "sha256_hash", None)),
                    })

            # 8. Build Reproducibility Curation Manifest
            manifest = ManifestBuilder.generate_manifest(
                run_id=run.id,
                dataset_id=dataset.id,
                dataset_name=dataset.name,
                intent_data={
                    "id": intent.id,
                    "name": intent.name,
                    "objective": intent.objective,
                    "scope": intent.scope,
                    "classification_system": intent.classification_system,
                } if intent else {},
                policy_id=policy_config.id,
                policy_version="1.0.0",
                engine_version=cls.ENGINE_VERSION,
                ruleset_version=cls.RULESET_VERSION,
                source_documents=source_docs_info,
                record_counts=total_records,
                include_count=included_count,
                exclude_count=excluded_count,
                review_count=review_count,
                conflict_count=total_conflicts_count,
                quality_metrics=quality_eval.dimensions.model_dump(),
                model_name=getattr(llm_provider, "model_name", "deterministic_rule_engine"),
                prompt_version="v2.2.0",
            )

            # 9. Update Dataset state
            dataset.intent_id = run.intent_id
            dataset.policy_id = run.policy_id
            dataset.quality_score = quality_eval.overall_score
            dataset.quality_dimensions = quality_eval.dimensions.model_dump()
            dataset.quality_gates_status = quality_eval.gates
            dataset.curation_summary = {
                "included": included_count,
                "excluded": excluded_count,
                "review_required": review_count,
                "unprocessed": 0,
            }

            # 10. Complete Curation Run
            duration_ms = int((time.time() - start_time) * 1000)
            run.status = "completed"
            run.progress = 100
            run.included_count = included_count
            run.excluded_count = excluded_count
            run.review_count = review_count
            run.manifest = manifest.model_dump()
            run.completed_at = datetime.now(timezone.utc)
            run.metrics = {
                "total_records": total_records,
                "included_count": included_count,
                "excluded_count": excluded_count,
                "review_count": review_count,
                "conflict_count": total_conflicts_count,
                "duplicates_found": len(dup_flags),
                "quality_score": quality_eval.overall_score,
                "duration_ms": duration_ms,
            }

            db.commit()
            return run

        except Exception as e:
            logger.exception("Curation run execution failed")
            db.rollback()
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return run
