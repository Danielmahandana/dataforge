# Darkroom DataForge: Extraction Guide

## 1. Creating Custom Extraction Profiles

Extraction profiles configure how Darkroom DataForge identifies, extracts, and validates specific document archetypes. Profiles are located in `config/profiles/*.yaml`.

### Profile Structure Example

```yaml
name: "my_custom_report"
display_name: "Custom Sector Skills Plan"
description: "Extraction profile for Sector Skills Plan Annexure B tables"
document_type: "SEMI_STRUCTURED_REPORT"
recommended_extractor: "pdf_tables"

matching_patterns:
  filename_regex: "(?i)(ssp|skills_plan|annexure_b)"
  keywords:
    - "Priority Skills"
    - "OFO Code"
    - "Scarce Skills"

columns:
  - name: "ofo_code"
    display_name: "OFO Code"
    type: "string"
    required: true
    pattern: "^[0-9]{4,6}$"
    aliases: ["OFO Code", "OFO", "Code"]
  - name: "occupation_title"
    display_name: "Occupation Title"
    type: "string"
    required: true
  - name: "scarcity_reasons"
    display_name: "Scarcity Drivers"
    type: "list"
    split_delimiter: ";"

datasets:
  - id: "priority_skills"
    name: "Priority Skills Demand"
    primary_key: ["ofo_code"]
```

---

## 2. Implementing a New BaseExtractor

To add a new extraction algorithm (e.g. for custom financial statements or specialized legal gazettes):

1. Subclass `BaseExtractor` in `extractors/`:

```python
from typing import List, Optional
from extractors.base import BaseExtractor, ExtractionResult, RawTable

class CustomGazetteExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(
            name="gazette_extractor",
            description="Specialized parser for Government Gazette notices"
        )

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        # Custom PDF parsing logic using pymupdf or pdfplumber...
        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.95
        )
```

2. Register the extractor in `core/extractor_engine.py`:

```python
self.extractors["gazette_extractor"] = CustomGazetteExtractor()
```

---

## 3. Best Practices for Complex PDF Challenges

| Challenge | Recommended Engine Solution |
| :--- | :--- |
| **Split tables across pages** | Handled automatically by `TableReconstructor.reconstruct()`. Compares header cosine similarity and strips duplicate headers across page breaks. |
| **Multi-line wrapped cells** | `TableReconstructor.heal_rows()` detects when primary key column is empty and merges subsequent column text into the preceding row. |
| **Delimited composite lists** | `RelationshipDetector.decompose_one_to_many()` detects multi-value cells and automatically generates relational junction tables. |
| **Scanned documents** | `OcrExtractor` renders pages to 2x resolution pixmaps and applies `pytesseract` line clustering. |
