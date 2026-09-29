from typing import Optional, List
from pydantic import BaseModel, Field

class ExportRequest(BaseModel):
    format: str = "csv"  # csv, json, xlsx, parquet
    include_provenance: bool = True
    include_curation: bool = True
    include_domain_knowledge: bool = False
    only_valid_records: bool = False
    curation_filter: Optional[str] = None  # e.g. "INCLUDE", "REVIEW", None
    selected_columns: Optional[List[str]] = None

class ExportResponse(BaseModel):
    download_url: str
    filename: str
    format: str
    record_count: int
    file_size_bytes: int
    domain_knowledge_filename: Optional[str] = None
    domain_knowledge_hash: Optional[str] = None

class DomainKnowledgeResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    filename: str
    content: str
    content_hash: str
    record_count: int
    generator_version: str
    generated_at: str
    download_url: str

