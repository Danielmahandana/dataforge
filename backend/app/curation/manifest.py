from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class CurationManifest(BaseModel):
    """Machine-readable provenance manifest capturing the exact environment, versions,
    rules, and documents used in a curation run to guarantee scientific reproducibility."""

    manifest_version: str = "2.0.0"
    run_id: str
    dataset_id: str
    dataset_name: str
    dataset_intent: Dict[str, Any] = Field(default_factory=dict)
    policy_id: str
    policy_version: str = "1.0.0"
    engine_version: str = "2.2.0"
    ruleset_version: str = "2024.1"
    classification_sources: List[str] = Field(default_factory=lambda: ["South African OFO 2024 (DHET Gazette)", "merSETA Chamber Profiles"])
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    source_documents: List[Dict[str, Any]] = Field(default_factory=list)  # [{doc_id, name, sha256_hash}]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    record_counts: int = 0
    include_count: int = 0
    exclude_count: int = 0
    review_count: int = 0
    conflict_count: int = 0
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    reproducibility_hash: Optional[str] = None


class ManifestBuilder:
    @classmethod
    def generate_manifest(
        cls,
        run_id: str,
        dataset_id: str,
        dataset_name: str,
        intent_data: Optional[Dict[str, Any]],
        policy_id: str,
        policy_version: str,
        engine_version: str,
        ruleset_version: str,
        source_documents: List[Dict[str, Any]],
        record_counts: int,
        include_count: int,
        exclude_count: int,
        review_count: int,
        conflict_count: int,
        quality_metrics: Dict[str, Any],
        model_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
    ) -> CurationManifest:
        return CurationManifest(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_intent=intent_data or {},
            policy_id=policy_id,
            policy_version=policy_version,
            engine_version=engine_version,
            ruleset_version=ruleset_version,
            source_documents=source_documents,
            record_counts=record_counts,
            include_count=include_count,
            exclude_count=exclude_count,
            review_count=review_count,
            conflict_count=conflict_count,
            quality_metrics=quality_metrics,
            model_name=model_name or "deterministic_rule_engine",
            prompt_version=prompt_version or "v2.2.0",
        )
