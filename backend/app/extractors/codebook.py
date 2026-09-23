from __future__ import annotations
import re
from typing import List, Optional
import pymupdf
import pdfplumber
from backend.app.extractors.base import BaseExtractor, ExtractionResult, RawTable

class CodebookExtractor(BaseExtractor):
    """Specialized extractor for survey codebooks and metadata dictionaries (e.g. Stats SA QLFS)."""

    def __init__(self):
        super().__init__(
            name="codebook",
            description="Specialized parser for QLFS codebooks, variables, and value categories"
        )

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []

        headers = ["variable_name", "variable_label", "value", "value_label", "data_type", "description"]

        try:
            with pdfplumber.open(file_path) as pdf:
                page_indices = range(len(pdf.pages)) if pages is None else [p - 1 for p in pages if 0 < p <= len(pdf.pages)]

                for p_idx in page_indices:
                    page = pdf.pages[p_idx]
                    page_num = p_idx + 1

                    extracted = page.extract_tables()
                    if extracted:
                        for t_idx, raw_tab in enumerate(extracted):
                            if not raw_tab or len(raw_tab) < 2:
                                continue
                            
                            data_rows: List[List[str]] = []
                            curr_var = ""
                            curr_label = ""

                            for row in raw_tab[1:]:
                                cleaned = [str(c).strip() if c is not None else "" for c in row]
                                if not any(cleaned):
                                    continue
                                
                                if len(cleaned) >= 4:
                                    var_col = cleaned[0]
                                    label_col = cleaned[1]
                                    val_col = cleaned[2]
                                    val_label_col = cleaned[3]
                                    dtype_col = cleaned[4] if len(cleaned) > 4 else "categorical"
                                    desc_col = cleaned[5] if len(cleaned) > 5 else ""

                                    if var_col:
                                        curr_var = var_col
                                    if label_col:
                                        curr_label = label_col

                                    data_rows.append([
                                        curr_var,
                                        curr_label,
                                        val_col,
                                        val_label_col,
                                        dtype_col,
                                        desc_col
                                    ])
                                elif len(cleaned) >= 2 and curr_var:
                                    data_rows.append([
                                        curr_var,
                                        curr_label,
                                        cleaned[0],
                                        cleaned[1],
                                        "categorical",
                                        ""
                                    ])

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

            if not tables:
                doc = pymupdf.open(file_path)
                page_indices = range(len(doc)) if pages is None else [p - 1 for p in pages if 0 < p <= len(doc)]

                for p_idx in page_indices:
                    page = doc[p_idx]
                    page_num = p_idx + 1
                    text = page.get_text("text")

                    lines = text.split("\n")
                    data_rows = []
                    curr_var = ""
                    curr_label = ""

                    for line in lines:
                        parts = [p.strip() for p in re.split(r"\||\t", line) if p.strip()]
                        if len(parts) >= 4:
                            curr_var = parts[0]
                            curr_label = parts[1]
                            data_rows.append([curr_var, curr_label, parts[2], parts[3], "categorical", ""])
                        elif len(parts) >= 2 and curr_var and re.match(r"^[0-9]+$", parts[0]):
                            data_rows.append([curr_var, curr_label, parts[0], parts[1], "categorical", ""])

                    if data_rows:
                        tables.append(
                            RawTable(
                                page_number=page_num,
                                table_index=0,
                                headers=headers,
                                rows=data_rows,
                                extraction_method=self.name,
                                confidence=0.86,
                            )
                        )
                doc.close()

        except Exception as e:
            errors.append(f"Codebook extraction error: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.94 if tables else 0.20,
            warnings=warnings,
            errors=errors,
        )
