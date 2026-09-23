from __future__ import annotations
import re
import logging
from typing import List, Dict, Any, Tuple
from backend.app.extractors.base import RawTable

logger = logging.getLogger("dataforge.pipeline.healer")


class TableHealer:
    """Enterprise table healing engine: header deduplication, text bleed repair, and cell deduplication."""

    @classmethod
    def clean_header_repeats(cls, tables: List[RawTable]) -> List[RawTable]:
        """Removes repeated header rows occurring across multi-page breaks."""
        if not tables:
            return []

        first_table = tables[0]
        canonical_headers = [h.lower().strip() for h in first_table.headers if h]

        healed_tables = []
        for tab in tables:
            cleaned_rows = []
            for row in tab.rows:
                # Check if row is a repeated header
                row_str_lower = [str(cell).lower().strip() for cell in row]
                is_header_repeat = False

                if len(canonical_headers) >= 2 and len(row_str_lower) >= 2:
                    match_count = sum(1 for h in canonical_headers if h in row_str_lower)
                    if match_count >= 2:
                        is_header_repeat = True

                if not is_header_repeat:
                    cleaned_rows.append(row)

            healed_tables.append(
                RawTable(
                    page_number=tab.page_number,
                    table_index=tab.table_index,
                    headers=tab.headers,
                    rows=cleaned_rows,
                    extraction_method=tab.extraction_method,
                    confidence=tab.confidence,
                    bounding_box=tab.bounding_box,
                )
            )

        return healed_tables

    @classmethod
    def heal_continuation_rows(cls, tables: List[RawTable]) -> List[RawTable]:
        """
        Detects and merges multi-line text-wrap continuation rows across pages and sub-table breaks
        where primary ID columns (such as saqa_id, ofo_code, code, id) are empty on secondary lines.
        """
        if not tables:
            return []

        healed_tables: List[RawTable] = []
        table_healed_rows: List[List[List[str]]] = [[] for _ in tables]

        global_prev_row: Optional[List[str]] = None

        for t_idx, tab in enumerate(tables):
            if not tab.rows:
                continue

            headers = tab.headers
            # Identify candidate primary ID column index using word boundaries
            id_col_idx = 0
            for idx, h in enumerate(headers):
                h_clean = str(h).lower().strip()
                if re.search(r"\b(?:saqa|ofo|code|id|number|no\.?)\b", h_clean):
                    id_col_idx = idx
                    break

            for row in tab.rows:
                if not row or not any(str(c).strip() for c in row):
                    continue

                id_val = str(row[id_col_idx]).strip() if id_col_idx < len(row) else ""

                # Check if this row is a continuation row (empty ID cell, but has text in other columns)
                is_continuation = False
                if global_prev_row is not None and not id_val:
                    other_content = any(str(c).strip() for i, c in enumerate(row) if i != id_col_idx)
                    if other_content:
                        is_continuation = True

                if is_continuation and global_prev_row is not None:
                    # Stitch into global_prev_row in-place
                    for c_idx in range(max(len(global_prev_row), len(row))):
                        curr_cell = str(row[c_idx]).strip() if c_idx < len(row) else ""
                        if not curr_cell:
                            continue

                        if c_idx >= len(global_prev_row):
                            global_prev_row.append(curr_cell)
                        else:
                            prev_cell = str(global_prev_row[c_idx]).strip()
                            if not prev_cell:
                                global_prev_row[c_idx] = curr_cell
                            elif curr_cell.lower() in prev_cell.lower():
                                # Avoid duplicate text stitching
                                pass
                            else:
                                col_header = str(headers[c_idx]).lower() if c_idx < len(headers) else ""
                                if ";" in prev_cell or ";" in curr_cell or any(k in col_header for k in ["college", "institution", "centre", "campus", "provider"]):
                                    global_prev_row[c_idx] = f"{prev_cell}; {curr_cell}".strip("; ")
                                else:
                                    global_prev_row[c_idx] = f"{prev_cell} {curr_cell}".strip()
                else:
                    new_row = [str(c).strip() if c is not None else "" for c in row]
                    table_healed_rows[t_idx].append(new_row)
                    global_prev_row = new_row

        for t_idx, tab in enumerate(tables):
            healed_tables.append(
                RawTable(
                    page_number=tab.page_number,
                    table_index=tab.table_index,
                    headers=tab.headers,
                    rows=table_healed_rows[t_idx],
                    extraction_method=tab.extraction_method,
                    confidence=tab.confidence,
                    bounding_box=tab.bounding_box,
                )
            )

        return healed_tables

    @classmethod
    def repair_text_wrap_bleed(cls, title: str, colleges_text: str) -> Tuple[str, str]:
        """
        Detects and fixes text wrapping bleed where words from a qualification title
        accidentally bleed into the colleges column (e.g., 'Engineer Motheo TVET' -> 'Software Developer Engineer', 'Motheo TVET').
        """
        if not colleges_text:
            return title, colleges_text

        college_kw_pattern = r"(?i)\b(?:tvet|college|campus|centre|center|institution|school|academy|university)\b"
        kw_match = re.search(college_kw_pattern, colleges_text)
        if kw_match:
            prefix = colleges_text[:kw_match.start()]
            prefix_words = prefix.strip(" ;,\t\n").split()
            if len(prefix_words) >= 2:
                bleed_words = prefix_words[:-1]
                college_start = prefix_words[-1]
                new_title = f"{title} {' '.join(bleed_words)}".strip()
                new_colleges = f"{college_start} {colleges_text[kw_match.start():]}".strip()
                return new_title, new_colleges

        colleges_split = re.split(r"[;\n•·]", colleges_text)
        first_item = colleges_split[0].strip() if colleges_split else ""
        college_keywords = ["tvet", "college", "campus", "centre", "center", "institution", "school", "academy", "university"]
        has_college_kw = any(kw in first_item.lower() for kw in college_keywords)

        if first_item and not has_college_kw and len(first_item.split()) <= 4:
            if not re.search(r"\d", first_item):
                new_title = f"{title} {first_item}".strip()
                remaining_colleges = "; ".join(colleges_split[1:]).strip()
                return new_title, remaining_colleges

        return title, colleges_text

    @classmethod
    def deduplicate_incell_colleges(cls, colleges_text: str) -> Tuple[List[str], List[str]]:
        """
        Splits, cleans, and deduplicates within-cell college listings.
        Returns: (unique_colleges_list, duplicates_flagged)
        """
        if not colleges_text:
            return [], []

        raw_list = [c.strip() for c in re.split(r"[;\n•·]+", colleges_text) if c.strip()]
        unique_colleges = []
        duplicates_flagged = []
        seen = set()

        for c in raw_list:
            c_clean = re.sub(r"\s+", " ", c)
            c_key = c_clean.lower()
            if c_key in seen:
                duplicates_flagged.append(c_clean)
            else:
                seen.add(c_key)
                unique_colleges.append(c_clean)

        return unique_colleges, duplicates_flagged

