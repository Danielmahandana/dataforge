import React, { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Info,
  CheckCircle2,
  Check,
  Database,
  Search,
  ExternalLink,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { ValidationIssue } from '../types';

export const Validation: React.FC = () => {
  const location = useLocation();
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const defaultDsId = location.state?.defaultDatasetId;

  const [activeDatasetId, setActiveDatasetId] = useState<string>(defaultDsId || '');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [resolvingIssue, setResolvingIssue] = useState<ValidationIssue | null>(null);
  const [correctedValue, setCorrectedValue] = useState<string>('');
  const [resolutionComment, setResolutionComment] = useState<string>('');

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  const { data: summary, isLoading } = useQuery({
    queryKey: ['validation-summary', activeDatasetId],
    queryFn: () => apiClient.getValidationSummary(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      apiClient.resolveValidationIssue(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validation-summary', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['records', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', activeDatasetId] });
      setResolvingIssue(null);
      setCorrectedValue('');
      setResolutionComment('');
    },
  });

  const handleResolveSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingIssue) return;
    resolveMutation.mutate({
      id: resolvingIssue.id,
      data: {
        is_resolved: true,
        resolved_by: 'Data Engineer',
        resolution_comment: resolutionComment,
        corrected_value: correctedValue.trim() ? correctedValue : undefined,
      },
    });
  };

  const filteredIssues = (summary?.issues || []).filter((iss) => {
    if (severityFilter && iss.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 font-sans">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">
            Data Quality & Validation Audit
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Automated schema constraints, relational integrity verification, and exception resolution
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
                {d.name} ({d.quality_score}% Quality)
              </option>
            ))}
          </select>
        </div>
      </div>

      {summary && (
        <>
          {/* Quality Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
              <div className="text-xs text-zinc-400 font-medium">Quality Score</div>
              <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
                {summary.quality_score}%
              </div>
              <div className="text-[11px] text-zinc-500 mt-1 font-mono">
                {summary.valid_records} / {summary.total_records} valid records
              </div>
            </div>

            <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
              <div className="text-xs text-rose-400 flex items-center space-x-1.5 font-medium">
                <XCircle className="w-3.5 h-3.5" />
                <span>Errors</span>
              </div>
              <div className="text-2xl font-bold text-rose-400 font-mono mt-1">
                {summary.issues_by_severity.error || 0}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">Requires manual correction</div>
            </div>

            <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
              <div className="text-xs text-amber-400 flex items-center space-x-1.5 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Warnings</span>
              </div>
              <div className="text-2xl font-bold text-amber-400 font-mono mt-1">
                {summary.issues_by_severity.warning || 0}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">Possible formatting anomalies</div>
            </div>

            <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
              <div className="text-xs text-emerald-400 flex items-center space-x-1.5 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Resolved</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
                {summary.issues.filter((i) => i.is_resolved).length}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">Audited exceptions</div>
            </div>
          </div>

          {/* Issues Filter & Table */}
          <div className="bg-[#121215] border border-zinc-800 rounded-xl overflow-hidden shadow-sm text-xs">
            <div className="p-3 bg-zinc-900/60 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-zinc-200">Validation Issues</span>
                <span className="text-zinc-500 font-mono">({filteredIssues.length} total)</span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setSeverityFilter('')}
                  className={`px-3 py-1 rounded-md text-[11px] font-medium transition-colors ${
                    severityFilter === '' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSeverityFilter('error')}
                  className={`px-3 py-1 rounded-md text-[11px] font-medium transition-colors ${
                    severityFilter === 'error' ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Errors
                </button>
                <button
                  onClick={() => setSeverityFilter('warning')}
                  className={`px-3 py-1 rounded-md text-[11px] font-medium transition-colors ${
                    severityFilter === 'warning' ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Warnings
                </button>
              </div>
            </div>

            <div className="overflow-x-auto max-h-[55vh]">
              <table className="w-full text-left border-collapse">
                <thead className="bg-zinc-900/80 border-b border-zinc-800 text-zinc-400 text-[11px]">
                  <tr>
                    <th className="p-3">Row #</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Field</th>
                    <th className="p-3">Rule Name</th>
                    <th className="p-3">Message</th>
                    <th className="p-3">Current Value</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                  {filteredIssues.map((iss) => (
                    <tr
                      key={iss.id}
                      className={`hover:bg-zinc-900/40 transition-colors ${
                        iss.is_resolved ? 'opacity-50' : ''
                      }`}
                    >
                      <td className="p-3 font-mono font-medium text-zinc-400">{iss.row_index ?? '-'}</td>
                      <td className="p-3">
                        <Badge
                          variant={
                            iss.severity === 'error'
                              ? 'danger'
                              : iss.severity === 'warning'
                              ? 'warning'
                              : 'navy'
                          }
                        >
                          {iss.severity.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3 text-zinc-200 font-mono font-medium">{iss.column_name || 'N/A'}</td>
                      <td className="p-3 text-zinc-400">{iss.rule_name}</td>
                      <td className="p-3 text-zinc-300 max-w-sm leading-relaxed">{iss.message}</td>
                      <td className="p-3 max-w-xs truncate text-amber-300/90 font-mono">
                        {iss.raw_value || <span className="italic text-zinc-600">empty</span>}
                      </td>
                      <td className="p-3">
                        {iss.is_resolved ? (
                          <span className="text-emerald-400 font-medium font-mono">Resolved</span>
                        ) : (
                          <span className="text-rose-400 font-mono">Open</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        {!iss.is_resolved ? (
                          <button
                            onClick={() => {
                              setResolvingIssue(iss);
                              setCorrectedValue(iss.raw_value || '');
                              setResolutionComment('');
                            }}
                            className="px-2.5 py-1 bg-emerald-950/70 hover:bg-emerald-900/70 text-emerald-400 border border-emerald-800/60 rounded text-[11px] font-semibold transition-colors"
                          >
                            Resolve & Fix
                          </button>
                        ) : (
                          <span className="text-[11px] text-zinc-500 font-mono">
                            {iss.resolved_by || 'Audited'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filteredIssues.length === 0 && (
              <div className="p-10 text-center text-zinc-500">
                No validation issues found for the selected filter.
              </div>
            )}
          </div>
        </>
      )}

      {/* Resolve Issue Modal */}
      {resolvingIssue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-[#121215] border border-zinc-800 rounded-xl shadow-2xl p-6">
            <h3 className="text-sm font-bold text-zinc-100 font-sans">
              Resolve Exception: {resolvingIssue.rule_name}
            </h3>
            <p className="text-xs text-zinc-400 font-mono mt-1">
              Field: <span className="text-amber-300">{resolvingIssue.column_name}</span> (Row #{resolvingIssue.row_index})
            </p>

            <form onSubmit={handleResolveSubmit} className="mt-4 space-y-4 text-xs font-sans">
              <div>
                <label className="block text-zinc-300 mb-1 font-medium">
                  Corrected Value (Will update dataset record)
                </label>
                <input
                  type="text"
                  value={correctedValue}
                  onChange={(e) => setCorrectedValue(e.target.value)}
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-zinc-300 mb-1 font-medium">
                  Resolution Rationale / Note
                </label>
                <textarea
                  rows={2}
                  required
                  value={resolutionComment}
                  onChange={(e) => setResolutionComment(e.target.value)}
                  placeholder="e.g. Corrected typo against DHET registration gazette..."
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-zinc-200 focus:outline-none focus:border-emerald-500 font-sans"
                />
              </div>

              <div className="pt-3 border-t border-zinc-800 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setResolvingIssue(null)}
                  className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resolveMutation.isPending}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm transition-colors"
                >
                  Apply Fix & Audit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

