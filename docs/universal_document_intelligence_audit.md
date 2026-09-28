# Universal Document Intelligence & Dataset Discovery Architecture Audit

**Document**: `docs/universal_document_intelligence_audit.md`  
**System**: Darkroom DataForge  
**Audit Target**: Universal Document Understanding, Dataset Discovery, Table Classification & Adaptive Curation Engine  
**Forensic Benchmark**: `Mpumalanga’s List of Occupations in High Demand: A Technical Research Report` (72 pages, 1.2 MB PDF)  
**Author**: Senior Research Data Systems Architect  
**Status**: ARCHITECTURAL REDESIGN & IMPLEMENTATION SPECIFICATION  

---

## 1. Executive Summary & Forensic Benchmark Overview

A rigorous empirical audit was conducted on Darkroom DataForge's extraction and curation pipeline using the official research report:  
**"Mpumalanga’s List of Occupations in High Demand: A Technical Research Report"** (DHET / DNA Economics, April 2024; 72 pages; 1,219,805 bytes).

### The Observed Failure
The prior pipeline execution produced an export CSV containing **744 rows** with generic headers:
```csv
column_1,column_2,_curation_decision,_curation_reason,_curation_confidence
,2024 Mpumalanga's List of Occupations in High Demand A Technical Research Report,unprocessed,,1.0
© Published in 20,,unprocessed,,1.0
...
Acknowledgements,,unprocessed,,1.0
...
Table of Contents,,unprocessed,,1.0
...
List of Figures,3,unprocessed,,1.0
...
SOFWARE DEVELOPER,,unprocessed,,1.0
...
1st digit,2nd digit,unprocessed,,1.0
LEVEL OF SKILL REQUIRED FOR A GIVEN NQF,NQF LEVEL,unprocessed,,1.0
High,10 9 8 7,unprocessed,,1.0
1.,"Please select th | Owner, dir...",unprocessed,,1.0
```

### Forensic Breakdown of the 744-Row Corruption
1. **Pages 1–7 (Front Matter)**: Title page boxes, copyright notices, acknowledgements, table of contents, and lists of figures were extracted as "tables" and dumped as data rows.
2. **Page 8 (Acronyms)**: A 10-table abbreviation layout was parsed as data rows.
3. **Pages 13–25 (Methodology & Intermediate Analysis)**: Secondary labour market indicators, sample descriptions, and diagnostic score tables were parsed as data rows.
4. **Pages 31–36 (Table 4: Final OIHD List)**: The actual 167 occupations in high demand were embedded inside the 744 rows, but mangled into two columns (`column_1`, `column_2`) where codes and multiline titles were randomly concatenated.
5. **Pages 42–58 (Annexure 3: Survey Responses)**: Free-text employer survey responses (e.g., `"Reach Truck Driver"`, `"WEDLER"`) were dumped into the same table.
6. **Pages 59–60 (Annexure 4: OFO Skill Levels)**: NQF skill mappings were dumped into the same table.
7. **Page 61 (Annexure 5: Survey Questions)**: Questionnaire survey prompts (`"1. Please select...", "2. Is your enterprise..."`) became data rows.
8. **Curation Falsehood**: Every single row was marked `_curation_decision = unprocessed`, yet stamped with `_curation_confidence = 1.0`.
9. **Export Breach**: The platform allowed this unprocessed, structurally corrupted 744-row payload to be downloaded as a "dataset" without triggering a single quality gate or validation error.

---

## 2. Root Cause Analysis (The 11 Architectural Flaws)

| Forensic Question | Root Cause in Existing Codebase |
|---|---|
| **1. Why did 72 pages become 744 rows?** | `PipelineEngine.run_pipeline` ran `extractor.extract()` across all 72 pages, collected every detected table (`all_raw_tables.append((doc, tab))`), and looped over all tables without filtering out layout, front-matter, survey, or appendix tables. |
| **2. Why were unrelated sections treated as records?** | The system lacked a **Document Structure Discovery** layer. It had no concept of front matter, executive summary, methodology, intermediate findings, final results, or annexures. |
| **3. Why were only `column_1` and `column_2` generated?** | In `engine.py`, `SchemaDetector.detect_columns()` was called exclusively on `all_raw_tables[0]` (the very first table on Page 1, a 2-column decorative title block). It detected `column_1` and `column_2`. Then, all rows from all subsequent 23 tables across 72 pages were forced into those 2 columns via `cls.map_table_row_to_schema()`. |
| **4. Why was the final OIHD table not identified?** | The system had no **Dataset Candidate Discovery** or **Dataset Role Resolver**. It assumed *Document = 1 Single Table*, never checking whether a document contains multiple candidate datasets or which table is the authoritative target. |
| **5. Why was curation marked UNPROCESSED?** | In the upload/extraction flow, `run_curation` was an optional post-process. Because the columns were generic `column_1` and `column_2`, no OFO code or occupation title could be parsed by curation policies. |
| **6. Why was curation confidence = 1.0?** | In `backend/app/models/record.py`, the default for `multi_confidence` was hardcoded to `{"extraction": 1.0, "normalization": 1.0, "validation": 1.0, "curation": 1.0, "overall": 1.0}`. Unprocessed records inherited `curation: 1.0` by default. |
| **7. Why did the export allow unprocessed data?** | `DatasetExporter` had no export-level quality gate verification. It exported whatever records were present, regardless of whether they had failed schema checks or remained un-curated. |
| **8. Why was there no dataset intent?** | The pipeline started with physical PDF extraction rather than defining the dataset intent (what entity is being extracted, what is the objective, what is the authoritative source table). |
| **9. Why was there no source table identity?** | Tables were treated as anonymous row arrays. Provenance only tracked `table_index` and `page_number`, with no table title, section hierarchy, or semantic role. |
| **10. Why was there no section context?** | The pipeline extracted raw table grids with `pdfplumber` without inspecting the preceding headings, section numbering (`PART 5`), or text narratives on the page. |
| **11. Why was final dataset not separated from intermediate evidence?** | The system assumed that every table in a research paper is part of the final dataset, failing to distinguish evidence tables (e.g. Table 2: variables, Table 3: top 10) from the authoritative dataset (Table 4: final list). |

---

## 3. The New Fundamental Architectural Principle

```
                       NEVER ASSUME:
              PDF = Dataset
              Every Table = Target Dataset
              First Detected Table = Authoritative Dataset
              All Rows in a PDF Belong to One Dataset
              Keyword Matching = Semantic Curation
              Successful PDF Extraction = Successful Dataset Extraction
```

### The Universal Research Pipeline
```
SOURCE DOCUMENT
      ↓
INGEST & FINGERPRINT (SHA-256)
      ↓
DOCUMENT PROFILING (Type, Metadata, Language, Estimated Datasets)
      ↓
DOCUMENT STRUCTURE DISCOVERY (Headings, Sections, Annexures, Hierarchy)
      ↓
SECTION / TABLE / FIGURE IDENTIFICATION (Layout vs Content vs Data)
      ↓
DATASET CANDIDATE DISCOVERY (Extract All Datasets Present)
      ↓
DATASET INTENT & ROLE RESOLUTION (Identify Authoritative Target Dataset)
      ↓
STRUCTURAL EXTRACTION (Target Tables Only)
      ↓
TABLE RECONSTRUCTION (Multi-page Stitching, Wrapped Cells, Artifact Stripping)
      ↓
SEMANTIC SCHEMA INTERPRETATION (Dynamic Field Types, Source Authority)
      ↓
NORMALIZATION (Dual-Value Raw vs Normalized, Never Silent Mutation)
      ↓
VALIDATION (Conditional Structural Validators)
      ↓
EVIDENCE-BACKED CURATION (Zero Blind Trust, Three States: INCLUDE/EXCLUDE/REVIEW)
      ↓
HUMAN REVIEW (Prioritized Triage Queue with Immutability)
      ↓
PROVENANCE + LINEAGE (Source Document SHA-256 to Row BBox)
      ↓
QUALITY GATES (10 Mandatory Gates; Block Production if Unprocessed)
      ↓
EXPORT (RAW_EXTRACTION, NORMALIZED, CURATED, REVIEW, AUDIT_PACKAGE)
```

---

## 4. Component Redesign & Implementation Blueprint

### A. Document Intelligence Package (`backend/app/document_intelligence/`)
1. **`document_profile.py` & `profiler.py`**:
   - Computes SHA-256 fingerprint, page count, text/image/table density, scanned detection, language.
   - Classifies `document_type`: `RESEARCH_REPORT`, `STATISTICAL_REPORT`, `POLICY_DOCUMENT`, `CODEBOOK`, `OCCUPATIONAL_DATASET`, `QUALIFICATION_DATASET`, `SURVEY_REPORT`, `TECHNICAL_REPORT`, `GENERAL_DATASET`, `MIXED_DOCUMENT`, `UNKNOWN`.
   - Extracts metadata: Title, authors, publisher, publication date, table of contents.
2. **`structure_detector.py` & `section_detector.py`**:
   - Builds hierarchical document tree: Front Matter, Executive Summary, Numbered Sections (`PART 1`, `4.1`), Subsections, Annexures, References.
   - Identifies semantic equivalents (`METHODOLOGY`, `RESULTS`, `FINDINGS`, `FINAL_LIST`, `SURVEY`, `APPENDIX`) while preserving verbatim source headings.
3. **`table_detector.py` & `table_classifier.py`**:
   - Detects all tables with page ranges and coordinates.
   - Filters out decorative/layout tables, acronym tables, TOC entries.
   - Assigns `semantic_role`: `METADATA`, `METHODOLOGY`, `SURVEY`, `INTERMEDIATE_ANALYSIS`, `EVIDENCE`, `FINAL_DATASET`, `REFERENCE`, `APPENDIX`, `UNKNOWN`.
4. **`dataset_discovery.py` & `dataset_role_resolver.py`**:
   - Discovers distinct candidate datasets.
   - Identifies candidate schema, row counts, and structural confidence.
   - Combines multi-factor signals (captions, section context, "final list", text references, summary counts like "167 occupations") to resolve the **Authoritative Target Dataset**.
   - Generates human-readable and machine-readable `DatasetDiscoveryReport`.
5. **`unit_of_observation.py`**:
   - Discovers whether records represent `occupation`, `qualification`, `person`, `institution`, `province`, `variable`, `survey_response`.
6. **`table_reconstructor.py`**:
   - Reconstructs multi-page tables (e.g. Table 4 across PDF pages 31–36).
   - Deduplicates repeated running headers, removes running page headers/footers in table margins.
   - Heals wrapped multi-line cells without destroying column alignment.
7. **`schema_detector.py`**:
   - Dynamic domain field semantics (OFO code, occupation title, minimum qualification, SAQA ID, NQF level, wage, employment).
   - Classifies field authority: `SOURCE_FACT`, `DERIVED_VALUE`, `INFERENCE`.

### B. Validation & Quality Gate Hardening
1. **Schema-Aware Validators (`backend/app/pipeline/validator.py`)**:
   - `OFOCodeValidator` (6-digit format `\d{4,6}` or `\d{4}-\d{6}`, checks against OFO taxonomy).
   - `DateValidator`, `NumericRangeValidator`, `EnumValidator`, `RequiredFieldValidator`, `IdentifierValidator`.
   - Activates conditionally when field semantics match.
2. **Confidence Repair (`backend/app/models/record.py`)**:
   - Change default `curation_decision = "unprocessed"`.
   - Change default `multi_confidence["curation"] = None`.
   - Strictly forbid `curation_confidence = 1.0` on un-curated data.
3. **Quality Gates & Export States (`backend/app/curation/quality_engine.py`, `pipeline/exporter.py`)**:
   - Enforce 10 Quality Gates before export.
   - Distinguish export states: `RAW_EXTRACTION`, `NORMALIZED_DATASET`, `CURATED_DATASET`, `REVIEW_DATASET`, `AUDIT_PACKAGE`.
   - Block `CURATED_DATASET` export if records remain unprocessed.

---

## 5. Mpumalanga Benchmark Acceptance Criteria

| Benchmark Metric | Prior Naive Extraction | Required Universal Target |
|---|---|---|
| **Document Classification** | Untyped / Generic | `RESEARCH_REPORT` / `OCCUPATIONAL_DATASET` |
| **Sections Discovered** | 0 (Flat table stream) | $\ge 8$ formal parts (`PART 1` to `PART 8`, Annexures 1–5) |
| **Tables Detected** | All 24 tables lumped together | Classified by role: Metadata, Methodology, Survey, Final List, Annexures |
| **Target Dataset Identified** | None (All tables combined) | **Table 4: The final list of OIHD in Mpumalanga** |
| **Target Section** | None | `PART 5: CONSOLIDATION OF EVIDENCE AND THE FINAL LIST` |
| **Unit of Observation** | Mixed (Text, Acronyms, Survey) | `occupation` |
| **Record Count** | 744 (Corrupted garbage) | **167** (Corroborated by narrative text: *"Total occupations 167"*) |
| **Columns Extracted** | `column_1`, `column_2` | `ofo_code`, `occupation_title`, `minimum_qualification_required` |
| **Curation Confidence** | 1.0 (Fabricated) | Explicitly calculated from evidence ($0.90 - 0.98$ for valid trades) |
| **Curation Decision** | `unprocessed` | Evaluated against `merseta_ofo_relevance` (`INCLUDE`, `EXCLUDE`, `REVIEW`) |
| **Quality Gate Status** | Passed blindly | Evaluated across 10 gates before export |

---

## 6. Remaining Risks & Nuances

1. **Complex Vector-less Layout PDFs**: Documents with zero border lines relying strictly on whitespace and font-size hierarchies require heuristic character bounding-box clustering.
2. **Multilingual Publications**: South African policy documents with Afrikaans or isiZulu translations of qualification titles require multi-lingual alias dictionaries.
3. **Footnote Splitting**: Footnotes inside table cells (e.g. `*` denoting outlier occupations with high unemployment) must be captured as qualifier metadata rather than contaminating the occupation title string.
