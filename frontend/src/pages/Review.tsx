import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  History,
  Database,
  UserCheck,
  AlertTriangle,
  ShieldAlert,
  CheckCircle,
  XCircle,
  FileText,
  ShieldCheck,
  ListOrdered,
  Eye,
  MessageSquare,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { ReviewQueueItem, EvidenceItem } from '../types';
import { EvidenceModal } from '../components/common/EvidenceModal';

export const Review: React.FC = () => {
  const { selectedProjectId, openSourceModal } = useAppStore();
  const queryClient = useQueryClient();
  const [activeDatasetId, setActiveDatasetId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'queue' | 'history'>('queue');
  const [priorityFilter, setPriorityFilter] = useState<'all' | 'critical' | 'high' | 'medium'>('all');

  // Override Modal state
  const [overrideItem, setOverrideItem] = useState<ReviewQueueItem | null>(null);
  const [overrideDecision, setOverrideDecision] = useState<'INCLUDE' | 'EXCLUDE'>('INCLUDE');
  const [overrideNotes, setOverrideNotes] = useState('');

  // Evidence Modal state
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
  const [selectedRecordForEvidence, setSelectedRecordForEvidence] = useState<ReviewQueueItem | null>(null);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  const { data: reviewQueue, isLoading: isQueueLoading } = useQuery({
    queryKey: ['review-queue', activeDatasetId],
    queryFn: () => apiClient.getReviewQueue(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  const { data: reviews = [] } = useQuery({
    queryKey: ['reviews', activeDatasetId],
    queryFn: () => apiClient.getDatasetReviews(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  const reviewDecisionMutation = useMutation({
    mutationFn: ({ recordId, decision, notes }: { recordId: string; decision: string; notes?: string }) =>
      apiClient.reviewRecordDecision(recordId, {
        decision,
        notes,
        reviewer_name: 'Lead Researcher',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['reviews', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['records', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', activeDatasetId] });
      setOverrideItem(null);
    },
  });

  const handleOpenEvidence = async (item: ReviewQueueItem) => {
    setSelectedRecordForEvidence(item);
    setEvidenceModalOpen(true);
    try {
      const items = await apiClient.getRecordEvidence(item.record_id);
      setEvidenceItems(items);
    } catch {
      setEvidenceItems([]);
    }
  };

  const handleQuickApprove = (item: ReviewQueueItem) => {
    reviewDecisionMutation.mutate({
      recordId: item.record_id,
      decision: 'INCLUDE',
      notes: 'Approved via Prioritized Review Queue',
    });
  };

  const handleQuickExclude = (item: ReviewQueueItem) => {
    reviewDecisionMutation.mutate({
      recordId: item.record_id,
      decision: 'EXCLUDE',
      notes: 'Excluded via Prioritized Review Queue',
    });
  };

  const handleOpenOverride = (item: ReviewQueueItem, defaultDecision: 'INCLUDE' | 'EXCLUDE') => {
    setOverrideItem(item);
    setOverrideDecision(defaultDecision);
    setOverrideNotes('');
  };

  const handleConfirmOverride = (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideItem) return;
    reviewDecisionMutation.mutate({
      recordId: overrideItem.record_id,
      decision: overrideDecision,
      notes: overrideNotes || `Manually overridden to ${overrideDecision} by operator.`,
    });
  };

  const queueItems = (reviewQueue?.items || []).filter((item) => {
    if (priorityFilter === 'all') return true;
    return item.priority === priorityFilter;
  });

  return (
    <div className="space-y-6 font-sans max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight flex items-center gap-2">
            <span>Human-in-the-Loop Review & Governance Workbench</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Zero Blind Trust operator review queue and immutable decision ledger for the Wits–merSETA Darkroom team
          </p>
        </div>

        {/* Dataset Selector */}
        <div className="flex items-center space-x-2.5">
          <Database className="w-4 h-4 text-emerald-400" />
          <select
            value={activeDatasetId}
            onChange={(e) => setActiveDatasetId(e.target.value)}
            className="px-3 py-1.5 bg-[#121215] border border-zinc-800 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-emerald-500"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-3 border-b border-zinc-800 text-xs">
        <button
          onClick={() => setActiveTab('queue')}
          className={`pb-2.5 px-1 font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'queue'
              ? 'text-amber-400 border-amber-400'
              : 'text-zinc-400 border-transparent hover:text-zinc-200'
          }`}
        >
          <ListOrdered className="w-4 h-4" />
          <span>Prioritized Review Queue</span>
          {reviewQueue && reviewQueue.total_review_required > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-[10px] font-mono">
              {reviewQueue.total_review_required}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`pb-2.5 px-1 font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'history'
              ? 'text-emerald-400 border-emerald-400'
              : 'text-zinc-400 border-transparent hover:text-zinc-200'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Immutable Audit Trail</span>
          <span className="px-1.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400 text-[10px] font-mono">
            {reviews.length}
          </span>
        </button>
      </div>

      {/* TAB 1: REVIEW QUEUE */}
      {activeTab === 'queue' && (
        <div className="space-y-4">
          {/* Priority Metric Filters */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => setPriorityFilter('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                priorityFilter === 'all'
                  ? 'bg-zinc-800 text-white border border-zinc-700'
                  : 'bg-zinc-900/60 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
              }`}
            >
              All Attention Required ({reviewQueue?.total_review_required || 0})
            </button>
            <button
              onClick={() => setPriorityFilter('critical')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                priorityFilter === 'critical'
                  ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                  : 'bg-zinc-900/60 text-zinc-400 hover:text-red-400 border border-zinc-800'
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span>Critical ({reviewQueue?.critical_count || 0})</span>
            </button>
            <button
              onClick={() => setPriorityFilter('high')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                priorityFilter === 'high'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                  : 'bg-zinc-900/60 text-zinc-400 hover:text-amber-400 border border-zinc-800'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>High Priority ({reviewQueue?.high_count || 0})</span>
            </button>
            <button
              onClick={() => setPriorityFilter('medium')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                priorityFilter === 'medium'
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40'
                  : 'bg-zinc-900/60 text-zinc-400 hover:text-sky-400 border border-zinc-800'
              }`}
            >
              Medium Priority ({reviewQueue?.medium_count || 0})
            </button>
          </div>

          {/* Queue Items Table */}
          <div className="bg-[#121215] border border-zinc-800 rounded-xl overflow-hidden shadow-sm text-xs">
            {queueItems.length === 0 ? (
              <div className="p-12 text-center text-zinc-500 space-y-2">
                <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto opacity-70" />
                <p className="text-sm font-medium text-zinc-300">All Queue Items Resolved</p>
                <p className="text-xs">No records require operator review under current filters.</p>
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[65vh]">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-zinc-900/80 sticky top-0 border-b border-zinc-800 text-zinc-400 text-[11px]">
                    <tr>
                      <th className="p-3 w-12 text-center">Row</th>
                      <th className="p-3">Priority</th>
                      <th className="p-3">Record Title / Identifier</th>
                      <th className="p-3">Reason Code & Uncertainty</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Source Origin</th>
                      <th className="p-3 text-right">Triage Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                    {queueItems.map((item) => {
                      const prov = item.provenance || {};
                      return (
                        <tr key={item.record_id} className="hover:bg-zinc-900/40 transition-colors">
                          <td className="p-3 text-center text-zinc-500 font-mono font-medium">
                            {item.row_index}
                          </td>

                          {/* Priority */}
                          <td className="p-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                item.priority === 'critical'
                                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                  : item.priority === 'high'
                                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                  : 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                              }`}
                            >
                              {item.priority}
                            </span>
                          </td>

                          {/* Title */}
                          <td className="p-3">
                            <div className="font-semibold text-zinc-100 max-w-xs truncate" title={item.primary_title}>
                              {item.primary_title}
                            </div>
                            {item.identifier && (
                              <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                                ID: {item.identifier}
                              </div>
                            )}
                          </td>

                          {/* Reason */}
                          <td className="p-3 max-w-sm">
                            <span className="font-mono text-[10px] uppercase text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20 mr-1.5">
                              {item.reason_code.replace('_', ' ')}
                            </span>
                            <span className="text-zinc-300 text-xs">{item.reason_details}</span>
                          </td>

                          {/* Confidence */}
                          <td className="p-3">
                            <span className="font-mono font-semibold text-slate-200">
                              {Math.round(item.overall_confidence * 100)}%
                            </span>
                          </td>

                          {/* Source Origin */}
                          <td className="p-3">
                            {prov.document_id ? (
                              <button
                                onClick={() =>
                                  openSourceModal({
                                    documentId: prov.document_id,
                                    documentName: prov.document_name || 'Source PDF',
                                    pageNumber: prov.page_number || 1,
                                    recordIndex: item.row_index,
                                  })
                                }
                                className="flex items-center space-x-1 px-2 py-1 bg-zinc-900 hover:bg-zinc-800 text-amber-400 border border-zinc-800 rounded text-[11px] transition"
                              >
                                <FileText className="w-3 h-3 text-amber-400" />
                                <span>p.{prov.page_number || 1}</span>
                                <Eye className="w-3 h-3 opacity-70" />
                              </button>
                            ) : (
                              <span className="text-zinc-600 text-[11px]">N/A</span>
                            )}
                          </td>

                          {/* Triage Actions */}
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end space-x-1.5">
                              <button
                                onClick={() => handleOpenEvidence(item)}
                                className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[11px] font-medium flex items-center gap-1 transition"
                                title="View Evidence Items"
                              >
                                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                                <span>Evidence</span>
                              </button>
                              <button
                                onClick={() => handleQuickApprove(item)}
                                className="px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/40 rounded text-[11px] font-semibold transition"
                                title="Confirm Inclusion in Dataset"
                              >
                                Include
                              </button>
                              <button
                                onClick={() => handleQuickExclude(item)}
                                className="px-2 py-1 bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-500/40 rounded text-[11px] font-semibold transition"
                                title="Exclude from Dataset"
                              >
                                Exclude
                              </button>
                              <button
                                onClick={() => handleOpenOverride(item, 'INCLUDE')}
                                className="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition"
                                title="Override with Detailed Notes"
                              >
                                <MessageSquare className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AUDIT HISTORY */}
      {activeTab === 'history' && (
        <div className="bg-[#121215] border border-zinc-800 rounded-xl overflow-hidden shadow-sm text-xs">
          <div className="p-3.5 bg-zinc-900/60 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <History className="w-4 h-4 text-emerald-400" />
              <span className="font-semibold text-zinc-200">Audit History Entries</span>
              <span className="text-zinc-500 font-mono">({reviews.length} logs)</span>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[65vh]">
            <table className="w-full text-left border-collapse">
              <thead className="bg-zinc-900/80 border-b border-zinc-800 text-zinc-400 text-[11px]">
                <tr>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Record ID</th>
                  <th className="p-3">Field</th>
                  <th className="p-3">Change (Old → New)</th>
                  <th className="p-3">Reviewer Rationale</th>
                  <th className="p-3">Reviewer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                {reviews.map((rev) => (
                  <tr key={rev.id} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="p-3 text-zinc-400 text-[11px] font-mono">
                      {new Date(rev.created_at).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <Badge
                        variant={
                          rev.action.includes('approve') || rev.action.includes('INCLUDE')
                            ? 'success'
                            : rev.action.includes('reject') || rev.action.includes('EXCLUDE')
                            ? 'danger'
                            : 'warning'
                        }
                      >
                        {rev.action.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </td>
                    <td className="p-3 text-zinc-400 font-mono text-[11px]">{rev.record_id.slice(0, 8)}...</td>
                    <td className="p-3 text-zinc-400 font-mono text-[11px]">{rev.field_name || '-'}</td>
                    <td className="p-3 font-mono text-[11px] text-zinc-300">
                      {rev.old_value && <span className="text-rose-400 line-through mr-1.5">{rev.old_value}</span>}
                      {rev.new_value && <span className="text-emerald-400">{rev.new_value}</span>}
                    </td>
                    <td className="p-3 text-zinc-400">{rev.reason || '-'}</td>
                    <td className="p-3 font-mono text-zinc-400">{rev.reviewed_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Override with Notes Modal */}
      {overrideItem && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121215] border border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-emerald-400" />
              <span>Operator Decision Override</span>
            </h3>
            <p className="text-xs text-zinc-400">
              Record: <strong className="text-zinc-200">{overrideItem.primary_title}</strong> (Row #{overrideItem.row_index})
            </p>

            <form onSubmit={handleConfirmOverride} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Decision</label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setOverrideDecision('INCLUDE')}
                    className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition ${
                      overrideDecision === 'INCLUDE'
                        ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500'
                        : 'bg-zinc-900 text-zinc-400 border-zinc-800'
                    }`}
                  >
                    INCLUDE (Curated)
                  </button>
                  <button
                    type="button"
                    onClick={() => setOverrideDecision('EXCLUDE')}
                    className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition ${
                      overrideDecision === 'EXCLUDE'
                        ? 'bg-rose-600/30 text-rose-300 border-rose-500'
                        : 'bg-zinc-900 text-zinc-400 border-zinc-800'
                    }`}
                  >
                    EXCLUDE (Irrelevant)
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
                  Researcher Justification & Audit Notes
                </label>
                <textarea
                  rows={3}
                  required
                  value={overrideNotes}
                  onChange={(e) => setOverrideNotes(e.target.value)}
                  placeholder="Reference policy rationale, gazette notice, or verified chamber scope..."
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setOverrideItem(null)}
                  className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-xs text-zinc-300 rounded-xl border border-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reviewDecisionMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl"
                >
                  Apply & Record Audit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Evidence Modal */}
      <EvidenceModal
        isOpen={evidenceModalOpen}
        onClose={() => setEvidenceModalOpen(false)}
        recordTitle={selectedRecordForEvidence ? selectedRecordForEvidence.primary_title : ''}
        evidenceItems={evidenceItems}
        curationDecision={selectedRecordForEvidence?.decision}
        confidence={selectedRecordForEvidence?.overall_confidence}
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
    </div>
  );
};
