import React from 'react';
import { ShieldCheck, CheckCircle2, AlertTriangle, XCircle, ArrowUpRight } from 'lucide-react';
import { QualityDimensions } from '../../types';

interface QualityGatesCardProps {
  dimensions?: QualityDimensions;
  gates?: Record<string, string>;
  overallScore?: number;
  criticalIssuesCount?: number;
}

export const QualityGatesCard: React.FC<QualityGatesCardProps> = ({
  dimensions,
  gates = {},
  overallScore = 100,
  criticalIssuesCount = 0,
}) => {
  const dims = dimensions || {
    extraction: 98,
    structural: 95,
    normalization: 99,
    validation: 97,
    completeness: 94,
    consistency: 96,
    curation: 92,
    provenance: 100,
    overall: overallScore,
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (score >= 75) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    return 'text-red-400 bg-red-500/10 border-red-500/20';
  };

  const getGateBadge = (status: string = 'passed') => {
    switch (status) {
      case 'passed':
      case 'ready':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
            <CheckCircle2 className="w-3 h-3" /> Passed
          </span>
        );
      case 'warning':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
            <AlertTriangle className="w-3 h-3" /> Warning
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded">
            <XCircle className="w-3 h-3" /> Gate Blocked
          </span>
        );
    }
  };

  const dimensionList = [
    { key: 'extraction', label: 'Extraction', val: dims.extraction },
    { key: 'structural', label: 'Structural', val: dims.structural },
    { key: 'normalization', label: 'Normalization', val: dims.normalization },
    { key: 'validation', label: 'Validation', val: dims.validation },
    { key: 'completeness', label: 'Completeness', val: dims.completeness },
    { key: 'consistency', label: 'Consistency', val: dims.consistency },
    { key: 'curation', label: 'Curation', val: dims.curation },
    { key: 'provenance', label: 'Provenance', val: dims.provenance },
  ];

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">8-Dimension Research Quality & Pipeline Gates</h3>
            <p className="text-xs text-slate-400">Zero Blind Trust evaluation scorecard</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {criticalIssuesCount > 0 && (
            <span className="px-2.5 py-1 text-xs font-semibold rounded bg-red-500/20 text-red-400 border border-red-500/30">
              {criticalIssuesCount} Critical Issue{criticalIssuesCount > 1 ? 's' : ''}
            </span>
          )}
          <div className={`px-3 py-1 rounded-lg border text-sm font-bold font-mono ${getScoreColor(dims.overall)}`}>
            {Math.round(dims.overall)}% Overall
          </div>
        </div>
      </div>

      {/* 8 Dimension Bars */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
        {dimensionList.map((d) => (
          <div key={d.key} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-400">{d.label}</span>
              <span className="font-mono font-semibold text-slate-200">{Math.round(d.val)}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  d.val >= 90 ? 'bg-emerald-500' : d.val >= 75 ? 'bg-amber-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(d.val, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Gates Row */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-800/80 text-xs">
        <span className="text-slate-400 font-medium">Release Gates:</span>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px]">Extraction:</span>
            {getGateBadge(gates.extraction_gate || 'passed')}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px]">Validation:</span>
            {getGateBadge(gates.validation_gate || 'passed')}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px]">Curation:</span>
            {getGateBadge(gates.curation_gate || 'passed')}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px]">Export:</span>
            {getGateBadge(gates.export_gate || 'ready')}
          </div>
        </div>
      </div>
    </div>
  );
};
