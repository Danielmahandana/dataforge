from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.validation_issue import ValidationIssue
from backend.app.services.llm import get_llm_provider
from backend.app.config import settings

router = APIRouter(prefix="/llm", tags=["LLM & Intelligence"])


class LLMQueryRequest(BaseModel):
    dataset_id: str
    query: str = Field(..., description="Natural language question about the dataset")


class LLMExplainRequest(BaseModel):
    issue_id: str


class LLMSummarizeRequest(BaseModel):
    dataset_id: str


@router.get("/status")
def get_llm_status():
    """Return configured LLM provider and readiness status."""
    provider = get_llm_provider()
    has_key = bool(
        settings.GROQ_API_KEY
        or settings.OPENAI_API_KEY
        or settings.GEMINI_API_KEY
        or settings.ANTHROPIC_API_KEY
        or settings.OLLAMA_BASE_URL
    )
    return {
        "enabled": settings.LLM_ENABLED,
        "active_provider": settings.LLM_PROVIDER,
        "active_model": provider.model_name,
        "configured": has_key,
        "supported_providers": ["groq", "openai", "gemini", "anthropic", "ollama"],
    }


@router.post("/query-dataset")
def query_dataset_with_llm(req: LLMQueryRequest, db: Session = Depends(get_db)):
    """Ask natural language questions about a dataset's extracted records."""
    dataset = db.query(Dataset).filter(Dataset.id == req.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = db.query(Record).filter(Record.dataset_id == req.dataset_id).limit(100).all()
    sample_data = [r.data for r in records if r.data]

    provider = get_llm_provider()

    system_prompt = (
        "You are Darkroom DataForge AI Assistant.\n"
        f"You are analyzing dataset '{dataset.name}' (Schema: {dataset.schema_name}).\n"
        f"Sample Records ({len(sample_data)} rows):\n"
        f"{sample_data[:20]}\n"
        "Answer user questions accurately based on the dataset schema and records."
    )

    prompt = f"User Question: {req.query}"
    answer = provider.generate_text(prompt=prompt, system_instruction=system_prompt)

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "query": req.query,
        "answer": answer,
        "model_used": provider.model_name,
    }


@router.post("/explain-issue")
def explain_validation_issue(req: LLMExplainRequest, db: Session = Depends(get_db)):
    """Provide AI explanation and suggested resolution for a validation issue."""
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == req.issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found")

    record = db.query(Record).filter(Record.id == issue.record_id).first()
    record_data = record.data if record else {}

    provider = get_llm_provider()

    prompt = (
        f"Validation Issue Details:\n"
        f"- Column: {issue.column_name}\n"
        f"- Severity: {issue.severity}\n"
        f"- Rule Violated: {issue.rule_name}\n"
        f"- Error Message: {issue.message}\n"
        f"- Raw Cell Value: {issue.raw_value}\n"
        f"- Record Context: {record_data}\n\n"
        f"Provide a 2-sentence explanation of why this error occurred and recommend a specific corrected value."
    )

    explanation = provider.generate_text(prompt=prompt)

    return {
        "issue_id": issue.id,
        "column_name": issue.column_name,
        "message": issue.message,
        "explanation": explanation,
    }


@router.post("/summarize-dataset")
def summarize_dataset(req: LLMSummarizeRequest, db: Session = Depends(get_db)):
    """Generate an executive narrative summary of a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == req.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    provider = get_llm_provider()

    prompt = (
        f"Generate a concise 3-bullet executive summary of the following extracted dataset:\n"
        f"- Dataset Name: {dataset.name}\n"
        f"- Description: {dataset.description}\n"
        f"- Total Records: {dataset.record_count}\n"
        f"- Valid Records: {dataset.valid_record_count}\n"
        f"- Error Records: {dataset.error_record_count}\n"
        f"- Quality Score: {dataset.quality_score}%\n"
        f"- Columns: {[c.get('name') for c in (dataset.schema_columns or [])]}"
    )

    summary = provider.generate_text(prompt=prompt)

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "summary": summary,
    }
