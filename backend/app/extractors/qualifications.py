from __future__ import annotations
import re
from typing import List, Optional
import pdfplumber
from backend.app.extractors.base import BaseExtractor, ExtractionResult, RawTable

class QualificationsExtractor(BaseExtractor):
    """Specialized extractor for TVET college occupational qualifications lists."""

    FIELD_ALIASES = {
        "saqa_id": ["saqa", "qual id", "qualification id", "code", "qual code", "id"],
        "qualification": ["qualification", "learning programme", "programme", "title", "description", "qual title", "occupational qualification"],
        "nqf_level": ["nqf", "level", "nqf level"],
        "framework": ["sub-framework", "framework", "subframework", "qualification type", "type"],
        "nsfas_eligible": ["nsfas", "funded", "bursary", "eligible", "nsfas eligible"],
        "participating_colleges": ["college", "colleges", "delivery centre", "offering", "institution", "campus", "tvet", "provider"],
    }

    def __init__(self):
        super().__init__(
            name="qualifications",
            description="Specialized parser for DHET/TVET Occupational Qualifications & College Offerings"
        )

    def _match_header_indices(self, header_cells: List[str]) -> dict:
        mapping = {}
        used_indices = set()
        for field, aliases in self.FIELD_ALIASES.items():
            for idx, cell in enumerate(header_cells):
                if idx in used_indices:
                    continue
                c_clean = cell.lower().strip()
                if any(alias in c_clean for alias in aliases):
                    mapping[field] = idx
                    used_indices.add(idx)
                    break
        return mapping

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []

        headers = ["saqa_id", "qualification", "nqf_level", "framework", "nsfas_eligible", "participating_colleges"]

        try:
            with pdfplumber.open(file_path) as pdf:
                page_indices = range(len(pdf.pages)) if pages is None else [p - 1 for p in pages if 0 < p <= len(pdf.pages)]

                for p_idx in page_indices:
                    page = pdf.pages[p_idx]
                    page_num = p_idx + 1

                    extracted = page.extract_tables()
                    if not extracted:
                        extracted = page.extract_tables({
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "snap_tolerance": 4,
                            "join_tolerance": 4,
                        })

                    if not extracted:
                        continue

                    for t_idx, raw_tab in enumerate(extracted):
                        if not raw_tab or len(raw_tab) < 1:
                            continue

                        col_mapping = {}
                        start_row_idx = 0

                        for r_i in range(min(3, len(raw_tab))):
                            candidate_header = [str(c).strip() if c else "" for c in raw_tab[r_i]]
                            mapped = self._match_header_indices(candidate_header)
                            if len(mapped) >= 2:
                                col_mapping = mapped
                                start_row_idx = r_i + 1
                                break

                        data_rows: List[List[str]] = []

                        for row_idx in range(start_row_idx, len(raw_tab)):
                            row = raw_tab[row_idx]
                            if not row:
                                continue
                            cleaned = [str(c).strip() if c is not None else "" for c in row]
                            if not any(cleaned):
                                continue

                            first_col = cleaned[0].lower() if cleaned else ""
                            if any(w in first_col for w in ["saqa", "qual id", "national qual"]):
                                continue

                            if col_mapping and "saqa_id" in col_mapping and "qualification" in col_mapping:
                                def get_cell(f_name: str, def_val: str = "") -> str:
                                    idx = col_mapping.get(f_name)
                                    return cleaned[idx] if idx is not None and idx < len(cleaned) else def_val

                                saqa_id = get_cell("saqa_id")
                                title = get_cell("qualification")
                                nqf = get_cell("nqf_level")
                                framework = get_cell("framework")
                                nsfas = get_cell("nsfas_eligible", "No")
                                colleges = get_cell("participating_colleges")
                            elif len(cleaned) >= 4:
                                saqa_id = cleaned[0]
                                title = cleaned[1]
                                nqf = cleaned[2]
                                framework = cleaned[3]
                                nsfas = cleaned[4] if len(cleaned) > 4 else "No"
                                colleges = cleaned[5] if len(cleaned) > 5 else ""
                            else:
                                saqa_id, title, nqf, framework, nsfas, colleges = "", "", "", "", "No", ""

                            colleges = re.sub(r"[\r\n•·]+", "; ", colleges).strip()
                            colleges = re.sub(r"\s*;\s*", "; ", colleges)

                            if re.search(r"\d{4,7}", saqa_id):
                                data_rows.append([
                                    saqa_id,
                                    title,
                                    nqf,
                                    framework,
                                    nsfas,
                                    colleges
                                ])
                            elif data_rows and (not saqa_id or not re.search(r"\d{3,}", saqa_id)):
                                last_row = data_rows[-1]
                                if title:
                                    last_row[1] = f"{last_row[1]} {title}".strip()
                                if colleges:
                                    last_row[5] = f"{last_row[5]}; {colleges}".strip("; ")

                        if data_rows:
                            tables.append(
                                RawTable(
                                    page_number=page_num,
                                    table_index=t_idx,
                                    headers=headers,
                                    rows=data_rows,
                                    extraction_method=self.name,
                                    confidence=0.96,
                                )
                            )

        except Exception as e:
            errors.append(f"TVET qualifications extraction error: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.96 if tables else 0.20,
            warnings=warnings,
            errors=errors,
        )
