import React from 'react';
import { X, ShieldCheck, FileText, GitBranch, CheckCircle2, AlertTriangle, Layers, Building2, UserCheck } from 'lucide-react';
import { EvidenceItem } from '../../types';

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  recordTitle: string;
  evidenceItems: EvidenceItem[];
  curationDecision?: string;
  confidence?: number;
  onViewSource?: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({
  isOpen,
  onClose,
  recordTitle,
  evidenceItems,
  curationDecision,
  confidence,
  onViewSource,
}) => {
  if (!isOpen) return null;

  const getDecisionBadge = () => {
    switch (curationDecision) {
      case 'INCLUDE':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">INCLUDE</span>;
      case 'EXCLUDE':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-red-500/20 text-red-400 border border-red-500/30">EXCLUDE</span>;
      case 'REVIEW':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">REVIEW REQUIRED</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-500/20 text-slate-400 border border-slate-500/30">UNPROCESSED</span>;
    }
  };

  const getEvidenceIcon = (type: string) => {
    switch (type) {
      case 'source_text':
        return <FileText className="w-4 h-4 text-sky-400" />;
      case 'classification_hierarchy':
        return <GitBranch className="w-4 h-4 text-purple-400" />;
      case 'rule_assertion':
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case 'sector_match':
        return <Building2 className="w-4 h-4 text-amber-400" />;
      case 'human_verified':
        return <UserCheck className="w-4 h-4 text-indigo-400" />;
      default:
        return <Layers className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0B1020]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-white">Record Evidence Explorer</h3>
                {getDecisionBadge()}
                {confidence !== undefined && (
                  <span className="text-xs text-slate-400 font-mono">
                    ({Math.round(confidence * 100)}% conf)
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 truncate max-w-md mt-0.5">{recordTitle}</p>
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
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {evidenceItems.length === 0 ? (
            <div className="text-center py-10 text-slate-400">
              <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2 opacity-60" />
              <p className="text-sm">No structured evidence items recorded for this record yet.</p>
              <p className="text-xs text-slate-500 mt-1">Run a Semantic Curation job to generate evidence claims.</p>
            </div>
          ) : (
            evidenceItems.map((item, idx) => (
              <div
                key={item.id || idx}
                className="p-4 rounded-lg border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded bg-slate-800 border border-slate-700">
                      {getEvidenceIcon(item.evidence_type)}
                    </div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                      {item.evidence_type.replace('_', ' ')}
                    </span>
                    {item.rule_id && (
                      <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {item.rule_id}
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-mono font-medium text-emerald-400">
                    {Math.round(item.confidence * 100)}% weight
                  </span>
                </div>

                <p className="text-sm text-slate-200 mt-2.5 font-medium leading-relaxed">
                  {item.claim}
                </p>

                {item.source_text && (
                  <div className="mt-2.5 p-2 rounded bg-black/40 border border-slate-800 text-xs text-slate-400 font-mono">
                    <span className="text-slate-500 mr-2">[Source Text]:</span>
                    "{item.source_text}"
                  </div>
                )}

                {(item.document_name || item.page_number) && (
                  <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/80">
                    <span>
                      {item.document_name} • Page {item.page_number || 1}
                    </span>
                    {onViewSource && item.page_number && (
                      <button
                        onClick={onViewSource}
                        className="text-xs text-sky-400 hover:text-sky-300 underline font-medium"
                      >
                        [ View Page {item.page_number} in Source PDF ]
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800 bg-[#0B1020]">
          <span className="text-xs text-slate-400">
            {evidenceItems.length} verifiable evidence item(s) logged
          </span>
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
