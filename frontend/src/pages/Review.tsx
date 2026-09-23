import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { History, Database, UserCheck, ArrowRight, ShieldAlert } from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';

export const Review: React.FC = () => {
  const { selectedProjectId } = useAppStore();
  const [activeDatasetId, setActiveDatasetId] = useState<string>('');

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  const { data: reviews = [], isLoading } = useQuery({
    queryKey: ['reviews', activeDatasetId],
    queryFn: () => apiClient.getDatasetReviews(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  return (
    <div className="space-y-6 font-sans">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">
            Human-in-the-Loop Audit Trail
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Immutable trace of all data engineer overrides, validation resolutions, and record corrections
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

      {/* Review Log Table */}
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
                        rev.action.includes('approve')
                          ? 'success'
                          : rev.action.includes('reject')
                          ? 'danger'
                          : rev.action.includes('flag')
                          ? 'warning'
                          : 'gold'
                      }
                    >
                      {rev.action.replace('_', ' ').toUpperCase()}
                    </Badge>
                  </td>
                  <td className="p-3 text-zinc-400 text-[11px] font-mono">
                    #{rev.record_id.slice(0, 8)}
                  </td>
                  <td className="p-3 font-semibold text-zinc-200 font-mono">
                    {rev.field_name || '-'}
                  </td>
                  <td className="p-3 max-w-xs">
                    {rev.field_name ? (
                      <div className="flex items-center space-x-1.5 text-[11px]">
                        <span className="text-rose-400 font-mono line-through truncate max-w-[100px]">
                          {rev.old_value || 'empty'}
                        </span>
                        <ArrowRight className="w-3 h-3 text-zinc-500 flex-shrink-0" />
                        <span className="text-emerald-400 font-mono font-medium truncate max-w-[100px]">
                          {rev.new_value}
                        </span>
                      </div>
                    ) : (
                      <span className="text-zinc-500 text-[11px] font-mono">-</span>
                    )}
                  </td>
                  <td className="p-3 text-zinc-300 max-w-sm leading-relaxed">
                    {rev.reason || 'Manual review verified'}
                  </td>
                  <td className="p-3 text-emerald-400 font-medium font-mono">
                    {rev.reviewed_by}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {reviews.length === 0 && !isLoading && (
          <div className="p-12 text-center text-zinc-500 font-mono text-xs">
            No manual review modifications logged yet for this dataset.
          </div>
        )}
      </div>
    </div>
  );
};

