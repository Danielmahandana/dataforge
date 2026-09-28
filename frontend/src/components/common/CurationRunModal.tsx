import React, { useState, useEffect } from 'react';
import { X, Sparkles, Sliders, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import { apiClient } from '../../services/api';
import { DatasetIntent, CurationPolicy } from '../../types';

interface CurationRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  datasetId: string;
  datasetName: string;
  projectId?: string;
  onRunStarted?: (runId: string) => void;
}

export const CurationRunModal: React.FC<CurationRunModalProps> = ({
  isOpen,
  onClose,
  datasetId,
  datasetName,
  projectId,
  onRunStarted,
}) => {
  const [intents, setIntents] = useState<DatasetIntent[]>([]);
  const [policies, setPolicies] = useState<CurationPolicy[]>([]);
  const [selectedIntentId, setSelectedIntentId] = useState<string>('');
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>('merseta_ofo_relevance');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadOptions();
    }
  }, [isOpen, projectId]);

  const loadOptions = async () => {
    try {
      const [intentsData, policiesData] = await Promise.all([
        apiClient.getIntents(projectId),
        apiClient.getPolicies(),
      ]);
      setIntents(intentsData);
      setPolicies(policiesData);
      if (intentsData.length > 0 && !selectedIntentId) {
        setSelectedIntentId(intentsData[0].id);
      }
    } catch (err: any) {
      setError('Failed to load curation options');
    }
  };

  const handleLaunch = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const run = await apiClient.createCurationRun({
        dataset_id: datasetId,
        intent_id: selectedIntentId || undefined,
        policy_id: selectedPolicyId || 'merseta_ofo_relevance',
      });
      if (onRunStarted) {
        onRunStarted(run.id);
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to trigger curation run');
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0B1020]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Execute Semantic Curation</h3>
              <p className="text-xs text-slate-400 truncate max-w-sm mt-0.5">{datasetName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Curation Policy Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Curation Policy Framework
            </label>
            <select
              value={selectedPolicyId}
              onChange={(e) => setSelectedPolicyId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              {policies.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.is_builtin ? '(Built-in)' : '(Custom)'}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Evaluates inclusion thresholds, chamber alignments, and weighted multi-factor rule evidence.
            </p>
          </div>

          {/* Dataset Intent Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Dataset Intent Objective
            </label>
            <select
              value={selectedIntentId}
              onChange={(e) => setSelectedIntentId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Default (Policy Standard Scope)</option>
              {intents.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Defines explicit research goals, target industrial sectors, and exclusion constraints.
            </p>
          </div>

          {/* Multi-Tier Processing Card */}
          <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs space-y-2">
            <span className="font-semibold text-slate-300">Automated Pipeline Guarantees:</span>
            <ul className="text-slate-400 space-y-1 text-[11px]">
              <li>• Tier 1: Deterministic Domain & Structural Rule Validation</li>
              <li>• Tier 2: OFO & Classification Taxonomy Tree Context Resolution</li>
              <li>• Tier 3: Zero Blind Trust 3-State Decisions (INCLUDE / EXCLUDE / REVIEW)</li>
              <li>• Tier 4: Immutable Decision Ledger and Provenance Tracking</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-[#0B1020]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleLaunch}
            className="flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {isSubmitting ? 'Starting Run...' : 'Launch Curation Engine'}
          </button>
        </div>
      </div>
    </div>
  );
};
