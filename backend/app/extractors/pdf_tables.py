from __future__ import annotations
import re
from typing import List, Optional
import pdfplumber
from backend.app.extractors.base import BaseExtractor, ExtractionResult, RawTable

class PdfTablesExtractor(BaseExtractor):
    """Extracts tables from PDFs using pdfplumber's lattice and stream algorithms."""

    def __init__(self):
        super().__init__(
            name="pdf_tables",
            description="Native PDF table parser using lattice/stream line detection"
        )

    @staticmethod
    def is_header_row(row: List[str]) -> bool:
        if not row or not any(row):
            return False
        row_text = " ".join(str(c).lower().strip() for c in row if c)
        header_keywords = ["saqa", "number", "qualification", "framework", "allowance", "college", "code", "programme", "name", "title", "id"]
        matches = sum(1 for kw in header_keywords if re.search(r"\b" + re.escape(kw) + r"\b", row_text))
        first_cell = str(row[0]).strip() if row else ""
        # If first cell is numeric digits (e.g. SAQA ID 93627), it is a data row
        if re.match(r"^\d{4,7}$", first_cell):
            return False
        # If first two cells are empty, it is a continuation data row
        if not first_cell and len(row) > 1 and not str(row[1]).strip():
            return False
        return matches >= 2

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []
        active_headers: List[str] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                page_indices = range(len(pdf.pages)) if pages is None else [p - 1 for p in pages if 0 < p <= len(pdf.pages)]

                for p_idx in page_indices:
                    page = pdf.pages[p_idx]
                    page_num = p_idx + 1

                    extracted_tables = page.extract_tables()
                    if not extracted_tables:
                        extracted_tables = page.extract_tables({
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "snap_tolerance": 4,
                            "join_tolerance": 4,
                        })

                    if not extracted_tables:
                        continue

                    for t_idx, raw_table in enumerate(extracted_tables):
                        cleaned_rows: List[List[str]] = []
                        for row in raw_table:
                            if not row:
                                continue
                            cleaned_cells = [re.sub(r"[\r\n\t]+", " ", str(c)).strip() if c is not None else "" for c in row]
                            if any(cleaned_cells):
                                cleaned_rows.append(cleaned_cells)

                        if not cleaned_rows:
                            continue

                        headers: List[str] = []
                        data_rows: List[List[str]] = []

                        if self.is_header_row(cleaned_rows[0]):
                            headers = cleaned_rows[0]
                            data_rows = cleaned_rows[1:]
                            active_headers = headers
                        else:
                            headers = active_headers if active_headers else [f"Column_{i+1}" for i in range(len(cleaned_rows[0]))]
                            data_rows = cleaned_rows

                        tables.append(
                            RawTable(
                                page_number=page_num,
                                table_index=t_idx,
                                headers=headers,
                                rows=data_rows,
                                extraction_method=self.name,
                                confidence=0.88,
                            )
                        )

        except Exception as e:
            errors.append(f"pdfplumber extraction failed: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.88 if tables else 0.20,
            warnings=warnings,
            errors=errors,
        )
