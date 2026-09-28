from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class QualityDimensionScores(BaseModel):
    extraction: float = 100.0
    structural: float = 100.0
    normalization: float = 100.0
    validation: float = 100.0
    completeness: float = 100.0
    consistency: float = 100.0
    curation: float = 100.0
    provenance: float = 100.0
    overall: float = 100.0


class QualityEvaluationResult(BaseModel):
    dimensions: QualityDimensionScores
    overall_score: float
    gates: Dict[str, str]  # passed, warning, failed, pending, blocked
    critical_issues_count: int
    warning_count: int
    can_export_clean: bool
    can_export_research: bool
    export_status: str = "PRODUCTION_READY"  # PRODUCTION_READY, REQUIRES_REVIEW, PARTIALLY_PROCESSED, BLOCKED
    reasons: List[str] = Field(default_factory=list)


class QualityEngine:
    """Evaluates multi-dimensional research data quality and checks pipeline release gates."""

    DIMENSION_WEIGHTS = {
        "extraction": 0.15,
        "structural": 0.10,
        "normalization": 0.10,
        "validation": 0.20,
        "completeness": 0.15,
        "consistency": 0.10,
        "curation": 0.10,
        "provenance": 0.10,
    }

    @classmethod
    def evaluate(
        cls,
        total_records: int,
        valid_records: int,
        error_records: int,
        warning_records: int,
        review_required_count: int,
        duplicate_count: int = 0,
        conflict_count: int = 0,
        null_cell_count: int = 0,
        total_cells: int = 0,
        provenance_missing_count: int = 0,
        curation_processed: bool = True,
        has_generic_columns: bool = False,
        document_profile_valid: bool = True,
        dataset_identified: bool = True,
    ) -> QualityEvaluationResult:
        if total_records <= 0:
            scores = QualityDimensionScores()
            return QualityEvaluationResult(
                dimensions=scores,
                overall_score=100.0,
                gates={
                    "document_understanding_gate": "passed",
                    "dataset_identification_gate": "passed",
                    "structural_integrity_gate": "passed",
                    "schema_gate": "passed",
                    "normalization_gate": "passed",
                    "validation_gate": "passed",
                    "curation_gate": "passed",
                    "evidence_gate": "passed",
                    "provenance_gate": "passed",
                    "review_gate": "passed",
                },
                critical_issues_count=0,
                warning_count=0,
                can_export_clean=True,
                can_export_research=True,
                export_status="PRODUCTION_READY",
                reasons=[],
            )

        # 1. Extraction Score
        ext_penalty = (error_records / total_records) * 60.0
        extraction_score = max(0.0, round(100.0 - ext_penalty, 2))

        # 2. Structural Score
        struct_penalty = (duplicate_count / total_records) * 40.0
        if has_generic_columns:
            struct_penalty += 50.0
        structural_score = max(0.0, round(100.0 - struct_penalty, 2))

        # 3. Normalization Score
        norm_penalty = (warning_records / total_records) * 20.0
        normalization_score = max(0.0, round(100.0 - norm_penalty, 2))

        # 4. Validation Score
        val_penalty = ((error_records * 2.0 + warning_records) / (total_records * 2.0)) * 100.0
        validation_score = max(0.0, round(100.0 - val_penalty, 2))

        # 5. Completeness Score
        if total_cells > 0:
            completeness_score = max(0.0, round(100.0 - (null_cell_count / total_cells) * 100.0, 2))
        else:
            completeness_score = 95.0

        # 6. Consistency Score
        conflict_penalty = min(conflict_count * 10.0, 50.0)
        consistency_score = max(0.0, round(100.0 - conflict_penalty, 2))

        # 7. Curation Score
        if curation_processed:
            cur_penalty = (review_required_count / total_records) * 50.0
            curation_score = max(0.0, round(100.0 - cur_penalty, 2))
        else:
            curation_score = 50.0

        # 8. Provenance Score
        prov_penalty = (provenance_missing_count / total_records) * 100.0
        provenance_score = max(0.0, round(100.0 - prov_penalty, 2))

        # Overall composite score
        overall = (
            extraction_score * cls.DIMENSION_WEIGHTS["extraction"]
            + structural_score * cls.DIMENSION_WEIGHTS["structural"]
            + normalization_score * cls.DIMENSION_WEIGHTS["normalization"]
            + validation_score * cls.DIMENSION_WEIGHTS["validation"]
            + completeness_score * cls.DIMENSION_WEIGHTS["completeness"]
            + consistency_score * cls.DIMENSION_WEIGHTS["consistency"]
            + curation_score * cls.DIMENSION_WEIGHTS["curation"]
            + provenance_score * cls.DIMENSION_WEIGHTS["provenance"]
        )
        overall = round(overall, 2)

        # Evaluate the 10 Universal Research Gates
        gates: Dict[str, str] = {}
        reasons: List[str] = []

        # Gate 1: Document Understanding Gate
        gates["document_understanding_gate"] = "passed" if document_profile_valid else "failed"
        if not document_profile_valid:
            reasons.append("Document understanding gate failed: Document structure and metadata unresolved.")

        # Gate 2: Dataset Identification Gate
        gates["dataset_identification_gate"] = "passed" if dataset_identified else "failed"
        if not dataset_identified:
            reasons.append("Dataset identification gate failed: Target dataset not resolved from candidate tables.")

        # Gate 3: Structural Integrity Gate
        gates["structural_integrity_gate"] = "passed" if structural_score >= 70.0 else "warning"

        # Gate 4: Schema Gate
        if has_generic_columns:
            gates["schema_gate"] = "failed"
            reasons.append("Schema gate failed: generic column_1/column_2 names detected instead of domain attributes.")
        else:
            gates["schema_gate"] = "passed"

        # Gate 5: Normalization Gate
        gates["normalization_gate"] = "passed" if normalization_score >= 75.0 else "warning"

        # Gate 6: Validation Gate
        if error_records == 0:
            gates["validation_gate"] = "passed"
        else:
            gates["validation_gate"] = "failed" if error_records > 5 else "warning"
            reasons.append(f"{error_records} schema or business rule validation error(s) detected.")

        # Gate 7: Curation Gate
        if not curation_processed:
            gates["curation_gate"] = "partially_processed"
            reasons.append("Curation gate notice: records are in unprocessed state.")
        elif review_required_count == 0:
            gates["curation_gate"] = "passed"
        else:
            gates["curation_gate"] = "requires_review"
            reasons.append(f"{review_required_count} record(s) flagged for human review.")

        # Gate 8: Evidence Gate
        gates["evidence_gate"] = "passed" if curation_processed else "pending"

        # Gate 9: Provenance Gate
        gates["provenance_gate"] = "passed" if provenance_missing_count == 0 else "warning"

        # Gate 10: Review Gate
        critical_issues = error_records + conflict_count
        if critical_issues == 0 and review_required_count == 0:
            gates["review_gate"] = "passed"
        elif critical_issues == 0:
            gates["review_gate"] = "warning"
        else:
            gates["review_gate"] = "failed"
            reasons.append(f"{critical_issues} critical unreviewed issues must be addressed.")

        # Backwards-compatibility gate aliases
        gates["extraction_gate"] = gates.get("document_understanding_gate", "passed")
        gates["structural_gate"] = gates.get("structural_integrity_gate", "passed")
        gates["export_gate"] = "ready" if (error_records == 0 and conflict_count == 0 and not has_generic_columns) else "blocked"

        # Determine Export Status
        can_clean = error_records == 0 and conflict_count == 0 and not has_generic_columns
        can_research = True

        export_status = "PRODUCTION_READY"
        if has_generic_columns or not dataset_identified or error_records > 5:
            export_status = "BLOCKED"
        elif not curation_processed:
            export_status = "PARTIALLY_PROCESSED"
        elif review_required_count > 0 or warning_records > 0 or conflict_count > 0:
            export_status = "REQUIRES_REVIEW"

        dim_scores = QualityDimensionScores(
            extraction=extraction_score,
            structural=structural_score,
            normalization=normalization_score,
            validation=validation_score,
            completeness=completeness_score,
            consistency=consistency_score,
            curation=curation_score,
            provenance=provenance_score,
            overall=overall,
        )

        return QualityEvaluationResult(
            dimensions=dim_scores,
            overall_score=overall,
            gates=gates,
            critical_issues_count=critical_issues,
            warning_count=warning_records + review_required_count,
            can_export_clean=can_clean,
            can_export_research=can_research,
            export_status=export_status,
            reasons=reasons,
        )
