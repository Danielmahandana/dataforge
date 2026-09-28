from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    RESEARCH_REPORT = "RESEARCH_REPORT"
    STATISTICAL_REPORT = "STATISTICAL_REPORT"
    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    CODEBOOK = "CODEBOOK"
    OCCUPATIONAL_DATASET = "OCCUPATIONAL_DATASET"
    QUALIFICATION_DATASET = "QUALIFICATION_DATASET"
    SURVEY_REPORT = "SURVEY_REPORT"
    TECHNICAL_REPORT = "TECHNICAL_REPORT"
    GENERAL_DATASET = "GENERAL_DATASET"
    MIXED_DOCUMENT = "MIXED_DOCUMENT"
    UNKNOWN = "UNKNOWN"


class SemanticTableRole(str, Enum):
    METADATA = "METADATA"
    METHODOLOGY = "METHODOLOGY"
    SURVEY = "SURVEY"
    INTERMEDIATE_ANALYSIS = "INTERMEDIATE_ANALYSIS"
    EVIDENCE = "EVIDENCE"
    FINAL_DATASET = "FINAL_DATASET"
    REFERENCE = "REFERENCE"
    APPENDIX = "APPENDIX"
    UNKNOWN = "UNKNOWN"


class UnitOfObservation(str, Enum):
    OCCUPATION = "occupation"
    QUALIFICATION = "qualification"
    PERSON = "person"
    HOUSEHOLD = "household"
    INSTITUTION = "institution"
    COURSE = "course"
    INDUSTRY = "industry"
    PROVINCE = "province"
    VARIABLE = "variable"
    COMPANY = "company"
    SURVEY_RESPONSE = "survey_response"
    UNKNOWN = "unknown"


class FieldAuthority(str, Enum):
    SOURCE_FACT = "SOURCE_FACT"
    DERIVED_VALUE = "DERIVED_VALUE"
    INFERENCE = "INFERENCE"


class SectionNode(BaseModel):
    section_id: str = ""
    title: str
    raw_heading: str = ""
    level: int = 1  # 1: Part/Chapter/Major, 2: Section, 3: Subsection, 4: Appendix
    page_start: int
    page_end: int
    semantic_type: str = "UNKNOWN"  # FRONT_MATTER, INTRODUCTION, METHODOLOGY, EVIDENCE, RESULTS, FINAL_LIST, CONCLUSION, APPENDIX, REFERENCES
    parent_id: Optional[str] = None
    subsections: List[str] = Field(default_factory=list)


class TableMetadata(BaseModel):
    table_id: str
    page_start: int
    page_end: int
    caption: str = ""
    raw_caption: str = ""
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    column_count: int = 0
    row_count: int = 0
    headers: List[str] = Field(default_factory=list)
    header_candidates: List[List[str]] = Field(default_factory=list)
    continuation_detected: bool = False
    table_type: str = "STANDARD"  # STANDARD, MULTI_PAGE, LAYOUT_ARTIFACT, DECORATIVE, ROTATED
    structural_confidence: float = 0.8
    semantic_role: SemanticTableRole = SemanticTableRole.UNKNOWN
    unit_of_observation: UnitOfObservation = UnitOfObservation.UNKNOWN
    evidence_signals: List[str] = Field(default_factory=list)
    sample_rows: List[List[str]] = Field(default_factory=list)

    @property
    def page_number(self) -> int:
        return self.page_start


class DatasetCandidate(BaseModel):
    candidate_id: str
    name: str
    source_section: str
    source_tables: List[str] = Field(default_factory=list)
    page_range: List[int] = Field(default_factory=list)
    candidate_schema: List[Dict[str, Any]] = Field(default_factory=list)
    record_count: int = 0
    structural_confidence: float = 0.8
    semantic_confidence: float = 0.8
    role: SemanticTableRole = SemanticTableRole.UNKNOWN
    unit_of_observation: UnitOfObservation = UnitOfObservation.UNKNOWN
    evidence_reasons: List[str] = Field(default_factory=list)
    is_authoritative: bool = False
    score: float = 0.0

    @property
    def page_start(self) -> int:
        return min(self.page_range) if self.page_range else 1

    @property
    def page_end(self) -> int:
        return max(self.page_range) if self.page_range else 1

    @property
    def table_ids(self) -> List[str]:
        return self.source_tables

    @property
    def stated_count(self) -> Optional[int]:
        import re
        for r in self.evidence_reasons:
            m = re.search(r"stated\s+(?:count|target|size)?\s*(?:of)?\s*:?\s*(\d+)", r, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return self.record_count


class DatasetDiscoveryReport(BaseModel):
    document_title: str
    document_type: DocumentType
    page_count: int
    sections_detected: int
    tables_detected: int
    candidate_count: int
    candidates: List[DatasetCandidate] = Field(default_factory=list)
    selected_candidate_id: Optional[str] = None
    selection_rationale: str = ""
    stated_record_counts_in_text: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentProfile(BaseModel):
    document_id: str
    file_hash: str
    file_type: str  # PDF, DOCX, XLSX, CSV, HTML, SCANNED_PDF
    file_size_bytes: int = 0
    page_count: int = 1
    has_text: bool = True
    has_images: bool = False
    has_tables: bool = True
    has_scanned_pages: bool = False
    ocr_required: bool = False
    language: str = "en"
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    document_type: DocumentType = DocumentType.UNKNOWN
    document_type_confidence: float = 0.5
    estimated_structure: str = ""
    estimated_dataset_count: int = 1
    sections: List[SectionNode] = Field(default_factory=list)
    tables: List[TableMetadata] = Field(default_factory=list)
    dataset_candidates: List[DatasetCandidate] = Field(default_factory=list)
    authoritative_dataset_id: Optional[str] = None
    discovery_report: Optional[DatasetDiscoveryReport] = None
