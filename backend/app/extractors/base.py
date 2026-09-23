from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class RawTable(BaseModel):
    page_number: int
    table_index: int = 0
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    extraction_method: str = "unknown"
    confidence: float = 1.0
    bounding_box: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        if self.headers:
            return len(self.headers)
        if self.rows:
            return len(self.rows[0])
        return 0

class ExtractionResult(BaseModel):
    tables: List[RawTable] = Field(default_factory=list)
    raw_text: Optional[str] = None
    extraction_method: str
    quality_score: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return sum(t.row_count for t in self.tables)

class BaseExtractor(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        """Extract structured tables/records from the document."""
        pass
