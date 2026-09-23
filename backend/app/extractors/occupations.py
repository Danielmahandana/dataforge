from __future__ import annotations
import re
from typing import List, Optional
import pdfplumber
from backend.app.extractors.base import BaseExtractor, ExtractionResult, RawTable

class OccupationsExtractor(BaseExtractor):
    """Specialized extractor for DHET Occupations in High Demand (OIHD) reports and annexures."""

    FIELD_ALIASES = {
        "ofo_code": ["ofo", "code", "ofo code", "occupation code", "unit group", "unit"],
        "occupation_title": ["occupation", "title", "occupation title", "description", "job title", "name"],
        "demand_rank": ["rank", "ranking", "demand", "priority", "demand rank", "priority level"],
        "major_group": ["major group", "group", "sub-major", "ofo group", "occupational group"],
        "province": ["province", "region", "provincial", "location", "prov"],
        "educational_qualification_req": ["qualification", "entry requirement", "education", "minimum qualification", "requirement"],
    }

    def __init__(self):
        super().__init__(
            name="occupations",
            description="Specialized parser for Occupations in High Demand (OIHD) lists & OFO tables"
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

        headers = ["ofo_code", "occupation_title", "demand_rank", "major_group", "province", "educational_qualification_req"]

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
                            if any(w in first_col for w in ["ofo", "code", "occupation"]):
                                continue

                            if col_mapping and "ofo_code" in col_mapping and "occupation_title" in col_mapping:
                                def get_cell(f_name: str, def_val: str = "") -> str:
                                    idx = col_mapping.get(f_name)
                                    return cleaned[idx] if idx is not None and idx < len(cleaned) else def_val

                                ofo = get_cell("ofo_code")
                                title = get_cell("occupation_title")
                                rank = get_cell("demand_rank", "1")
                                group = get_cell("major_group")
                                province = get_cell("province", "National")
                                qual = get_cell("educational_qualification_req")
                            elif len(cleaned) >= 3:
                                ofo = cleaned[0]
                                title = cleaned[1]
                                rank = cleaned[2]
                                group = cleaned[3] if len(cleaned) > 3 else ""
                                province = cleaned[4] if len(cleaned) > 4 else "National"
                                qual = cleaned[5] if len(cleaned) > 5 else ""
                            else:
                                ofo, title, rank, group, province, qual = "", "", "", "", "National", ""

                            if re.match(r"^\d{4,6}$", ofo):
                                data_rows.append([ofo, title, rank, group, province, qual])
                            elif data_rows and not ofo and title:
                                data_rows[-1][1] = f"{data_rows[-1][1]} {title}".strip()

                        if data_rows:
                            tables.append(
                                RawTable(
                                    page_number=page_num,
                                    table_index=t_idx,
                                    headers=headers,
                                    rows=data_rows,
                                    extraction_method=self.name,
                                    confidence=0.94,
                                )
                            )

        except Exception as e:
            errors.append(f"OIHD extraction error: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.94 if tables else 0.20,
            warnings=warnings,
            errors=errors,
        )
