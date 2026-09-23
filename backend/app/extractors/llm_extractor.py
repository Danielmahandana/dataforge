from __future__ import annotations
import logging
from typing import List, Optional
import fitz  # PyMuPDF

from backend.app.extractors.base import BaseExtractor, ExtractionResult, RawTable
from backend.app.services.llm import get_llm_provider, BaseLLMProvider

logger = logging.getLogger("dataforge.extractors.llm")


class LLMExtractor(BaseExtractor):
    """Layout-aware AI extractor using LLMs for complex, borderless, or unstructured tables."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            name="llm_ai_table",
            description="AI-driven structural table and record extraction using Large Language Models"
        )
        self.provider = provider or get_llm_provider()

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []

        try:
            doc = fitz.open(file_path)
            page_indices = range(len(doc)) if pages is None else [p - 1 for p in pages if 0 < p <= len(doc)]

            system_instruction = (
                "You are Darkroom DataForge AI, an expert research data engineering assistant.\n"
                "Extract tabular data from raw PDF page text into clean JSON format.\n"
                "Return a JSON object containing key 'tables', which is a list of table objects.\n"
                "Each table object MUST have:\n"
                "- 'headers': list of string column names\n"
                "- 'rows': list of lists of string cell values\n"
                "Standardize multi-line headers and unaligned row cells."
            )

            for p_idx in page_indices:
                page_num = p_idx + 1
                page = doc[p_idx]
                page_text = page.get_text("text")

                if not page_text or len(page_text.strip()) < 20:
                    warnings.append(f"Page {page_num} contains insufficient text for LLM extraction.")
                    continue

                prompt = (
                    f"--- PDF PAGE {page_num} TEXT LAYOUT ---\n"
                    f"{page_text[:4000]}\n"
                    f"----------------------------------------\n"
                    f"Extract all tables present on page {page_num} as clean headers and row arrays."
                )

                res = self.provider.generate_structured(prompt=prompt, system_instruction=system_instruction)

                extracted_tables = res.get("tables", [])
                if not extracted_tables and "headers" in res and "rows" in res:
                    extracted_tables = [res]

                for t_idx, tab_dict in enumerate(extracted_tables):
                    headers = tab_dict.get("headers", [])
                    rows = tab_dict.get("rows", [])
                    if headers or rows:
                        tables.append(
                            RawTable(
                                page_number=page_num,
                                table_index=t_idx,
                                headers=[str(h) for h in headers],
                                rows=[[str(cell) for cell in row] for row in rows],
                                extraction_method="llm_ai_table",
                                confidence=0.92,
                            )
                        )

            doc.close()

        except Exception as e:
            logger.exception("LLM Extractor execution failed")
            errors.append(f"LLM Extraction exception: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.92 if tables else 0.10,
            warnings=warnings,
            errors=errors,
        )
