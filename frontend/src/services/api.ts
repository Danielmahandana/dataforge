import axios from 'axios';
import {
  Project,
  Document,
  DocumentInspection,
  ExtractionJob,
  Dataset,
  DatasetRecord,
  RecordListResponse,
  ValidationSummary,
  ValidationIssue,
  ReviewAudit,
  ActivityLog,
  ExportResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiClient = {
  // Health
  getHealth: async () => {
    const res = await api.get('/health');
    return res.data;
  },

  // Projects
  getProjects: async (): Promise<Project[]> => {
    const res = await api.get('/projects');
    return res.data;
  },
  getProject: async (id: string): Promise<Project> => {
    const res = await api.get(`/projects/${id}`);
    return res.data;
  },
  createProject: async (data: { name: string; description?: string; tags?: string[] }): Promise<Project> => {
    const res = await api.post('/projects', data);
    return res.data;
  },
  updateProject: async (id: string, data: { name?: string; description?: string; tags?: string[] }): Promise<Project> => {
    const res = await api.put(`/projects/${id}`, data);
    return res.data;
  },
  deleteProject: async (id: string): Promise<void> => {
    await api.delete(`/projects/${id}`);
  },

  // Documents
  getDocuments: async (projectId?: string): Promise<Document[]> => {
    const res = await api.get('/documents', { params: { project_id: projectId } });
    return res.data;
  },
  getDocument: async (id: string): Promise<Document> => {
    const res = await api.get(`/documents/${id}`);
    return res.data;
  },
  uploadDocuments: async (projectId: string, files: File[], docType?: string): Promise<Document[]> => {
    const formData = new FormData();
    formData.append('project_id', projectId);
    if (docType) {
      formData.append('doc_type', docType);
    }
    files.forEach((file) => {
      formData.append('files', file);
    });

    const res = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },
  inspectDocument: async (id: string): Promise<DocumentInspection> => {
    const res = await api.get(`/documents/${id}/inspect`);
    return res.data;
  },
  updateDocument: async (id: string, data: { doc_type?: string; status?: string }): Promise<Document> => {
    const res = await api.patch(`/documents/${id}`, data);
    return res.data;
  },
  deleteDocument: async (id: string): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },
  getDocumentFileUrl: (id: string): string => {
    return `/api/v1/documents/${id}/file`;
  },

  // Extraction
  getJobs: async (projectId?: string): Promise<ExtractionJob[]> => {
    const res = await api.get('/extraction/jobs', { params: { project_id: projectId } });
    return res.data;
  },
  getJob: async (id: string): Promise<ExtractionJob> => {
    const res = await api.get(`/extraction/jobs/${id}`);
    return res.data;
  },
  createJob: async (data: {
    project_id: string;
    document_ids: string[];
    pipeline_type: string;
    parameters?: Record<string, any>;
    target_dataset_name?: string;
  }): Promise<ExtractionJob> => {
    const res = await api.post('/extraction/jobs', data);
    return res.data;
  },

  // Datasets
  getDatasets: async (projectId?: string): Promise<Dataset[]> => {
    const res = await api.get('/datasets', { params: { project_id: projectId } });
    return res.data;
  },
  getDataset: async (id: string): Promise<Dataset> => {
    const res = await api.get(`/datasets/${id}`);
    return res.data;
  },
  updateDataset: async (id: string, data: { name?: string; description?: string; status?: string }): Promise<Dataset> => {
    const res = await api.patch(`/datasets/${id}`, data);
    return res.data;
  },
  deleteDataset: async (id: string): Promise<void> => {
    await api.delete(`/datasets/${id}`);
  },

  // Records
  getRecords: async (
    datasetId: string,
    params?: { page?: number; page_size?: number; status_filter?: string; search?: string }
  ): Promise<RecordListResponse> => {
    const res = await api.get(`/datasets/${datasetId}/records`, { params });
    return res.data;
  },
  getRecord: async (id: string): Promise<DatasetRecord> => {
    const res = await api.get(`/records/${id}`);
    return res.data;
  },
  updateRecord: async (
    id: string,
    data: { data?: Record<string, any>; status?: string; review_notes?: string }
  ): Promise<DatasetRecord> => {
    const res = await api.patch(`/records/${id}`, data);
    return res.data;
  },
  deleteRecord: async (id: string): Promise<void> => {
    await api.delete(`/records/${id}`);
  },

  // Validation
  getValidationSummary: async (datasetId: string): Promise<ValidationSummary> => {
    const res = await api.get(`/validation/datasets/${datasetId}`);
    return res.data;
  },
  resolveValidationIssue: async (
    issueId: string,
    data: { is_resolved?: boolean; resolved_by?: string; resolution_comment?: string; corrected_value?: string }
  ): Promise<ValidationIssue> => {
    const res = await api.patch(`/validation/issues/${issueId}/resolve`, data);
    return res.data;
  },

  // Review
  createReviewAudit: async (data: {
    record_id: string;
    action: string;
    field_name?: string;
    old_value?: string;
    new_value?: string;
    reason?: string;
    reviewed_by?: string;
  }): Promise<ReviewAudit> => {
    const res = await api.post('/review/audit', data);
    return res.data;
  },
  getDatasetReviews: async (datasetId: string): Promise<ReviewAudit[]> => {
    const res = await api.get(`/review/datasets/${datasetId}`);
    return res.data;
  },

  // Exports
  exportDataset: async (
    datasetId: string,
    payload: { format: string; include_provenance?: boolean; only_valid_records?: boolean; selected_columns?: string[] }
  ): Promise<ExportResponse> => {
    const res = await api.post(`/datasets/${datasetId}/export`, payload);
    return res.data;
  },
  exportRelationalPackage: async (datasetId: string) => {
    const res = await api.post(`/datasets/${datasetId}/relational-export`);
    return res.data;
  },

  // Activity
  getActivity: async (projectId?: string, limit: number = 50): Promise<ActivityLog[]> => {
    const res = await api.get('/activity', { params: { project_id: projectId, limit } });
    return res.data;
  },

  // LLM Intelligence
  getLLMStatus: async () => {
    const res = await api.get('/llm/status');
    return res.data;
  },
  queryDatasetWithLLM: async (datasetId: string, query: string) => {
    const res = await api.post('/llm/query-dataset', { dataset_id: datasetId, query });
    return res.data;
  },
  explainIssueWithLLM: async (issueId: string) => {
    const res = await api.post('/llm/explain-issue', { issue_id: issueId });
    return res.data;
  },
  summarizeDatasetWithLLM: async (datasetId: string) => {
    const res = await api.post('/llm/summarize-dataset', { dataset_id: datasetId });
    return res.data;
  },

  // System Clean / Reset
  resetSystem: async (): Promise<{ status: string; message: string }> => {
    const res = await api.post('/system/reset');
    return res.data;
  },
};
