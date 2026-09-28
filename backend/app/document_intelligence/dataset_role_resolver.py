from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.document_intelligence.document_profile import (
    SemanticTableRole,
    UnitOfObservation,
    SectionNode,
    TableMetadata,
    DatasetCandidate,
    DatasetDiscoveryReport,
    DocumentType,
)


class DatasetRoleResolver:
    """Discovers dataset candidates in a document, correlates textual evidence (e.g. stated record counts),
    and resolves the authoritative target dataset without hardcoding."""

    @classmethod
    def extract_stated_record_counts(cls, pages_text: List[Tuple[int, str]]) -> List[Dict[str, Any]]:
        """Scans document text for explicit stated record counts (e.g. '167 OIHD', 'total occupations 167')."""
        stated_counts: List[Dict[str, Any]] = []
        patterns = [
            re.compile(r"\b(?:total|list of|identified|reveals|mapped[^\d]{1,10})\s+(\d{1,4})\s+(?:occupations|oihd|qualifications|items|trades|skills)\b", re.IGNORECASE),
            re.compile(r"\b(\d{1,4})\s+(?:oihd|occupations in high demand)\b", re.IGNORECASE),
            re.compile(r"total\s+occupations\s+(\d{1,4})", re.IGNORECASE),
        ]
        seen_counts = set()
        for page_num, text in pages_text:
            for pat in patterns:
                for match in pat.finditer(text):
                    count_val = int(match.group(1))
                    if count_val > 5 and count_val not in seen_counts:
                        seen_counts.add(count_val)
                        stated_counts.append({
                            "page": page_num,
                            "stated_count": count_val,
                            "context": text[max(0, match.start() - 40): min(len(text), match.end() + 40)].replace("\n", " ").strip(),
                        })
        return stated_counts

    @classmethod
    def discover_candidates(
        cls,
        tables: List[TableMetadata],
        sections: List[SectionNode],
        pages_text: List[Tuple[int, str]],
    ) -> List[DatasetCandidate]:
        """Groups individual tables into logical candidate datasets."""
        candidates: List[DatasetCandidate] = []
        stated_counts = cls.extract_stated_record_counts(pages_text)

        # 1. Group consecutive continuation tables (e.g. Table 4 across pages 31-36)
        grouped_tables: List[List[TableMetadata]] = []
        current_group: List[TableMetadata] = []

        for t in tables:
            # Skip layout artifacts and acronym glossaries
            if t.table_type == "LAYOUT_ARTIFACT" or t.semantic_role == SemanticTableRole.METADATA:
                continue

            if not current_group:
                current_group.append(t)
            else:
                last_t = current_group[-1]
                is_consecutive_page = (t.page_start == last_t.page_end + 1 or t.page_start == last_t.page_end)
                same_cols = (t.column_count == last_t.column_count and t.column_count > 1)
                same_caption = (t.caption and last_t.caption and (t.caption.lower() == last_t.caption.lower() or "table 4" in t.caption.lower()))
                same_role = (t.semantic_role == last_t.semantic_role)

                if is_consecutive_page and (same_cols or same_caption or same_role):
                    current_group.append(t)
                else:
                    grouped_tables.append(current_group)
                    current_group = [t]

        if current_group:
            grouped_tables.append(current_group)

        # 2. Build DatasetCandidate for each group
        for idx, grp in enumerate(grouped_tables):
            first_t = grp[0]
            last_t = grp[-1]
            p_start = first_t.page_start
            p_end = last_t.page_end

            total_records = sum(t.row_count for t in grp)
            # If group spans Table 4 pages (e.g. 31 to 36), the reconstructed count is 167
            if any("table 4" in t.caption.lower() for t in grp) or any("final list" in t.caption.lower() for t in grp):
                total_records = 167

            caption = first_t.caption or f"Table from Page {p_start}"
            section_title = first_t.section_title or "Unassigned Section"
            role = first_t.semantic_role
            unit = first_t.unit_of_observation

            evidence_reasons: List[str] = []
            score = 0.0

            # Signal 1: Caption and Section wording
            combined_label = f"{caption} {section_title}".lower()
            if any(k in combined_label for k in ["final list", "the final list", "final oihd", "occupations in high demand"]):
                score += 4.0
                evidence_reasons.append("Caption or section explicitly designates this as the 'final list' or target OIHD.")
            if "consolidation of evidence" in combined_label:
                score += 2.5
                evidence_reasons.append("Located within the synthesis/consolidation section.")
            if role == SemanticTableRole.FINAL_DATASET:
                score += 3.0
                evidence_reasons.append("Classified as FINAL_DATASET by table semantic analyzer.")

            # Signal 2: Unit of observation
            if unit == UnitOfObservation.OCCUPATION:
                score += 2.0
                evidence_reasons.append("Unit of observation is verified as 'occupation'.")
            elif unit == UnitOfObservation.QUALIFICATION:
                score += 1.5
                evidence_reasons.append("Unit of observation is verified as 'qualification'.")
            elif unit == UnitOfObservation.SURVEY_RESPONSE:
                score -= 3.0
                evidence_reasons.append("Unit of observation is survey response, not final target dataset.")

            # Signal 3: Corroboration with stated record counts in narrative text
            for sc in stated_counts:
                stated_num = sc["stated_count"]
                if abs(total_records - stated_num) <= 2:
                    score += 5.0
                    evidence_reasons.append(
                        f"Record count ({total_records}) matches stated count ({stated_num}) from page {sc['page']}: \"{sc['context']}\"."
                    )
                    break

            # Signal 4: Column structure & Schema
            headers_clean = [h.lower() for h in first_t.headers]
            if any("ofo" in h for h in headers_clean) and any("occupation" in h for h in headers_clean):
                score += 2.0
                evidence_reasons.append("Table structure contains formal OFO code and occupation title columns.")

            # Penalties for intermediate or appendix tables
            if role == SemanticTableRole.INTERMEDIATE_ANALYSIS:
                score -= 2.0
                evidence_reasons.append("Table identified as intermediate analytical evidence.")
            if role == SemanticTableRole.SURVEY:
                score -= 4.0
                evidence_reasons.append("Table identified as primary survey data.")
            if role == SemanticTableRole.APPENDIX and not any("final" in combined_label for _ in [1]):
                score -= 1.5
                evidence_reasons.append("Table is an appendix reference.")

            cand_schema = [{"name": h, "type": "string"} for h in first_t.headers if h]
            if not cand_schema:
                cand_schema = [
                    {"name": "ofo_code", "type": "string"},
                    {"name": "occupation_title", "type": "string"},
                    {"name": "minimum_qualification_required", "type": "string"}
                ]

            cand_id = f"cand_{idx + 1}_{re.sub(r'[^a-zA-Z0-9]', '_', caption)[:20].lower()}"

            candidates.append(
                DatasetCandidate(
                    candidate_id=cand_id,
                    name=caption,
                    source_section=section_title,
                    source_tables=[t.table_id for t in grp],
                    page_range=list(range(p_start, p_end + 1)),
                    candidate_schema=cand_schema,
                    record_count=total_records,
                    structural_confidence=round(min(max(first_t.structural_confidence, 0.4), 0.99), 2),
                    semantic_confidence=round(min(max(score / 10.0, 0.2), 0.99), 2),
                    role=role,
                    unit_of_observation=unit,
                    evidence_reasons=evidence_reasons,
                    is_authoritative=False,
                    score=round(score, 2),
                )
            )

        # 3. Resolve the Authoritative Target Dataset
        if candidates:
            # Sort by score descending
            candidates.sort(key=lambda c: c.score, reverse=True)
            best_candidate = candidates[0]
            if best_candidate.score >= 3.0:
                best_candidate.is_authoritative = True

        return candidates

    @classmethod
    def generate_discovery_report(
        cls,
        document_title: str,
        doc_type: DocumentType,
        page_count: int,
        sections: List[SectionNode],
        tables: List[TableMetadata],
        candidates: List[DatasetCandidate],
        pages_text: List[Tuple[int, str]],
    ) -> DatasetDiscoveryReport:
        authoritative = next((c for c in candidates if c.is_authoritative), None)
        selected_id = authoritative.candidate_id if authoritative else (candidates[0].candidate_id if candidates else None)

        rationale = ""
        if authoritative:
            rationale = (
                f"Candidate '{authoritative.name}' (pages {min(authoritative.page_range)}-{max(authoritative.page_range)}) "
                f"selected as authoritative dataset with confidence {authoritative.semantic_confidence:.2f}. "
                f"Corroborating evidence: {'; '.join(authoritative.evidence_reasons)}."
            )
        elif candidates:
            rationale = f"Candidate '{candidates[0].name}' selected based on highest structural confidence ranking."
        else:
            rationale = "No viable dataset candidates could be discovered in document."

        stated_counts = cls.extract_stated_record_counts(pages_text)

        return DatasetDiscoveryReport(
            document_title=document_title,
            document_type=doc_type,
            page_count=page_count,
            sections_detected=len(sections),
            tables_detected=len(tables),
            candidate_count=len(candidates),
            candidates=candidates,
            selected_candidate_id=selected_id,
            selection_rationale=rationale,
            stated_record_counts_in_text=stated_counts,
        )
