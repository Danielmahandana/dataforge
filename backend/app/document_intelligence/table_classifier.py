from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from backend.app.document_intelligence.document_profile import (
    SemanticTableRole,
    TableMetadata,
    SectionNode,
    UnitOfObservation,
)
from backend.app.document_intelligence.unit_of_observation import UnitOfObservationDetector


class TableClassifier:
    """Discovers table captions, eliminates decorative/layout artifacts, and classifies table semantic roles."""

    FINAL_DATASET_INDICATORS = [
        "final list", "final oihd", "occupations in high demand",
        "selected occupations", "authoritative list", "final dataset",
        "oihd in mpumalanga", "priority skills list", "master list"
    ]

    SURVEY_INDICATORS = [
        "survey response mapping", "survey responses", "survey questions",
        "employer survey", "respondents", "survey sample", "questionnaire"
    ]

    INTERMEDIATE_INDICATORS = [
        "top 10", "variables used", "historical overview", "indicators used",
        "regression results", "sample description", "scoring range", "demand score ranges"
    ]

    METADATA_INDICATORS = [
        "acronyms", "abbreviations", "table of contents", "list of tables",
        "list of figures", "document history", "version control"
    ]

    @classmethod
    def extract_caption_near_table(cls, page_text: str, table_headers: List[str]) -> str:
        """Finds table caption like 'Table 4: The final list...' from page text."""
        caption_patterns = [
            r"(TABLE\s+\d+[:\.\-]\s+[^\n\r]+)",
            r"(Table\s+\d+[:\.\-]\s+[^\n\r]+)",
            r"(Annexure\s+\d+[:\.\-]\s+[^\n\r]+)",
            r"(ANNEXURE\s+\d+[:\.\-]\s+[^\n\r]+)",
            r"(Appendix\s+[A-Z0-9]+[:\.\-]\s+[^\n\r]+)",
        ]
        for pat in caption_patterns:
            matches = re.findall(pat, page_text, re.IGNORECASE)
            if matches:
                # Return the most plausible caption
                for m in matches:
                    clean_m = str(m).strip()
                    if len(clean_m) > 7 and not clean_m.lower().startswith("table of contents"):
                        return clean_m
        return ""

    @classmethod
    def is_layout_or_decorative(cls, rows: List[List[str]]) -> bool:
        """Checks if an extracted table is merely a layout border or decorative artifact."""
        if not rows:
            return True
        total_cells = sum(len(r) for r in rows)
        if total_cells <= 2:
            return True

        non_empty = [c for r in rows for c in r if c and str(c).strip()]
        if len(non_empty) <= 1:
            return True

        # Check if entire table is just copyright or page header/footer
        full_text = " ".join(str(c) for c in non_empty).lower()
        if len(rows) <= 3 and any(k in full_text for k in ["© published in", "private bag x174", "isbn:", "all rights reserved"]):
            return True

        return False

    @classmethod
    def is_acronym_table(cls, headers: List[str], rows: List[List[str]]) -> bool:
        """Checks if a table is an acronym or abbreviation glossary."""
        if len(headers) == 2 or (rows and len(rows[0]) == 2):
            sample = rows[:10]
            acronym_like = sum(
                1 for r in sample
                if len(r) >= 2 and re.match(r"^[A-Z0-9\-\&]{2,8}$", str(r[0]).strip()) and len(str(r[1]).split()) >= 2
            )
            if len(sample) > 0 and (acronym_like / len(sample)) >= 0.70:
                return True
        return False

    @classmethod
    def classify_table(
        cls,
        table_id: str,
        page_num: int,
        headers: List[str],
        rows: List[List[str]],
        page_text: str,
        current_section: Optional[SectionNode] = None,
    ) -> TableMetadata:
        caption = cls.extract_caption_near_table(page_text, headers)
        raw_caption = caption

        clean_sample_3 = [[str(c) if c is not None else "" for c in r] for r in rows[:3]]
        clean_sample_5 = [[str(c) if c is not None else "" for c in r] for r in rows[:5]]

        # Check if layout artifact
        if cls.is_layout_or_decorative(rows):
            return TableMetadata(
                table_id=table_id,
                page_start=page_num,
                page_end=page_num,
                caption=caption,
                raw_caption=raw_caption,
                section_id=current_section.section_id if current_section else None,
                section_title=current_section.title if current_section else None,
                column_count=len(headers),
                row_count=len(rows),
                headers=headers,
                table_type="LAYOUT_ARTIFACT",
                structural_confidence=0.1,
                semantic_role=SemanticTableRole.METADATA,
                unit_of_observation=UnitOfObservation.UNKNOWN,
                evidence_signals=["Table determined to be a decorative layout border or metadata box."],
                sample_rows=clean_sample_3,
            )

        # Check for acronyms
        if cls.is_acronym_table(headers, rows) or "acronym" in caption.lower():
            return TableMetadata(
                table_id=table_id,
                page_start=page_num,
                page_end=page_num,
                caption=caption or "Acronyms and Abbreviations",
                raw_caption=raw_caption,
                section_id=current_section.section_id if current_section else None,
                section_title=current_section.title if current_section else None,
                column_count=len(headers),
                row_count=len(rows),
                headers=headers,
                table_type="STANDARD",
                structural_confidence=0.9,
                semantic_role=SemanticTableRole.METADATA,
                unit_of_observation=UnitOfObservation.UNKNOWN,
                evidence_signals=["Acronym glossary table mapping abbreviations to organizational titles."],
                sample_rows=clean_sample_3,
            )

        # Detect Unit of Observation
        unit = UnitOfObservationDetector.detect(headers, rows, caption=caption)

        # Classify Semantic Role
        role = SemanticTableRole.UNKNOWN
        signals: List[str] = []

        combined_search = f"{caption} {current_section.title if current_section else ''} {' '.join(headers)}".lower()

        # Check if survey questions or response mapping
        is_survey = (
            unit == UnitOfObservation.SURVEY_RESPONSE
            or any(k in combined_search for k in cls.SURVEY_INDICATORS)
        )
        if is_survey:
            role = SemanticTableRole.SURVEY
            signals.append("Matched survey responses or questionnaire structure.")

        # Check if Final Dataset
        elif any(k in combined_search for k in cls.FINAL_DATASET_INDICATORS) and unit in [UnitOfObservation.OCCUPATION, UnitOfObservation.QUALIFICATION]:
            role = SemanticTableRole.FINAL_DATASET
            signals.append("Explicit 'final list' / 'occupations in high demand' in caption or section with occupational schema.")

        # Check if Appendix
        elif (current_section and current_section.semantic_type == "APPENDIX") or any(k in combined_search for k in ["annexure", "appendix"]):
            role = SemanticTableRole.APPENDIX
            signals.append("Located within Appendix / Annexure section.")

        # Check if Intermediate Analysis
        elif any(k in combined_search for k in cls.INTERMEDIATE_INDICATORS):
            role = SemanticTableRole.INTERMEDIATE_ANALYSIS
            signals.append("Intermediate analytical indicators, sample description, or diagnostic rankings.")

        # Check if Methodology
        elif current_section and current_section.semantic_type == "METHODOLOGY":
            role = SemanticTableRole.METHODOLOGY
            signals.append("Located within Methodology section.")

        # Check if Evidence
        elif current_section and current_section.semantic_type == "EVIDENCE":
            role = SemanticTableRole.EVIDENCE
            signals.append("Located within Evidence section.")

        else:
            role = SemanticTableRole.UNKNOWN
            signals.append("Role could not be determined with high certainty.")

        return TableMetadata(
            table_id=table_id,
            page_start=page_num,
            page_end=page_num,
            caption=caption,
            raw_caption=raw_caption,
            section_id=current_section.section_id if current_section else None,
            section_title=current_section.title if current_section else None,
            column_count=len(headers),
            row_count=len(rows),
            headers=headers,
            table_type="STANDARD",
            structural_confidence=0.85 if role != SemanticTableRole.UNKNOWN else 0.50,
            semantic_role=role,
            unit_of_observation=unit,
            evidence_signals=signals,
            sample_rows=clean_sample_5,
        )
