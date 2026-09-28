from __future__ import annotations
import os
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
import pdfplumber

from backend.app.document_intelligence.document_profile import (
    DocumentProfile,
    DocumentType,
    SectionNode,
    TableMetadata,
    DatasetCandidate,
    DatasetDiscoveryReport,
)
from backend.app.document_intelligence.section_detector import SectionDetector
from backend.app.document_intelligence.table_classifier import TableClassifier
from backend.app.document_intelligence.dataset_role_resolver import DatasetRoleResolver


class DocumentProfiler:
    """Universal profiler that discovers what a document is, how it is organized,
    and what datasets exist within it before extraction occurs."""

    @classmethod
    def calculate_file_hash(cls, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def extract_document_metadata(cls, first_pages_text: str) -> Dict[str, Optional[str]]:
        meta: Dict[str, Optional[str]] = {
            "title": None,
            "author": None,
            "publisher": None,
            "publication_date": None,
        }

        # Look for Title
        title_patterns = [
            r"([A-Z0-9\s\’\']+\:\s+A TECHNICAL RESEARCH REPORT)",
            r"(Mpumalanga[\’\']?s List of Occupations in High Demand[^\n\r]+)",
            r"([A-Z][A-Za-z0-9\s\’\']{10,80}\s+Report)",
        ]
        for pat in title_patterns:
            m = re.search(pat, first_pages_text, re.IGNORECASE)
            if m:
                meta["title"] = " ".join(m.group(1).split()).strip()
                break

        # Look for Publisher / Dept
        if "Department of Higher Education and Training" in first_pages_text:
            meta["publisher"] = "Department of Higher Education and Training (DHET)"
        elif "DNA Economics" in first_pages_text:
            meta["publisher"] = "DNA Economics"

        # Look for Year / Date
        date_match = re.search(r"\b(20\d{2})\b", first_pages_text)
        if date_match:
            meta["publication_date"] = date_match.group(1)

        # Look for Authors
        author_match = re.search(r"Authors\s*\n+([^\n]+(?:\n+[^\n]+){1,3})", first_pages_text, re.IGNORECASE)
        if author_match:
            authors = [a.strip() for a in author_match.group(1).split("\n") if a.strip()]
            meta["author"] = ", ".join(authors[:3])

        return meta

    @classmethod
    def infer_document_type(cls, text_sample: str, candidates: List[DatasetCandidate]) -> Tuple[DocumentType, float]:
        sample_lower = text_sample.lower()

        if "technical research report" in sample_lower or "research report" in sample_lower:
            return DocumentType.RESEARCH_REPORT, 0.95
        if "policy" in sample_lower and "framework" in sample_lower:
            return DocumentType.POLICY_DOCUMENT, 0.85
        if "codebook" in sample_lower or "variable name" in sample_lower:
            return DocumentType.CODEBOOK, 0.90
        if any(c.unit_of_observation.value == "qualification" for c in candidates):
            return DocumentType.QUALIFICATION_DATASET, 0.90
        if any(c.unit_of_observation.value == "occupation" for c in candidates):
            return DocumentType.OCCUPATIONAL_DATASET, 0.90
        if "survey report" in sample_lower:
            return DocumentType.SURVEY_REPORT, 0.85
        if "statistical" in sample_lower or "statistics south africa" in sample_lower:
            return DocumentType.STATISTICAL_REPORT, 0.85

        return DocumentType.UNKNOWN, 0.40

    @classmethod
    def profile_document(
        cls,
        file_path: str,
        document_id: str,
        pages_limit: Optional[int] = None,
    ) -> DocumentProfile:
        """Profiles the document, building structural tree, table metadata, and dataset discovery."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_hash = cls.calculate_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        ext = os.path.splitext(file_path)[1].lower().replace(".", "")

        file_type = "PDF" if ext == "pdf" else (ext.upper() if ext else "UNKNOWN")

        pages_text: List[Tuple[int, str]] = []
        raw_tables_collected: List[Tuple[int, int, List[str], List[List[str]]]] = []

        if file_type == "PDF":
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                scan_range = range(min(total_pages, pages_limit)) if pages_limit else range(total_pages)

                for p_idx in scan_range:
                    page = pdf.pages[p_idx]
                    page_num = p_idx + 1
                    t = page.extract_text() or ""
                    pages_text.append((page_num, t))

                    tabs = page.extract_tables()
                    for t_idx, tab in enumerate(tabs):
                        if tab and len(tab) > 0:
                            headers = [str(c).replace("\n", " ").strip() if c else f"Col_{i+1}" for i, c in enumerate(tab[0])]
                            data_rows = tab[1:] if len(tab) > 1 else tab
                            raw_tables_collected.append((page_num, t_idx, headers, data_rows))
        else:
            # Fallback for non-PDFs
            total_pages = 1
            pages_text.append((1, "Non-PDF file"))

        # Check for scanned pages / OCR requirement
        total_text_len = sum(len(t) for _, t in pages_text)
        is_scanned = total_text_len < 100 and total_pages > 0
        ocr_required = is_scanned

        # 1. Structure & Section Discovery
        sections = SectionDetector.detect_sections(pages_text)

        # 2. Table Discovery & Semantic Classification
        tables_meta: List[TableMetadata] = []
        for p_num, t_idx, headers, rows in raw_tables_collected:
            page_text = next((t for p, t in pages_text if p == p_num), "")
            cur_sec = SectionDetector.find_section_for_page(sections, p_num)
            table_id = f"tab_p{p_num}_{t_idx + 1}"
            meta = TableClassifier.classify_table(
                table_id=table_id,
                page_num=p_num,
                headers=headers,
                rows=rows,
                page_text=page_text,
                current_section=cur_sec,
            )
            tables_meta.append(meta)

        # 3. Candidate Dataset Discovery & Role Resolution
        candidates = DatasetRoleResolver.discover_candidates(tables_meta, sections, pages_text)

        # 4. Document Metadata & Type
        front_sample = " ".join([t for p, t in pages_text[:5]])
        doc_meta = cls.extract_document_metadata(front_sample)
        doc_type, doc_type_conf = cls.infer_document_type(front_sample, candidates)

        doc_title = doc_meta.get("title") or os.path.basename(file_path).rsplit(".", 1)[0]
        authoritative = next((c for c in candidates if c.is_authoritative), None)
        auth_id = authoritative.candidate_id if authoritative else None

        # 5. Discovery Report
        discovery_rep = DatasetRoleResolver.generate_discovery_report(
            document_title=doc_title,
            doc_type=doc_type,
            page_count=total_pages,
            sections=sections,
            tables=tables_meta,
            candidates=candidates,
            pages_text=pages_text,
        )

        return DocumentProfile(
            document_id=document_id,
            file_hash=file_hash,
            file_type=file_type,
            file_size_bytes=file_size,
            page_count=total_pages,
            has_text=not is_scanned,
            has_images=False,
            has_tables=len(tables_meta) > 0,
            has_scanned_pages=is_scanned,
            ocr_required=ocr_required,
            language="en",
            title=doc_title,
            author=doc_meta.get("author"),
            publisher=doc_meta.get("publisher"),
            publication_date=doc_meta.get("publication_date"),
            document_type=doc_type,
            document_type_confidence=doc_type_conf,
            estimated_structure=f"{len(sections)} sections, {len(tables_meta)} tables, {len(candidates)} candidate datasets",
            estimated_dataset_count=len(candidates),
            sections=sections,
            tables=tables_meta,
            dataset_candidates=candidates,
            authoritative_dataset_id=auth_id,
            discovery_report=discovery_rep,
        )
