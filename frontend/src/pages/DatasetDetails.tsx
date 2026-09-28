import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Eye,
  Edit2,
  CheckCircle,
  AlertTriangle,
  Download,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  FileText,
  X,
  Sparkles,
  Package,
  Network,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { DatasetRecord, EvidenceItem, LineageGraph } from '../types';
import { DatasetAIAssistant } from '../components/DatasetAIAssistant';
import { QualityGatesCard } from '../components/common/QualityGatesCard';
import { EvidenceModal } from '../components/common/EvidenceModal';
import { LineageModal } from '../components/common/LineageModal';
import { CurationRunModal } from '../components/common/CurationRunModal';

export const DatasetDetails: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const queryClient = useQueryClient();
  const { openSourceModal } = useAppStore();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [curationFilter, setCurationFilter] = useState('');
  const [editingRecord, setEditingRecord] = useState<DatasetRecord | null>(null);
  const [editFormData, setEditFormData] = useState<Record<string, any>>({});
  const [editNotes, setEditNotes] = useState('');
  const [relationalExportData, setRelationalExportData] = useState<any | null>(null);
  const [isExportingRelational, setIsExportingRelational] = useState(false);

  // Curation & Evidence Modals
  const [isCurationModalOpen, setIsCurationModalOpen] = useState(false);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
  const [selectedRecordForEvidence, setSelectedRecordForEvidence] = useState<DatasetRecord | null>(null);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);
  const [lineageModalOpen, setLineageModalOpen] = useState(false);
  const [selectedRecordForLineage, setSelectedRecordForLineage] = useState<DatasetRecord | null>(null);
  const [lineageData, setLineageData] = useState<LineageGraph | null>(null);

  const { data: dataset, isLoading: isDatasetLoading } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => apiClient.getDataset(datasetId!),
    enabled: !!datasetId,
  });

  const { data: recordsData, isLoading: isRecordsLoading } = useQuery({
    queryKey: ['records', datasetId, page, pageSize, statusFilter, search],
    queryFn: () =>
      apiClient.getRecords(datasetId!, {
        page,
        page_size: pageSize,
        status_filter: statusFilter || undefined,
        search: search || undefined,
      }),
    enabled: !!datasetId,
  });

  const updateRecordMutation = useMutation({
    mutationFn: ({ id, data, notes }: { id: string; data: any; notes?: string }) =>
      apiClient.updateRecord(id, { data, review_notes: notes, status: 'human_reviewed' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      setEditingRecord(null);
    },
  });

  const reviewActionMutation = useMutation({
    mutationFn: ({ recordId, action }: { recordId: string; action: string }) =>
      apiClient.createReviewAudit({
        record_id: recordId,
        action,
        reviewed_by: 'Researcher',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
    },
  });

  const handleOpenEvidence = async (rec: DatasetRecord) => {
    setSelectedRecordForEvidence(rec);
    setEvidenceModalOpen(true);
    try {
      const items = await apiClient.getRecordEvidence(rec.id);
      setEvidenceItems(items);
    } catch {
      setEvidenceItems([]);
    }
  };

  const handleOpenLineage = async (rec: DatasetRecord) => {
    setSelectedRecordForLineage(rec);
    setLineageModalOpen(true);
    try {
      const data = await apiClient.getRecordLineage(rec.id);
      setLineageData(data);
    } catch {
      setLineageData(null);
    }
  };

  const handleExportRelationalPackage = async () => {
    if (!datasetId) return;
    setIsExportingRelational(true);
    try {
      const res = await apiClient.exportRelationalPackage(datasetId);
      setRelationalExportData(res);
    } catch (err: any) {
      alert('Relational Package Export failed: ' + (err.message || 'Error occurred'));
    } finally {
      setIsExportingRelational(false);
    }
  };

  if (isDatasetLoading) {
    return (
      <div className="p-12 text-center text-zinc-500 text-xs font-sans">
        Loading dataset schema and records...
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="p-12 text-center text-rose-400 font-sans text-xs">
        Dataset not found.
      </div>
    );
  }

  const columns = dataset.schema_columns || [];
  const rawRecords = recordsData?.records || [];
  const records = rawRecords.filter((r) => {
    if (!curationFilter) return true;
    return (r.curation_decision || 'unprocessed').toUpperCase() === curationFilter.toUpperCase();
  });
  const total = recordsData?.total || 0;
  const totalPages = Math.ceil(total / pageSize) || 1;

  const handleEditClick = (record: DatasetRecord) => {
    setEditingRecord(record);
    setEditFormData({ ...record.data });
    setEditNotes(record.review_notes || '');
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRecord) return;
    updateRecordMutation.mutate({
      id: editingRecord.id,
      data: editFormData,
      notes: editNotes,
    });
  };

  const curSummary = dataset.curation_summary || { included: 0, excluded: 0, review_required: 0, unprocessed: 0 };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link
              to="/datasets"
              className="text-xs text-zinc-400 hover:text-amber-400 flex items-center space-x-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>All Datasets</span>
            </Link>
          </div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight mt-1 flex items-center space-x-2">
            <span>{dataset.name}</span>
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400 mt-1">
            <span>Model: <strong className="text-zinc-200 capitalize">{dataset.schema_name}</strong></span>
            <span>•</span>
            <span>{dataset.record_count.toLocaleString()} Total Records</span>
            <span>•</span>
            <span>Quality Score: <strong className="text-amber-400">{dataset.quality_score}%</strong></span>
            {dataset.policy_id && (
              <>
                <span>•</span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px] border border-slate-700">
                  Policy: {dataset.policy_id}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsCurationModalOpen(true)}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl shadow-sm transition"
          >
            <Sparkles className="w-4 h-4" />
            <span>Run Semantic Curation</span>
          </button>
          <button
            onClick={handleExportRelationalPackage}
            disabled={isExportingRelational}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-amber-400 hover:bg-amber-300 text-black text-xs font-semibold rounded-xl shadow-sm transition"
          >
            <Package className="w-4 h-4" />
            <span>{isExportingRelational ? 'Decomposing...' : 'Export Relational Package'}</span>
          </button>
          <Link
            to="/exports"
            state={{ defaultDatasetId: dataset.id }}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 text-xs text-zinc-200 border border-zinc-800 rounded-xl transition"
          >
            <Download className="w-4 h-4 text-amber-400" />
            <span>Standard Export</span>
          </Link>
          <Link
            to="/validation"
            state={{ defaultDatasetId: dataset.id }}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 text-xs text-zinc-200 border border-zinc-800 rounded-xl transition"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Audit Validation</span>
          </Link>
        </div>
      </div>

      {/* Quality Gates & Dimension Scorecard */}
      <QualityGatesCard
        dimensions={dataset.quality_dimensions as any}
        gates={dataset.quality_gates_status}
        overallScore={dataset.quality_score}
        criticalIssuesCount={dataset.error_record_count}
      />

      {/* Curation Summary Metric Chips */}
      {(curSummary.included > 0 || curSummary.review_required > 0 || curSummary.excluded > 0) && (
        <div className="flex flex-wrap items-center gap-3 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
          <span className="text-slate-400 font-medium">Curation Decision Breakdown:</span>
          <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold font-mono">
            {curSummary.included} INCLUDED
          </span>
          <span className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold font-mono">
            {curSummary.review_required} IN REVIEW
          </span>
          <span className="px-2.5 py-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold font-mono">
            {curSummary.excluded} EXCLUDED
          </span>
          <Link
            to="/review"
            state={{ defaultDatasetId: dataset.id }}
            className="ml-auto text-sky-400 hover:text-sky-300 font-semibold text-xs flex items-center gap-1"
          >
            Open Prioritized Review Queue →
          </Link>
        </div>
      )}

      {/* Relational Package Downloads Modal / Panel */}
      {relationalExportData && (
        <div className="p-5 bg-[#121215] border border-amber-500/40 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs">
              <Sparkles className="w-4 h-4" />
              <span>Relational Package Ready (Palantir Ontology Decomposition)</span>
            </div>
            <button
              onClick={() => setRelationalExportData(null)}
              className="text-zinc-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(relationalExportData.tables || {}).map(([key, tbl]: [string, any]) => (
              <a
                key={key}
                href={tbl.download_url}
                download
                className="p-3 bg-[#09090b] border border-zinc-800 hover:border-amber-400/60 rounded-xl text-xs flex flex-col justify-between transition group"
              >
                <div className="font-semibold text-zinc-200 group-hover:text-amber-400 capitalize truncate">
                  {key.replace(/_/g, ' ')}
                </div>
                <div className="text-[11px] text-zinc-500 mt-1 flex items-center justify-between">
                  <span>{tbl.records} records</span>
                  <Download className="w-3.5 h-3.5 text-amber-400" />
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Dataset AI Assistant Widget */}
      <DatasetAIAssistant datasetId={dataset.id} datasetName={dataset.name} />

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#121215] p-4 rounded-2xl border border-zinc-800 text-xs">
        <div className="flex items-center space-x-3 flex-1 min-w-[280px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search record values..."
              className="w-full pl-10 pr-4 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3.5 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
          >
            <option value="">All Validation Statuses</option>
            <option value="valid">Valid Only</option>
            <option value="warning">Warnings</option>
            <option value="error">Errors</option>
            <option value="human_reviewed">Human Reviewed</option>
          </select>

          <select
            value={curationFilter}
            onChange={(e) => {
              setCurationFilter(e.target.value);
              setPage(1);
            }}
            className="px-3.5 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-emerald-400"
          >
            <option value="">All Curation Decisions</option>
            <option value="INCLUDE">INCLUDE Only</option>
            <option value="REVIEW">REVIEW Only</option>
            <option value="EXCLUDE">EXCLUDE Only</option>
            <option value="unprocessed">Unprocessed</option>
          </select>
        </div>

        <div className="flex items-center space-x-2 text-zinc-400">
          <span>Rows per page:</span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="px-2.5 py-1 bg-[#09090b] border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none"
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </div>

      {/* Dataset Data Table */}
      <div className="bg-[#121215] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto max-h-[60vh]">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead className="bg-zinc-900/90 sticky top-0 z-10 border-b border-zinc-800 text-zinc-300">
              <tr>
                <th className="p-3.5 w-12 text-center">#</th>
                <th className="p-3.5">Curation Decision</th>
                <th className="p-3.5">Confidence</th>
                <th className="p-3.5">Validation</th>
                <th className="p-3.5">Source Lineage</th>
                {columns.map((col) => (
                  <th key={col.name} className="p-3.5">
                    <div className="flex flex-col">
                      <span className="font-semibold text-zinc-100">{col.name}</span>
                      <span className="text-[10px] text-zinc-500 font-normal">{col.type}</span>
                    </div>
                  </th>
                ))}
                <th className="p-3.5 text-right">Evidence & Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
              {records.map((record) => {
                const prov = record.provenance || {};
                const dec = record.curation_decision || 'unprocessed';
                const conf = record.confidence_score !== undefined ? record.confidence_score : 1.0;

                return (
                  <tr
                    key={record.id}
                    className="hover:bg-zinc-800/40 transition-colors"
                  >
                    <td className="p-3.5 text-center text-zinc-500 font-semibold">
                      {record.row_index}
                    </td>

                    {/* Curation Decision Badge */}
                    <td className="p-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          dec === 'INCLUDE'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                            : dec === 'EXCLUDE'
                            ? 'bg-rose-950/60 text-rose-400 border border-rose-800/50'
                            : dec === 'REVIEW'
                            ? 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
                            : 'bg-zinc-800/60 text-slate-400 border border-zinc-700/50'
                        }`}
                      >
                        {dec}
                      </span>
                    </td>

                    {/* Multi-Dimensional Confidence */}
                    <td className="p-3.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[11px] font-semibold text-slate-200">
                          {Math.round(conf * 100)}%
                        </span>
                        {record.multi_confidence && (
                          <span
                            className="text-[10px] text-slate-500 cursor-help"
                            title={`Extraction: ${Math.round((record.multi_confidence.extraction || 1)*100)}% | Normalization: ${Math.round((record.multi_confidence.normalization || 1)*100)}% | Validation: ${Math.round((record.multi_confidence.validation || 1)*100)}% | Curation: ${Math.round((record.multi_confidence.curation || 1)*100)}%`}
                          >
                            ℹ️
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Validation Status */}
                    <td className="p-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          record.status === 'valid'
                            ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-800/40'
                            : record.status === 'warning'
                            ? 'bg-amber-950/50 text-amber-400 border border-amber-800/40'
                            : record.status === 'error'
                            ? 'bg-rose-950/50 text-rose-400 border border-rose-800/40'
                            : 'bg-zinc-800 text-amber-400 border border-amber-500/40'
                        }`}
                      >
                        {record.status}
                      </span>
                    </td>

                    {/* Source Lineage */}
                    <td className="p-3.5">
                      {prov.document_id ? (
                        <button
                          onClick={() =>
                            openSourceModal({
                              documentId: prov.document_id,
                              documentName: prov.document_name || 'Source PDF',
                              pageNumber: prov.page_number || 1,
                              recordIndex: record.row_index,
                            })
                          }
                          className="flex items-center space-x-1 px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-amber-400 border border-zinc-800 rounded text-[11px] transition"
                          title="Open exact PDF page in viewer"
                        >
                          <FileText className="w-3 h-3 text-amber-400" />
                          <span>p.{prov.page_number || 1}</span>
                          <Eye className="w-3 h-3 ml-0.5 opacity-70" />
                        </button>
                      ) : (
                        <span className="text-zinc-600 text-[11px]">N/A</span>
                      )}
                    </td>

                    {/* Column values */}
                    {columns.map((col) => {
                      const val = record.data?.[col.name];
                      const valStr = val !== null && val !== undefined ? String(val) : '';
                      return (
                        <td
                          key={col.name}
                          className="p-3.5 max-w-xs truncate"
                          title={valStr}
                        >
                          {valStr || <span className="text-zinc-600 italic">null</span>}
                        </td>
                      );
                    })}

                    {/* Actions */}
                    <td className="p-3.5 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <button
                          onClick={() => handleOpenEvidence(record)}
                          className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[11px] font-medium flex items-center gap-1 transition"
                          title="View Verifiable Evidence Set"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Evidence</span>
                        </button>
                        <button
                          onClick={() => handleOpenLineage(record)}
                          className="px-2 py-1 rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/30 text-[11px] font-medium flex items-center gap-1 transition"
                          title="View Full Provenance Lineage"
                        >
                          <Network className="w-3.5 h-3.5" />
                          <span>Lineage</span>
                        </button>
                        <button
                          onClick={() => handleEditClick(record)}
                          className="p-1 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded transition"
                          title="Edit Row Values"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        <div className="p-4 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-400">
          <div>
            Showing {records.length} of {total} records
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-zinc-200">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Row Edit Modal */}
      {editingRecord && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121215] border border-zinc-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-semibold text-zinc-100 flex items-center space-x-2">
                <Edit2 className="w-4 h-4 text-amber-400" />
                <span>Edit Record Row #{editingRecord.row_index}</span>
              </h3>
              <button
                onClick={() => setEditingRecord(null)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
              {columns.map((col) => (
                <div key={col.name}>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1 capitalize">
                    {col.name.replace(/_/g, ' ')}
                  </label>
                  <input
                    type="text"
                    value={editFormData[col.name] !== undefined ? editFormData[col.name] : ''}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        [col.name]: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
                  />
                </div>
              ))}

              <div>
                <label className="block text-xs text-zinc-300 mb-1">
                  Researcher Review Notes (Audit Trail)
                </label>
                <textarea
                  rows={2}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Reason for manual edit, verified document source..."
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="pt-4 border-t border-zinc-800 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setEditingRecord(null)}
                  className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-xs text-zinc-300 rounded-xl border border-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateRecordMutation.isPending}
                  className="px-4 py-2 bg-amber-400 hover:bg-amber-300 text-black text-xs font-semibold rounded-xl"
                >
                  Save & Apply Audit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Curation Run Modal */}
      <CurationRunModal
        isOpen={isCurationModalOpen}
        onClose={() => setIsCurationModalOpen(false)}
        datasetId={dataset.id}
        datasetName={dataset.name}
        projectId={dataset.project_id}
        onRunStarted={() => {
          queryClient.invalidateQueries({ queryKey: ['records', datasetId] });
          queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
        }}
      />

      {/* Evidence Explorer Modal */}
      <EvidenceModal
        isOpen={evidenceModalOpen}
        onClose={() => setEvidenceModalOpen(false)}
        recordTitle={
          selectedRecordForEvidence
            ? String(
                selectedRecordForEvidence.data.occupation_title ||
                selectedRecordForEvidence.data.qualification ||
                `Row #${selectedRecordForEvidence.row_index}`
              )
            : ''
        }
        evidenceItems={evidenceItems}
        curationDecision={selectedRecordForEvidence?.curation_decision}
        confidence={selectedRecordForEvidence?.confidence_score}
        onViewSource={() => {
          if (selectedRecordForEvidence?.provenance?.document_id) {
            openSourceModal({
              documentId: selectedRecordForEvidence.provenance.document_id,
              documentName: selectedRecordForEvidence.provenance.document_name || 'Source Document',
              pageNumber: selectedRecordForEvidence.provenance.page_number || 1,
              recordIndex: selectedRecordForEvidence.row_index,
            });
          }
        }}
      />

      {/* Lineage Modal */}
      <LineageModal
        isOpen={lineageModalOpen}
        onClose={() => setLineageModalOpen(false)}
        recordTitle={
          selectedRecordForLineage
            ? String(
                selectedRecordForLineage.data.occupation_title ||
                selectedRecordForLineage.data.qualification ||
                `Row #${selectedRecordForLineage.row_index}`
              )
            : ''
        }
        lineage={lineageData}
        onViewSource={(docId, pageNum) => {
          openSourceModal({
            documentId: docId,
            documentName: 'Source Document',
            pageNumber: pageNum,
            recordIndex: selectedRecordForLineage?.row_index || 1,
          });
        }}
      />
    </div>
  );
};
