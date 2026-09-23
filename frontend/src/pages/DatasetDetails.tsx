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
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { DatasetRecord } from '../types';
import { DatasetAIAssistant } from '../components/DatasetAIAssistant';

export const DatasetDetails: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const queryClient = useQueryClient();
  const { openSourceModal } = useAppStore();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [editingRecord, setEditingRecord] = useState<DatasetRecord | null>(null);
  const [editFormData, setEditFormData] = useState<Record<string, any>>({});
  const [editNotes, setEditNotes] = useState('');
  const [relationalExportData, setRelationalExportData] = useState<any | null>(null);
  const [isExportingRelational, setIsExportingRelational] = useState(false);

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
  const records = recordsData?.records || [];
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
          <p className="text-xs text-zinc-400 mt-0.5">
            Model: <span className="text-zinc-200 capitalize">{dataset.schema_name}</span> • {dataset.record_count.toLocaleString()} Total Records • Quality Score: <span className="text-amber-400 font-semibold">{dataset.quality_score}%</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
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
            <option value="">All Statuses</option>
            <option value="valid">Valid Only</option>
            <option value="warning">Warnings</option>
            <option value="error">Errors</option>
            <option value="human_reviewed">Human Reviewed</option>
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
                <th className="p-3.5 w-14 text-center">#</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Source Lineage</th>
                {columns.map((col) => (
                  <th key={col.name} className="p-3.5">
                    <div className="flex flex-col">
                      <span className="font-semibold text-zinc-100">{col.name}</span>
                      <span className="text-[10px] text-zinc-500 font-normal">{col.type}</span>
                    </div>
                  </th>
                ))}
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
              {records.map((record) => {
                const prov = record.provenance || {};
                return (
                  <tr
                    key={record.id}
                    className="hover:bg-zinc-800/40 transition-colors"
                  >
                    <td className="p-3.5 text-center text-zinc-500 font-semibold">
                      {record.row_index}
                    </td>
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
                          className="flex items-center space-x-1.5 px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-amber-400 border border-zinc-800 rounded-lg text-[11px] transition"
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
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => handleEditClick(record)}
                          className="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded-lg transition"
                          title="Edit Row Values"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() =>
                            reviewActionMutation.mutate({
                              recordId: record.id,
                              action: 'approve_record',
                            })
                          }
                          className="p-1.5 text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800 rounded-lg transition"
                          title="Approve Record"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() =>
                            reviewActionMutation.mutate({
                              recordId: record.id,
                              action: 'flag_record',
                            })
                          }
                          className="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded-lg transition"
                          title="Flag for Investigation"
                        >
                          <AlertTriangle className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {records.length === 0 && !isRecordsLoading && (
          <div className="p-12 text-center text-zinc-500 text-xs">
            No records match current filter criteria.
          </div>
        )}

        {/* Pagination Footer */}
        <div className="p-4 bg-zinc-900/60 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-400">
          <div>
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} records
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 bg-[#09090b] border border-zinc-800 rounded-lg hover:text-white disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-zinc-200 font-semibold">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 bg-[#09090b] border border-zinc-800 rounded-lg hover:text-white disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Edit Record Modal */}
      {editingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl bg-[#121215] border border-zinc-800 rounded-2xl shadow-2xl p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <h3 className="text-sm font-semibold text-zinc-100">
                Edit Record #{editingRecord.row_index}
              </h3>
              <button
                onClick={() => setEditingRecord(null)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="flex-1 overflow-y-auto mt-4 space-y-4 pr-1">
              {columns.map((col) => (
                <div key={col.name}>
                  <label className="block text-xs text-zinc-300 mb-1">
                    {col.name} {col.required && <span className="text-rose-400">*</span>}
                  </label>
                  <input
                    type="text"
                    value={editFormData[col.name] ?? ''}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, [col.name]: e.target.value })
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
    </div>
  );
};
