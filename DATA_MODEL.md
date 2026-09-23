# Darkroom DataForge: Data Model Specification

## 1. Core Models

### `DocumentMetadata`
Represents an ingested PDF document and its forensic characteristics.
- `id`: Unique UUID.
- `filename`: Base filename on disk.
- `file_path`: Canonical path inside the project `documents/` directory.
- `file_size_bytes`: Size in bytes.
- `sha256_hash`: Cryptographic checksum for reproducibility and provenance.
- `status`: Lifecycle status (`PENDING`, `INSPECTED`, `CLASSIFIED`, `EXTRACTED`, `FAILED`).
- `inspection`: `InspectionResult` (page counts, text availability, image ratio, table likelihood).
- `classification`: `ClassificationResult` (assigned `DocumentType`, confidence score, recommended extractor).

### `Record` & `CellValue`
Provides granular tracking of raw source text versus normalized output.
```json
{
  "id": "e678b87c-...",
  "cells": {
    "saqa_id": {
      "raw_value": "118792",
      "normalized_value": "118792",
      "is_modified": false,
      "confidence": 0.98,
      "field_name": "saqa_id"
    },
    "qualification": {
      "raw_value": "Occupational Certificate:  Artificial Intelligence Software Developer  ",
      "normalized_value": "Occupational Certificate: Artificial Intelligence Software Developer",
      "is_modified": true,
      "confidence": 0.98,
      "field_name": "qualification"
    }
  },
  "provenance": {
    "source_document": "DHET_TVET_Qualifications_2026.pdf",
    "source_page": 1,
    "extraction_method": "qualifications",
    "confidence": 0.98,
    "status": "NORMALIZED"
  }
}
```

### `Dataset`
Represents a relational tabular dataset produced by the pipeline.
- `metadata`: `DatasetMetadata` (name, display name, description, quality metrics).
- `columns`: List of `FieldDefinition` models (name in `snake_case`, display_name, data_type, required, nullable, is_primary_key, is_foreign_key).
- `records`: List of `Record` instances.
- `primary_key`: Ordered list of key column names.

---

## 2. PostgreSQL / Supabase Mapping

| Darkroom DataForge Type | PostgreSQL / Supabase Column Type | Constraints Generated |
| :--- | :--- | :--- |
| `DataType.STRING` | `TEXT` | `NOT NULL` (if required) |
| `DataType.INTEGER` | `INTEGER` | `NOT NULL` (if required) |
| `DataType.FLOAT` | `NUMERIC(12, 4)` | `NOT NULL` (if required) |
| `DataType.BOOLEAN` | `BOOLEAN` | `NOT NULL` (if required) |
| `DataType.DATE` | `DATE` | `NOT NULL` (if required) |
| `DataType.LIST` | `TEXT[]` | Multi-value array |
| `DataType.JSON` | `JSONB` | Flexible payload |
| `Relationship` | `FOREIGN KEY` | `ON DELETE CASCADE` |
