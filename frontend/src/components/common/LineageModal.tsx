import React from 'react';
import { X, Network, FileCode, CheckCircle2, Clock, ShieldCheck, History, ArrowRight } from 'lucide-react';
import { LineageGraph } from '../../types';

interface LineageModalProps {
  isOpen: boolean;
  onClose: () => void;
  recordTitle: string;
  lineage: LineageGraph | null;
  onViewSource?: (docId: string, pageNum: number) => void;
}

export const LineageModal: React.FC<LineageModalProps> = ({
  isOpen,
  onClose,
  recordTitle,
  lineage,
  onViewSource,
}) => {
  if (!isOpen || !lineage) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0B1020]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Full Provenance & Traceability Lineage</h3>
              <p className="text-xs text-slate-400 truncate max-w-lg mt-0.5">{recordTitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Source Document Badge */}
          <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-sky-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Originating Source Document
                </span>
              </div>
              <p className="text-sm font-medium text-white mt-1">
                {lineage.source_document.document_name || 'Source PDF'}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                <span className="font-mono text-[11px] bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                  SHA-256: {lineage.source_document.sha256_hash ? lineage.source_document.sha256_hash.slice(0, 16) + '...' : 'Verified'}
                </span>
                <span>Page: {lineage.source_document.page_number || 1}</span>
                <span>Method: {lineage.source_document.extraction_method || 'Table Extractor'}</span>
              </div>
            </div>
            {onViewSource && lineage.source_document.document_id && (
              <button
                onClick={() => onViewSource(lineage.source_document.document_id!, lineage.source_document.page_number || 1)}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-sky-600/20 text-sky-300 hover:bg-sky-600/30 border border-sky-500/40 transition-colors"
              >
                [ Jump to Page {lineage.source_document.page_number || 1} ]
              </button>
            )}
          </div>

          {/* Stepper Timeline */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Transformation Pipeline Stages
            </h4>
            <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
              {lineage.steps.map((step, idx) => (
                <div key={idx} className="relative flex items-start gap-4 pl-8">
                  <div className="absolute left-1.5 -translate-x-1/2 top-1.5 w-4 h-4 rounded-full bg-slate-800 border-2 border-sky-400 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                  </div>
                  <div className="flex-1 p-3.5 rounded-lg bg-slate-900/50 border border-slate-800">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-sky-300 uppercase tracking-wide">
                        {step.stage} • {step.title}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">{step.actor}</span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">{step.description}</p>
                    {step.data_snapshot && Object.keys(step.data_snapshot).length > 0 && (
                      <div className="mt-2 p-2 rounded bg-black/40 border border-slate-800 text-[11px] font-mono text-slate-400 max-h-24 overflow-y-auto">
                        {JSON.stringify(step.data_snapshot, null, 2)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Decision Ledger Audit Trail */}
          {lineage.ledger && lineage.ledger.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <History className="w-4 h-4 text-amber-400" />
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Decision Ledger (Audit History)
                </h4>
              </div>
              <div className="border border-slate-800 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0B1020] text-slate-400 font-semibold border-b border-slate-800">
                    <tr>
                      <th className="px-3 py-2">Stage</th>
                      <th className="px-3 py-2">Field</th>
                      <th className="px-3 py-2">Previous</th>
                      <th className="px-3 py-2">New</th>
                      <th className="px-3 py-2">Actor</th>
                      <th className="px-3 py-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 bg-slate-900/40 text-slate-300">
                    {lineage.ledger.map((entry) => (
                      <tr key={entry.id}>
                        <td className="px-3 py-2 font-mono text-[11px] text-sky-400">{entry.stage}</td>
                        <td className="px-3 py-2 font-mono text-[11px]">{entry.field_name || '-'}</td>
                        <td className="px-3 py-2 text-slate-400 truncate max-w-[120px]">{entry.previous_value || 'None'}</td>
                        <td className="px-3 py-2 text-emerald-400 font-medium truncate max-w-[120px]">{entry.new_value || '-'}</td>
                        <td className="px-3 py-2 text-slate-400">{entry.actor_id}</td>
                        <td className="px-3 py-2 text-slate-400 truncate max-w-[160px]">{entry.reason || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-3.5 border-t border-slate-800 bg-[#0B1020]">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
