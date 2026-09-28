from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.document_intelligence.document_profile import SectionNode


class SectionDetector:
    """Discovers hierarchical sections, headings, annexures, and structural boundaries in documents.
    Preserves exact verbatim source headings while assigning normalized semantic types."""

    SEMANTIC_KEYWORDS = {
        "FRONT_MATTER": ["acknowledgements", "table of contents", "contents", "list of figures", "list of tables", "acronyms", "abbreviations"],
        "INTRODUCTION": ["introduction", "background", "executive summary", "context", "overview", "purpose", "scope"],
        "METHODOLOGY": ["methodology", "research method", "methods", "approach", "study design", "data collection", "evolution of the methodology", "evolution", "analytical framework"],
        "EVIDENCE": ["secondary data analysis", "primary data analysis", "survey data", "labour market", "labour market and economy", "evidence", "indicators", "demand score"],
        "FINAL_LIST": ["consolidation of evidence and the final list", "consolidation", "the final list", "final list", "occupations in high demand", "selected occupations", "target dataset", "final oihd"],
        "RESULTS": ["results", "findings", "key findings", "analysis"],
        "CONCLUSION": ["conclusion", "recommendations", "policy implications", "summary"],
        "APPENDIX": ["annexure", "annexures", "appendix", "appendices", "survey questions", "survey response mapping"],
        "REFERENCES": ["references", "bibliography", "works cited"],
    }

    @classmethod
    def classify_heading_semantics(cls, heading_text: str) -> str:
        h_lower = heading_text.lower().strip()
        for sem_type, keywords in cls.SEMANTIC_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", h_lower):
                    return sem_type
        return "UNKNOWN"

    @classmethod
    def detect_sections(cls, pages_text: List[Tuple[int, str]]) -> List[SectionNode]:
        """Detects section nodes from a list of (page_number, text) tuples."""
        raw_sections: List[Dict[str, Any]] = []

        # Patterns for headings
        part_pattern = re.compile(r"^(PART\s+[0-9IVXLCDM]+)\b", re.IGNORECASE)
        annex_pattern = re.compile(r"^(ANNEXURE\s+[0-9A-Z]+|APPENDIX\s+[0-9A-Z]+)\b", re.IGNORECASE)
        numbered_pattern = re.compile(r"^(\d+\.\d+(\.\d+)?)\s+([A-Z][A-Za-z0-9\s,\-\(\)\'\’]+)$")
        major_num_pattern = re.compile(r"^(\d+)\s+([A-Z\s]{4,})$")
        front_matter_pattern = re.compile(r"^(Table of Contents|Acknowledgements|List of Figures|List of Tables|Acronyms and Abbreviations)$", re.IGNORECASE)

        toc_mode = False
        for page_num, text in pages_text:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if any(l.lower() in ["table of contents", "contents"] for l in lines[:3]):
                toc_mode = True
            elif page_num > 7:
                toc_mode = False

            # If inside TOC pages, don't treat listing items as section bodies on this page
            if toc_mode:
                if any(l.lower() in ["table of contents", "contents"] for l in lines[:3]):
                    raw_sections.append({
                        "raw_heading": "Table of Contents",
                        "title": "Table of Contents",
                        "level": 1,
                        "page_start": page_num,
                        "semantic_type": "FRONT_MATTER",
                    })
                continue

            for line_idx, line in enumerate(lines[:15]):  # Headings typically appear near top of page
                # Filter out running headers like "2 MPUMALANGA'S LIST..." or page numbers
                if re.match(r"^\d+\s+[A-Z\s\’\']+$", line) and len(line.split()) > 4 and page_num > 5:
                    continue
                if re.match(r"^[A-Z\s\’\']+\s+\d+$", line) and len(line.split()) > 4 and page_num > 5:
                    continue

                part_match = part_pattern.match(line)
                annex_match = annex_pattern.match(line)
                num_match = numbered_pattern.match(line)
                major_match = major_num_pattern.match(line)
                front_match = front_matter_pattern.match(line)

                if part_match:
                    # Look ahead for subtitle on next line
                    subtitle = ""
                    if line_idx + 1 < len(lines):
                        next_line = lines[line_idx + 1]
                        if not any(k in next_line.lower() for k in ["part ", "annexure", "page "]) and len(next_line) < 100:
                            subtitle = f": {next_line}"
                    full_title = f"{line}{subtitle}".strip()
                    raw_sections.append({
                        "raw_heading": line,
                        "title": full_title,
                        "level": 1,
                        "page_start": page_num,
                        "semantic_type": cls.classify_heading_semantics(full_title),
                    })
                elif annex_match:
                    full_title = line
                    if line_idx + 1 < len(lines) and ":" not in line:
                        next_line = lines[line_idx + 1]
                        if len(next_line) < 120:
                            full_title = f"{line}: {next_line}"
                    raw_sections.append({
                        "raw_heading": line,
                        "title": full_title,
                        "level": 4,
                        "page_start": page_num,
                        "semantic_type": "APPENDIX",
                    })
                elif front_match:
                    raw_sections.append({
                        "raw_heading": line,
                        "title": line,
                        "level": 1,
                        "page_start": page_num,
                        "semantic_type": cls.classify_heading_semantics(line),
                    })
                elif num_match:
                    raw_sections.append({
                        "raw_heading": line,
                        "title": line,
                        "level": 2 if line.count(".") == 1 else 3,
                        "page_start": page_num,
                        "semantic_type": cls.classify_heading_semantics(line),
                    })
                elif major_match and not any(k in line.lower() for k in ["figure", "table"]):
                    raw_sections.append({
                        "raw_heading": line,
                        "title": line,
                        "level": 1,
                        "page_start": page_num,
                        "semantic_type": cls.classify_heading_semantics(line),
                    })

        if not raw_sections:
            # Fallback single root section
            total_pages = max([p for p, _ in pages_text], default=1)
            return [
                SectionNode(
                    section_id="sec_root",
                    title="Document Content",
                    raw_heading="Document Content",
                    level=1,
                    page_start=1,
                    page_end=total_pages,
                    semantic_type="GENERAL_CONTENT",
                )
            ]

        # Deduplicate consecutive identical headings on same page
        deduped: List[Dict[str, Any]] = []
        for s in raw_sections:
            if not deduped:
                deduped.append(s)
            else:
                last = deduped[-1]
                if last["title"].lower() != s["title"].lower() or last["page_start"] != s["page_start"]:
                    deduped.append(s)

        # Calculate page_end for each section
        total_pages = max([p for p, _ in pages_text], default=1)
        nodes: List[SectionNode] = []
        for idx, s in enumerate(deduped):
            next_start = deduped[idx + 1]["page_start"] if idx + 1 < len(deduped) else total_pages
            p_end = max(s["page_start"], next_start - 1 if idx + 1 < len(deduped) else total_pages)
            sec_id = f"sec_{idx + 1}_{re.sub(r'[^a-zA-Z0-9]', '_', s['title'])[:24].lower()}"
            nodes.append(
                SectionNode(
                    section_id=sec_id,
                    title=s["title"],
                    raw_heading=s["raw_heading"],
                    level=s["level"],
                    page_start=s["page_start"],
                    page_end=p_end,
                    semantic_type=s["semantic_type"],
                )
            )

        return nodes

    @classmethod
    def find_section_for_page(cls, sections: List[SectionNode], page_num: int) -> Optional[SectionNode]:
        """Finds the most specific section containing a page."""
        matching = [s for s in sections if s.page_start <= page_num <= s.page_end]
        if not matching:
            return None
        # Return most specific level
        return max(matching, key=lambda s: s.level)
