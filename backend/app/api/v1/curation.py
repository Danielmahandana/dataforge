from __future__ import annotations
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.project import Project
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.review import ReviewAudit
from backend.app.models.curation import (
    DatasetIntent,
    CurationPolicy,
    CurationRun,
    CurationDecision,
    EvidenceItem,
    DecisionLedger,
    DatasetVersion,
)
from backend.app.schemas.curation import (
    DatasetIntentCreate,
    DatasetIntentResponse,
    CurationPolicyCreate,
    CurationPolicyResponse,
    CurationRunCreate,
    CurationRunResponse,
    CurationDecisionResponse,
    EvidenceItemResponse,
    DecisionLedgerResponse,
    RecordReviewRequest,
    ReviewQueueResponse,
    ReviewQueueItem,
    LineageGraphResponse,
    QualityGatesResponse,
    QualityDimensionsResponse,
    DeduplicationRunResponse,
)
from backend.app.curation.policy import get_builtin_policies, get_policy_by_id
from backend.app.curation.engine import CurationEngine
from backend.app.curation.lineage_builder import LineageBuilder
from backend.app.curation.quality_engine import QualityEngine
from backend.app.curation.deduplicator import SemanticDeduplicator

logger = logging.getLogger("dataforge.api.curation")

router = APIRouter(prefix="/curation", tags=["Semantic Curation & Curation Governance"])


# --- Dataset Intents ---

@router.get("/intents", response_model=List[DatasetIntentResponse])
def list_intents(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(DatasetIntent)
    if project_id:
        q = q.filter(DatasetIntent.project_id == project_id)
    return q.order_by(DatasetIntent.created_at.desc()).all()


@router.post("/intents", response_model=DatasetIntentResponse, status_code=status.HTTP_201_CREATED)
def create_intent(payload: DatasetIntentCreate, db: Session = Depends(get_db)):
    intent = DatasetIntent(
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        objective=payload.objective,
        scope=payload.scope,
        include_criteria=payload.include_criteria,
        exclude_criteria=payload.exclude_criteria,
        authoritative_sources=payload.authoritative_sources,
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    return intent


@router.get("/intents/{intent_id}", response_model=DatasetIntentResponse)
def get_intent(intent_id: str, db: Session = Depends(get_db)):
    intent = db.query(DatasetIntent).filter(DatasetIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="DatasetIntent not found")
    return intent


@router.delete("/intents/{intent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intent(intent_id: str, db: Session = Depends(get_db)):
    intent = db.query(DatasetIntent).filter(DatasetIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="DatasetIntent not found")
    db.delete(intent)
    db.commit()


# --- Curation Policies ---

@router.get("/policies", response_model=List[CurationPolicyResponse])
def list_policies(db: Session = Depends(get_db)):
    # 1. Built-in presets
    builtins = get_builtin_policies()
    builtin_responses = [
        CurationPolicyResponse(
            id=bp.id,
            name=bp.name,
            description=bp.description,
            dimensions=bp.dimensions,
            rules=bp.rules,
            include_threshold=bp.include_threshold,
            review_threshold=bp.review_threshold,
            exclude_threshold=bp.exclude_threshold,
            is_builtin=True,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        for bp in builtins
    ]

    # 2. Custom database policies
    custom_policies = db.query(CurationPolicy).all()
    custom_responses = [CurationPolicyResponse.model_validate(p) for p in custom_policies]

    # Combine (avoid duplicate IDs)
    existing_ids = {p.id for p in custom_responses}
    all_policies = [p for p in builtin_responses if p.id not in existing_ids] + custom_responses
    return all_policies


@router.post("/policies", response_model=CurationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_custom_policy(payload: CurationPolicyCreate, db: Session = Depends(get_db)):
    existing = db.query(CurationPolicy).filter(CurationPolicy.id == payload.id).first()
    if existing:
        existing.name = payload.name
        existing.description = payload.description
        existing.dimensions = payload.dimensions
        existing.rules = payload.rules
        existing.include_threshold = payload.include_threshold
        existing.review_threshold = payload.review_threshold
        existing.exclude_threshold = payload.exclude_threshold
        db.commit()
        db.refresh(existing)
        return existing

    policy = CurationPolicy(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        dimensions=payload.dimensions,
        rules=payload.rules,
        include_threshold=payload.include_threshold,
        review_threshold=payload.review_threshold,
        exclude_threshold=payload.exclude_threshold,
        is_builtin=False,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


# --- Curation Runs ---

def run_curation_task(run_id: str):
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        CurationEngine.execute_curation_run(db, run_id)
    finally:
        db.close()


@router.post("/runs", response_model=CurationRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_curation_run(
    payload: CurationRunCreate,
    background_tasks: BackgroundTasks,
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    dataset_query = db.query(Dataset).filter(Dataset.id == payload.dataset_id)
    if project_id:
        dataset_query = dataset_query.filter(Dataset.project_id == project_id)
    dataset = dataset_query.first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or does not belong to specified project")

    policy_id = payload.policy_id or "merseta_ofo_relevance"

    run = CurationRun(
        dataset_id=dataset.id,
        intent_id=payload.intent_id,
        policy_id=policy_id,
        status="queued",
        progress=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Queue background curation execution
    background_tasks.add_task(run_curation_task, run.id)
    return run


@router.get("/runs/{run_id}", response_model=CurationRunResponse)
def get_curation_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(CurationRun).filter(CurationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="CurationRun not found")
    return run


@router.get("/runs/{run_id}/manifest")
def get_curation_run_manifest(run_id: str, db: Session = Depends(get_db)):
    run = db.query(CurationRun).filter(CurationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="CurationRun not found")
    if not run.manifest:
        raise HTTPException(status_code=404, detail="Manifest not yet generated for this run")
    return run.manifest


# --- Record Curation Decisions & Evidence ---

@router.get("/records/{record_id}/evidence", response_model=List[EvidenceItemResponse])
def get_record_evidence(record_id: str, db: Session = Depends(get_db)):
    items = (
        db.query(EvidenceItem)
        .filter(EvidenceItem.record_id == record_id)
        .order_by(EvidenceItem.confidence.desc())
        .all()
    )
    return items


@router.get("/records/{record_id}/lineage", response_model=LineageGraphResponse)
def get_record_lineage(record_id: str, db: Session = Depends(get_db)):
    lineage = LineageBuilder.get_record_lineage(db, record_id)
    if "error" in lineage:
        raise HTTPException(status_code=404, detail=lineage["error"])
    return lineage


@router.post("/records/{record_id}/review", response_model=CurationDecisionResponse)
def review_record_decision(
    record_id: str,
    payload: RecordReviewRequest,
    db: Session = Depends(get_db),
):
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    prev_decision = record.curation_decision or "unprocessed"
    new_decision = payload.decision.upper()  # INCLUDE, EXCLUDE, OVERRIDE

    # Update record
    record.curation_decision = new_decision
    record.status = "human_reviewed"
    record.review_notes = payload.notes or f"Human operator reviewed: set to {new_decision}"

    if payload.corrected_data:
        record.data = {**record.data, **payload.corrected_data}

    # Fetch or create CurationDecision
    dec = db.query(CurationDecision).filter(CurationDecision.record_id == record_id).first()
    if not dec:
        dec = CurationDecision(
            record_id=record.id,
            dataset_id=record.dataset_id,
            decision=new_decision,
            confidence=1.0,
            primary_claim="Operator human review verified",
            reason=payload.notes or "Decision updated by researcher.",
            model_used="human-reviewer",
        )
        db.add(dec)
    else:
        dec.decision = new_decision
        dec.confidence = 1.0
        dec.reason = f"Human Review Override: {payload.notes or 'Verified by operator'}"
        dec.model_used = "human-reviewer"

    # Add Evidence for human audit
    human_ev = EvidenceItem(
        record_id=record.id,
        decision_id=dec.id,
        evidence_type="HUMAN_DECISION",
        claim=f"Human reviewer '{payload.reviewer_name or 'Researcher'}' set decision to {new_decision}: {payload.notes or 'Approved.'}",
        confidence=1.0,
        source_text=str(payload.notes or ""),
        observed_source_value=new_decision,
        relation_nature="human_research_determination",
        interpretation="Authoritative research expert review overriding automated inference.",
        strength="STRONG",
        is_inherited=False,
    )
    db.add(human_ev)

    # Record in DecisionLedger
    ledger = DecisionLedger(
        record_id=record.id,
        dataset_id=record.dataset_id,
        stage="HUMAN_REVIEW",
        field_name="curation_decision",
        previous_value=prev_decision,
        new_value=new_decision,
        decision=new_decision,
        reason=payload.notes or "Human operator decision override",
        actor="user",
        actor_id=payload.reviewer_name or "Researcher",
        metadata_snapshot={"corrected_data": payload.corrected_data},
    )
    db.add(ledger)

    # Record in ReviewAudit for existing audit tab
    review_audit = ReviewAudit(
        dataset_id=record.dataset_id,
        record_id=record.id,
        action="curation_decision_override",
        field_name="curation_decision",
        old_value=prev_decision,
        new_value=new_decision,
        reason=payload.notes,
        reviewed_by=payload.reviewer_name or "Researcher",
    )
    db.add(review_audit)

    db.commit()
    db.refresh(dec)
    return dec


# --- Prioritized Review Queue ---

@router.get("/datasets/{dataset_id}/review-queue", response_model=ReviewQueueResponse)
def get_dataset_review_queue(
    dataset_id: str,
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    dataset_query = db.query(Dataset).filter(Dataset.id == dataset_id)
    if project_id:
        dataset_query = dataset_query.filter(Dataset.project_id == project_id)
    dataset = dataset_query.first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or does not belong to specified project")

    records = db.query(Record).filter(Record.dataset_id == dataset_id).all()
    queue_items: List[ReviewQueueItem] = []

    crit_count = 0
    high_count = 0
    med_count = 0

    for rec in records:
        dec = rec.curation_decision or "unprocessed"
        is_error = (rec.status == "error") or any(i.severity == "error" for i in rec.validation_issues)
        is_warn = (rec.status == "warning") or any(i.severity == "warning" for i in rec.validation_issues)
        is_dup = rec.duplicate_status in ["exact", "structural", "semantic_candidate"]

        # Only include in review queue if explicitly REVIEW, or unprocessed, or has error/duplicate conflict
        if dec not in ["REVIEW", "unprocessed"] and not is_error and not is_dup:
            continue

        priority = "medium"
        reason_code = "ambiguous_evidence"
        reason_details = rec.curation_reason or "Record requires evaluation"

        if is_error:
            priority = "critical"
            reason_code = "validation_error"
            reason_details = "Schema or domain validation violation must be fixed."
            crit_count += 1
        elif is_dup:
            priority = "high"
            reason_code = "duplicate_risk"
            reason_details = f"Duplicate risk detected ({rec.duplicate_status}). Confirm canonical record."
            high_count += 1
        elif dec == "REVIEW":
            priority = "high" if (rec.confidence_score or 1.0) < 0.65 else "medium"
            reason_code = "low_confidence" if (rec.confidence_score or 1.0) < 0.65 else "ambiguous_evidence"
            if priority == "high":
                high_count += 1
            else:
                med_count += 1
        else:
            med_count += 1

        title = str(
            rec.data.get("occupation_title")
            or rec.data.get("occupation")
            or rec.data.get("qualification")
            or rec.data.get("qualification_name")
            or rec.data.get("title")
            or f"Row {rec.row_index}"
        )
        identifier = str(rec.data.get("ofo_code") or rec.data.get("saqa_id") or rec.data.get("code") or "")

        multi_conf = rec.multi_confidence or {
            "extraction": 1.0, "normalization": 1.0, "validation": 1.0, "curation": 0.5, "overall": 0.7
        }

        queue_items.append(ReviewQueueItem(
            record_id=rec.id,
            dataset_id=dataset.id,
            row_index=rec.row_index,
            primary_title=title,
            identifier=identifier if identifier else None,
            decision=dec,
            priority=priority,
            reason_code=reason_code,
            reason_details=reason_details,
            overall_confidence=rec.confidence_score or 0.7,
            multi_confidence=multi_conf,
            provenance=rec.provenance or {},
            data=rec.data or {},
            raw_data=rec.raw_data or {},
            derived_data=rec.derived_data or {},
            evidence_summary=[e.claim for e in rec.evidence_items[:3]] if rec.evidence_items else [],
        ))

    # Sort queue by priority: critical -> high -> medium
    priority_order = {"critical": 0, "high": 1, "medium": 2}
    queue_items.sort(key=lambda x: priority_order.get(x.priority, 3))

    return ReviewQueueResponse(
        dataset_id=dataset.id,
        total_review_required=len(queue_items),
        critical_count=crit_count,
        high_count=high_count,
        medium_count=med_count,
        items=queue_items,
    )


# --- Semantic Deduplication & Quality Gates ---

@router.post("/datasets/{dataset_id}/deduplicate", response_model=DeduplicationRunResponse)
def run_dataset_deduplication(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = db.query(Record).filter(Record.dataset_id == dataset_id).all()
    raw_dicts = [{"id": r.id, "data": r.data} for r in records]

    flags = SemanticDeduplicator.analyze_dataset_duplicates(raw_dicts)

    exact_c = sum(1 for f in flags if f.duplicate_type == "EXACT_DUPLICATE")
    struct_c = sum(1 for f in flags if f.duplicate_type == "STRUCTURAL_DUPLICATE")
    sem_c = sum(1 for f in flags if f.duplicate_type == "POSSIBLE_SEMANTIC_DUPLICATE")

    # Update records with duplicate flags
    flag_map = {f.record_id: f for f in flags}
    for r in records:
        if r.id in flag_map:
            f = flag_map[r.id]
            r.duplicate_status = f.duplicate_type.lower()
            r.duplicate_of_id = f.target_record_id
    db.commit()

    return DeduplicationRunResponse(
        dataset_id=dataset.id,
        total_records_analyzed=len(records),
        exact_duplicates_count=exact_c,
        structural_duplicates_count=struct_c,
        semantic_candidates_count=sem_c,
        duplicates_flagged=[f.model_dump() for f in flags],
    )


@router.get("/datasets/{dataset_id}/quality-gates", response_model=QualityGatesResponse)
def get_dataset_quality_gates(
    dataset_id: str,
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    dataset_query = db.query(Dataset).filter(Dataset.id == dataset_id)
    if project_id:
        dataset_query = dataset_query.filter(Dataset.project_id == project_id)
    dataset = dataset_query.first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or does not belong to specified project")

    records = db.query(Record).filter(Record.dataset_id == dataset_id).all()
    total = len(records)
    error_c = sum(1 for r in records if r.status == "error")
    warn_c = sum(1 for r in records if r.status == "warning")
    valid_c = total - error_c - warn_c
    review_c = sum(1 for r in records if r.curation_decision == "REVIEW" or r.status == "warning")

    res = QualityEngine.evaluate(
        total_records=total,
        valid_records=valid_c,
        error_records=error_c,
        warning_records=warn_c,
        review_required_count=review_c,
    )

    return QualityGatesResponse(
        overall_score=res.overall_score,
        dimensions=QualityDimensionsResponse(
            extraction=res.dimensions.extraction,
            structural=res.dimensions.structural,
            normalization=res.dimensions.normalization,
            validation=res.dimensions.validation,
            completeness=res.dimensions.completeness,
            consistency=res.dimensions.consistency,
            curation=res.dimensions.curation,
            provenance=res.dimensions.provenance,
            overall=res.dimensions.overall,
        ),
        gates=res.gates,
        critical_issues_count=res.critical_issues_count,
        warning_count=res.warning_count,
        can_export_clean=res.can_export_clean,
        can_export_research=res.can_export_research,
        reasons=res.reasons,
    )
