from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Tuple


class ReconstructedTable:
    """Represents a clean, logically unified table reconstructed across multiple pages."""

    def __init__(
        self,
        table_id: str,
        caption: str,
        headers: List[str],
        rows: List[List[str]],
        page_start: int,
        page_end: int,
        row_provenance: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.95,
    ):
        self.table_id = table_id
        self.caption = caption
        self.headers = headers
        self.rows = rows
        self.page_start = page_start
        self.page_end = page_end
        self.row_provenance = row_provenance or []
        self.confidence = confidence


class TableReconstructor:
    """Reconstructs multi-page tables, removes repeated running headers, heals continuation rows,
    and strips layout artifacts (running headers/footers, margin numbers)."""

    QUALIFICATION_KEYWORDS = [
        "nqf level", "diploma", "degree", "certificate", "advanced certificate",
        "postgraduate", "honours", "bachelor", "master", "doctoral", "no formal qualification",
        "professional driving permit", "occupational certificate", "trade test"
    ]

    @classmethod
    def clean_cell_text(cls, text: Optional[str]) -> str:
        if not text:
            return ""
        s = str(text)
        # Collapse excessive newlines and tabs
        s = re.sub(r"[\r\n\t]+", " ", s)
        # Replace non-breaking spaces
        s = s.replace("\u00a0", " ").replace("\u200b", "")
        # Normalize quotes
        s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
        return " ".join(s.split()).strip()

    @classmethod
    def is_header_row_match(cls, row: List[str], reference_headers: List[str]) -> bool:
        if not row or not reference_headers:
            return False
        clean_row = [cls.clean_cell_text(c).lower() for c in row if c]
        clean_ref = [cls.clean_cell_text(h).lower() for h in reference_headers if h]
        if not clean_row or not clean_ref:
            return False
        matches = sum(1 for c in clean_row if any(r == c or r in c or c in r for r in clean_ref))
        return (matches / max(len(clean_ref), 1)) >= 0.50

    @classmethod
    def is_margin_or_footnote_artifact(cls, row: List[str]) -> bool:
        """Detects footnote text or running header captured as a table row."""
        if not row:
            return True
        non_empty = [cls.clean_cell_text(c) for c in row if c and cls.clean_cell_text(c)]
        if not non_empty:
            return True
        full_text = " ".join(non_empty).lower()

        # Footnote indicators e.g. "8 Interquartile range...", "9 Upper outlier...", "Note: Data..."
        if re.match(r"^(?:\d+\s+)?(?:interquartile|upper outlier|source:|note:|footnote:)", full_text):
            return True
        # Running headers e.g. "CONSOLIDATION OF EVIDENCE AND THE FINAL LIST 27"
        if re.search(r"\b(consolidation of evidence|technical research report|list of occupations in high demand)\b", full_text) and len(non_empty) <= 2:
            return True

        return False

    @classmethod
    def split_occupation_and_qualification(cls, text: str) -> Tuple[str, str]:
        """Separates an occupation title and a minimum qualification when merged in a single string."""
        clean_str = cls.clean_cell_text(text)
        # Check for qualification pattern
        pattern = re.compile(
            r"\b((?:Honours Degree|Postgraduate Diploma|Bachelor\'s Degree|Master\'s Degree|Doctoral Degree|Diploma|National Certificate|Advanced Certificate|Advanced Diploma|Higher Certificate|Intermediate Certificate|Professional Driving Permit|No Formal Qualification Required|General Education and Training Certificate).*)$",
            re.IGNORECASE,
        )
        match = pattern.search(clean_str)
        if match:
            qual = match.group(1).strip()
            occ = clean_str[:match.start()].strip()
            # Clean trailing footnote or running footer from qual
            qual = re.sub(r"\s+\d+\s+MPUMALANGA.*$", "", qual, flags=re.IGNORECASE).strip()
            return occ, qual
        return clean_str, ""

    @staticmethod
    def _get_val(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @classmethod
    def reconstruct_from_text_lines(
        cls,
        pages_text: List[Tuple[int, str]],
        target_caption: str,
        start_page: int,
        end_page: int,
        unit_of_observation: Optional[str] = "occupation",
    ) -> ReconstructedTable:
        """Reconstructs structured multi-page records directly from text layouts
        when vector line borders are missing or disrupted by shading."""
        if unit_of_observation == "qualification":
            headers = ["saqa_id", "qualification_title", "nqf_level"]
            code_pattern = re.compile(r"^\b(\d{4,7})\b\s+(.*)$")
        else:
            headers = ["ofo_code", "occupation_title", "minimum_qualification_required"]
            code_pattern = re.compile(r"^\b((?:20\d{2}-)?\d{4,6})\b\s+(.*)$")

        rows: List[List[str]] = []
        provenance: List[Dict[str, Any]] = []

        current_record: Optional[Dict[str, Any]] = None

        for page_num, text in pages_text:
            if page_num < start_page or page_num > end_page:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            for line in lines:
                # Filter out running page header, footer, and table header repeats
                if any(h in line.upper() for h in ["TABLE ", "OFO CODE", "MINIMUM QUALIFICATION", "CONSOLIDATION OF EVIDENCE", "TECHNICAL RESEARCH REPORT"]):
                    continue
                if re.match(r"^\d+\s+(Interquartile|Upper outlier|MPUMALANGA|Source:|Note:)", line, re.IGNORECASE):
                    continue

                code_match = code_pattern.match(line)
                if code_match:
                    if current_record:
                        occ, qual = cls.split_occupation_and_qualification(current_record["raw_rest"])
                        rows.append([current_record["code"], occ, qual])
                        provenance.append({
                            "page_number": current_record["page"],
                            "row_index": len(rows),
                            "raw_text": f"{current_record['code']} {current_record['raw_rest']}",
                        })

                    code = code_match.group(1)
                    raw_rest = code_match.group(2)
                    current_record = {
                        "page": page_num,
                        "code": code,
                        "raw_rest": raw_rest,
                    }
                elif current_record:
                    # Continuation of qualification or title from previous wrapped line
                    current_record["raw_rest"] += " " + line

        # Add the final trailing record
        if current_record:
            occ, qual = cls.split_occupation_and_qualification(current_record["raw_rest"])
            rows.append([current_record["code"], occ, qual])
            provenance.append({
                "page_number": current_record["page"],
                "row_index": len(rows),
                "raw_text": f"{current_record['code']} {current_record['raw_rest']}",
            })

        return ReconstructedTable(
            table_id="reconstructed_table",
            caption=target_caption,
            headers=headers,
            rows=rows,
            page_start=start_page,
            page_end=end_page,
            row_provenance=provenance,
            confidence=0.98,
        )

    @classmethod
    def reconstruct_table(
        cls,
        raw_tables: List[Any],
        target_caption: str = "",
        pages_text: Optional[List[Tuple[int, str]]] = None,
        unit_of_observation: Optional[str] = "occupation",
    ) -> ReconstructedTable:
        """Reconstructs a table from raw tables across pages, healing headers and multi-line cells.
        Falls back to text layout reconstruction if raw tables suffer from cell dropping due to shading."""
        if not raw_tables:
            return ReconstructedTable(
                table_id="empty_table",
                caption=target_caption,
                headers=[],
                rows=[],
                page_start=1,
                page_end=1,
            )

        page_start = min(cls._get_val(t, "page_number", 1) for t in raw_tables)
        page_end = max(cls._get_val(t, "page_number", 1) for t in raw_tables)

        # Primary reference headers
        first_table = raw_tables[0]
        headers = [cls.clean_cell_text(h) for h in cls._get_val(first_table, "headers", [])]

        # Check if this table has missing cells due to shading (e.g. 35%+ first cells are None/Empty while page text has codes)
        all_first_cells = [
            r[0] for t in raw_tables for r in cls._get_val(t, "rows", []) if r and len(r) > 0
        ]
        empty_first_cells = sum(1 for c in all_first_cells if not c or not str(c).strip() or str(c).strip().lower() == "none")

        if len(all_first_cells) > 10 and (empty_first_cells / len(all_first_cells)) >= 0.35 and pages_text:
            # Table is shaded or has missing column boundaries; use high-fidelity text reconstruction
            return cls.reconstruct_from_text_lines(pages_text, target_caption, page_start, page_end, unit_of_observation=unit_of_observation)

        # Standard grid reconstruction
        reconstructed_rows: List[List[str]] = []
        provenance: List[Dict[str, Any]] = []

        for t in raw_tables:
            p_no = cls._get_val(t, "page_number", 1)
            t_rows = cls._get_val(t, "rows", [])
            for r_idx, row in enumerate(t_rows):
                if cls.is_header_row_match(row, headers):
                    continue
                if cls.is_margin_or_footnote_artifact(row):
                    continue

                cleaned_row = [cls.clean_cell_text(c) for c in row]
                if not any(cleaned_row):
                    continue

                reconstructed_rows.append(cleaned_row)
                provenance.append({
                    "page_number": p_no,
                    "row_index": len(reconstructed_rows),
                    "raw_row": row,
                })

        return ReconstructedTable(
            table_id="reconstructed_table",
            caption=target_caption,
            headers=headers,
            rows=reconstructed_rows,
            page_start=page_start,
            page_end=page_end,
            row_provenance=provenance,
            confidence=0.92,
        )
