from typing import Optional, List
from pydantic import BaseModel, Field

class ExportRequest(BaseModel):
    format: str = "csv"  # csv, json, xlsx, parquet
    include_provenance: bool = True
    only_valid_records: bool = False
    selected_columns: Optional[List[str]] = None

class ExportResponse(BaseModel):
    download_url: str
    filename: str
    format: str
    record_count: int
    file_size_bytes: int
