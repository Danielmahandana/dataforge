export interface Project {
  id: string;
  name: string;
  description?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  document_count: number;
  dataset_count: number;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  original_name: string;
  file_path: string;
  file_size: number;
  file_hash?: string;
  mime_type: string;
  page_count: number;
  doc_type: 'qualifications' | 'occupations' | 'codebook' | 'general_table' | 'unclassified';
  doc_metadata: Record<string, any>;
  status: 'uploaded' | 'inspected' | 'processing' | 'extracted' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface DocumentInspection {
  id: string;
  filename: string;
  page_count: number;
  doc_type: string;
  doc_metadata: Record<string, any>;
  pages_sample: Array<{
    page_number: number;
    width: number;
    height: number;
    text_preview: string;
    table_count: number;
  }>;
  detected_tables_count: number;
  has_text_layer: boolean;
}

export interface ExtractionJob {
  id: string;
  project_id: string;
  document_id: string;
  dataset_id?: string;
  pipeline_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  parameters: Record<string, any>;
  progress: number;
  metrics: {
    total_documents?: number;
    total_tables?: number;
    records_extracted?: number;
    valid_records?: number;
    errors_count?: number;
    warnings_count?: number;
    quality_score?: number;
    duration_ms?: number;
  };
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ColumnDefinition {
  name: string;
  original_name?: string;
  type: 'string' | 'integer' | 'float' | 'boolean';
  required: boolean;
  description?: string;
}

export interface Dataset {
  id: string;
  project_id: string;
  document_id?: string;
  name: string;
  description?: string;
  schema_name: string;
  schema_columns: ColumnDefinition[];
  record_count: number;
  valid_record_count: number;
  warning_record_count: number;
  error_record_count: number;
  quality_score: number;
  status: 'raw' | 'normalized' | 'validated' | 'reviewed' | 'published';
  created_at: string;
  updated_at: string;
}

export interface Provenance {
  document_id?: string;
  document_name?: string;
  page_number?: number;
  table_index?: number;
  bounding_box?: [number, number, number, number];
  method?: string;
}

export interface DatasetRecord {
  id: string;
  dataset_id: string;
  row_index: number;
  data: Record<string, any>;
  raw_data?: Record<string, any>;
  confidence_score: number;
  provenance: Provenance;
  status: 'valid' | 'warning' | 'error' | 'human_reviewed';
  review_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface RecordListResponse {
  total: number;
  page: number;
  page_size: number;
  records: DatasetRecord[];
}

export interface ValidationIssue {
  id: string;
  dataset_id: string;
  record_id?: string;
  row_index?: number;
  column_name?: string;
  rule_name: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  raw_value?: string;
  is_resolved: boolean;
  resolved_by?: string;
  resolution_comment?: string;
  created_at: string;
}

export interface ValidationSummary {
  dataset_id: string;
  quality_score: number;
  total_records: number;
  valid_records: number;
  warning_records: number;
  error_records: number;
  issues_by_severity: {
    error: number;
    warning: number;
    info: number;
  };
  issues_by_column: Record<string, number>;
  issues: ValidationIssue[];
}

export interface ReviewAudit {
  id: string;
  dataset_id: string;
  record_id: string;
  action: 'edit_field' | 'approve_record' | 'reject_record' | 'flag_record' | 'update_record' | 'resolve_issue';
  field_name?: string;
  old_value?: string;
  new_value?: string;
  reason?: string;
  reviewed_by: string;
  created_at: string;
}

export interface ActivityLog {
  id: string;
  project_id?: string;
  entity_type: string;
  entity_id?: string;
  action: string;
  description: string;
  user: string;
  details: Record<string, any>;
  created_at: string;
}

export interface ExportResponse {
  download_url: string;
  filename: string;
  format: string;
  record_count: number;
  file_size_bytes: number;
}
