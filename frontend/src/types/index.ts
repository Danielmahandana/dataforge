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
  intent_id?: string;
  policy_id?: string;
  name: string;
  description?: string;
  version_label?: string;
  schema_name: string;
  schema_columns: ColumnDefinition[];
  record_count: number;
  valid_record_count: number;
  warning_record_count: number;
  error_record_count: number;
  quality_score: number;
  quality_dimensions?: {
    extraction: number;
    structural: number;
    normalization: number;
    validation: number;
    completeness: number;
    consistency: number;
    curation: number;
    provenance: number;
    overall: number;
  };
  quality_gates_status?: Record<string, string>;
  curation_summary?: {
    included: number;
    excluded: number;
    review_required: number;
    unprocessed: number;
  };
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
  derived_data?: Record<string, any>;
  confidence_score: number;
  multi_confidence?: {
    extraction: number;
    normalization: number;
    validation: number;
    curation: number;
    overall: number;
  };
  curation_decision?: 'unprocessed' | 'INCLUDE' | 'EXCLUDE' | 'REVIEW';
  curation_reason?: string;
  duplicate_status?: string;
  duplicate_of_id?: string;
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
  action: 'edit_field' | 'approve_record' | 'reject_record' | 'flag_record' | 'update_record' | 'resolve_issue' | 'curation_decision_override';
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

// --- Curation & Governance Domain Interfaces ---

export interface DatasetIntent {
  id: string;
  project_id?: string;
  name: string;
  description?: string;
  objective: string;
  scope: string[];
  include_criteria: string[];
  exclude_criteria: string[];
  authoritative_sources: string[];
  created_at: string;
  updated_at: string;
}

export interface CurationPolicy {
  id: string;
  name: string;
  description?: string;
  dimensions: Record<string, string>;
  rules: Array<{
    id: string;
    weight: number;
    description: string;
  }>;
  include_threshold: number;
  review_threshold: number;
  exclude_threshold: number;
  is_builtin: boolean;
}

export interface CurationRun {
  id: string;
  dataset_id: string;
  intent_id?: string;
  policy_id?: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  total_records: number;
  included_count: number;
  excluded_count: number;
  review_count: number;
  metrics: Record<string, any>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface EvidenceItem {
  id: string;
  record_id: string;
  decision_id?: string;
  evidence_type: 'source_text' | 'classification_hierarchy' | 'semantic_context' | 'sector_match' | 'rule_assertion' | 'human_verified';
  document_id?: string;
  document_name?: string;
  page_number?: number;
  table_index?: number;
  row_index?: number;
  cell_key?: string;
  source_text?: string;
  claim: string;
  rule_id?: string;
  confidence: number;
  created_at: string;
}

export interface DecisionLedgerEntry {
  id: string;
  record_id: string;
  dataset_id: string;
  stage: 'EXTRACTION' | 'NORMALIZATION' | 'CURATION' | 'CLASSIFICATION' | 'VALIDATION' | 'HUMAN_REVIEW';
  field_name?: string;
  previous_value?: string;
  new_value?: string;
  decision?: string;
  reason?: string;
  actor: string;
  actor_id: string;
  metadata_snapshot: Record<string, any>;
  created_at: string;
}

export interface LineageStep {
  stage: string;
  title: string;
  description: string;
  timestamp?: string;
  actor: string;
  status: string;
  data_snapshot: Record<string, any>;
  provenance?: Provenance;
}

export interface LineageGraph {
  record_id: string;
  dataset_id: string;
  source_document: {
    document_id?: string;
    document_name?: string;
    sha256_hash?: string;
    page_number?: number;
    table_index?: number;
    extraction_method?: string;
    bounding_box?: [number, number, number, number];
  };
  steps: LineageStep[];
  ledger: DecisionLedgerEntry[];
}

export interface ReviewQueueItem {
  record_id: string;
  dataset_id: string;
  row_index: number;
  primary_title: string;
  identifier?: string;
  decision: string;
  priority: 'critical' | 'high' | 'medium';
  reason_code: string;
  reason_details: string;
  overall_confidence: number;
  multi_confidence: {
    extraction: number;
    normalization: number;
    validation: number;
    curation: number;
    overall: number;
  };
  provenance: Provenance;
  data: Record<string, any>;
  raw_data?: Record<string, any>;
  derived_data?: Record<string, any>;
  evidence_summary: string[];
}

export interface ReviewQueueResponse {
  dataset_id: string;
  total_review_required: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  items: ReviewQueueItem[];
}

export interface QualityDimensions {
  extraction: number;
  structural: number;
  normalization: number;
  validation: number;
  completeness: number;
  consistency: number;
  curation: number;
  provenance: number;
  overall: number;
}

export interface QualityGates {
  overall_score: number;
  dimensions: QualityDimensions;
  gates: Record<string, string>;
  critical_issues_count: number;
  warning_count: number;
  can_export_clean: boolean;
  can_export_research: boolean;
  reasons: string[];
}
