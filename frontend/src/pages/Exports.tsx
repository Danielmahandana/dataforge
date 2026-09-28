import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Download,
  FileSpreadsheet,
  FileCode,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  PackageCheck,
  ShieldCheck,
  Sparkles,
  Sliders,
  Layers,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ExportResponse, QualityGates } from '../types';

type ExportPreset = 'clean_production' | 'research_curated' | 'full_audit' | 'custom';

export const Exports: React.FC = () => {
  const location = useLocation();
  const { selectedProjectId } = useAppStore();

  const defaultDsId = location.state?.defaultDatasetId;

  const [activeDatasetId, setActiveDatasetId] = useState<string>(defaultDsId || '');
  const [preset, setPreset] = useState<ExportPreset>('research_curated');
  const [format, setFormat] = useState<string>('csv');
  const [includeProvenance, setIncludeProvenance] = useState<boolean>(true);
  const [includeCuration, setIncludeCuration] = useState<boolean>(true);
  const [curationFilter, setCurationFilter] = useState<string>('INCLUDE');
  const [onlyValidRecords, setOnlyValidRecords] = useState<boolean>(false);
  const [lastExport, setLastExport] = useState<ExportResponse | null>(null);

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  // Fetch quality gates for the active dataset
  const { data: qualityGates, isLoading: isLoadingGates } = useQuery<QualityGates>({
    queryKey: ['qualityGates', activeDatasetId],
    queryFn: () => apiClient.getQualityGates(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  // Handle Preset Switching
  const handlePresetSelect = (selected: ExportPreset) => {
    setPreset(selected);
    if (selected === 'clean_production') {
      setIncludeProvenance(false);
      setIncludeCuration(false);
      setCurationFilter('INCLUDE');
      setOnlyValidRecords(true);
    } else if (selected === 'research_curated') {
      setIncludeProvenance(true);
      setIncludeCuration(true);
      setCurationFilter('INCLUDE');
      setOnlyValidRecords(false);
    } else if (selected === 'full_audit') {
      setIncludeProvenance(true);
      setIncludeCuration(true);
      setCurationFilter('ALL');
      setOnlyValidRecords(false);
    }
  };

  const exportMutation = useMutation({
    mutationFn: () =>
      apiClient.exportDataset(activeDatasetId, {
        format,
        include_provenance: includeProvenance,
        include_curation: includeCuration,
        curation_filter: curationFilter === 'ALL' ? null : curationFilter,
        only_valid_records: onlyValidRecords,
      }),
    onSuccess: (data) => {
      setLastExport(data);
    },
    onError: (err: any) => {
      alert('Export failed: ' + (err.response?.data?.detail || err.message));
    },
  });

  const activeDataset = datasets.find((d) => d.id === activeDatasetId);

  const renderGateBadge = () => {
    if (!qualityGates) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700">
          Ungated / Uncurated
        </span>
      );
    }
    if (qualityGates.can_export_clean) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
          Gates Passed: Publication Ready
        </span>
      );
    }
    if (qualityGates.can_export_research) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="w-3.5 h-3.5 mr-1" />
          Review Required Before Publication
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <XCircle className="w-3.5 h-3.5 mr-1" />
        Quality Gates Blocked
      </span>
    );
  };

  return (
    <div className="space-y-6 font-sans">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100 tracking-tight flex items-center space-x-2">
          <Download className="w-6 h-6 text-emerald-400" />
          <span>Research Data & Export Workstation</span>
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Export verified research artifacts with configurable provenance, semantic curation claims, and quality gate assurance.
        </p>
      </div>

      {/* Dataset Selection & Quality Gates Status Bar */}
      <div className="bg-[#121215] border border-zinc-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1 max-w-md">
          <label className="block text-zinc-400 text-xs font-semibold uppercase tracking-wider mb-1 font-mono">
            Target Dataset
          </label>
          <select
            value={activeDatasetId}
            onChange={(e) => setActiveDatasetId(e.target.value)}
            className="w-full px-3 py-2 bg-[#09090b] border border-zinc-700 rounded-lg text-zinc-200 text-sm focus:outline-none focus:border-emerald-500 font-mono"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.record_count} records) {d.version_label ? `— ${d.version_label}` : ''}
              </option>
            ))}
          </select>
        </div>

        {activeDataset && (
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <div className="text-[11px] text-zinc-400 uppercase font-mono mb-1">Quality Gate Posture</div>
              {isLoadingGates ? (
                <span className="text-xs text-zinc-500">Evaluating quality gates...</span>
              ) : (
                renderGateBadge()
              )}
            </div>

            {qualityGates && (
              <div className="pl-4 border-l border-zinc-800 hidden lg:block font-mono">
                <div className="text-[11px] text-zinc-400 uppercase mb-1">Score</div>
                <div className="text-base font-bold text-emerald-400">
                  {Math.round(qualityGates.overall_score || qualityGates.dimensions?.overall || 0)}%
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Preset Selection & Configuration Form (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Preset Cards */}
          <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center space-x-2 text-zinc-200 text-xs font-semibold uppercase tracking-wider font-mono">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>1. Choose Delivery Preset</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <button
                type="button"
                onClick={() => handlePresetSelect('clean_production')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  preset === 'clean_production'
                    ? 'border-emerald-500 bg-emerald-950/20 text-zinc-100 shadow-sm'
                    : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center space-x-2 font-bold mb-1">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Clean Production</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Only validated, INCLUDED records. Standard column schema with no internal audit metadata.
                </p>
              </button>

              <button
                type="button"
                onClick={() => handlePresetSelect('research_curated')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  preset === 'research_curated'
                    ? 'border-indigo-500 bg-indigo-950/20 text-zinc-100 shadow-sm'
                    : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center space-x-2 font-bold mb-1">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  <span>Curated Research</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Curated subset with multi-confidence metrics, derived chamber mappings, and source provenance.
                </p>
              </button>

              <button
                type="button"
                onClick={() => handlePresetSelect('full_audit')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  preset === 'full_audit'
                    ? 'border-amber-500 bg-amber-950/20 text-zinc-100 shadow-sm'
                    : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center space-x-2 font-bold mb-1">
                  <Sliders className="w-4 h-4 text-amber-400" />
                  <span>Full Audit Package</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Complete dataset including EXCLUDED & REVIEW records, decision reasons, and lineage links.
                </p>
              </button>
            </div>
          </div>

          {/* Granular Parameters Form */}
          <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-5 text-xs">
            <div className="flex items-center space-x-2 text-zinc-200 text-xs font-semibold uppercase tracking-wider font-mono pb-3 border-b border-zinc-800">
              <Download className="w-4 h-4 text-emerald-400" />
              <span>2. File Format & Pipeline Filters</span>
            </div>

            {/* Target File Format */}
            <div>
              <label className="block text-zinc-300 mb-2 font-medium">Target File Format *</label>
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setFormat('csv')}
                  className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-1.5 transition-all ${
                    format === 'csv'
                      ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400 font-bold'
                      : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                  }`}
                >
                  <FileText className="w-5 h-5" />
                  <span>CSV</span>
                </button>

                <button
                  type="button"
                  onClick={() => setFormat('xlsx')}
                  className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-1.5 transition-all ${
                    format === 'xlsx'
                      ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400 font-bold'
                      : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                  }`}
                >
                  <FileSpreadsheet className="w-5 h-5" />
                  <span>Excel (.xlsx)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setFormat('json')}
                  className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-1.5 transition-all ${
                    format === 'json'
                      ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400 font-bold'
                      : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                  }`}
                >
                  <FileCode className="w-5 h-5" />
                  <span>JSON</span>
                </button>
              </div>
            </div>

            {/* Curation Filter & Validation Filter */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-zinc-300 mb-1 font-medium">Curation Decision Filter</label>
                <select
                  value={curationFilter}
                  onChange={(e) => {
                    setCurationFilter(e.target.value);
                    setPreset('custom');
                  }}
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                >
                  <option value="ALL">All Records (No Curation Filter)</option>
                  <option value="INCLUDE">INCLUDE Records Only (Curated Valid)</option>
                  <option value="REVIEW">REVIEW Records Only (Needs Attention)</option>
                  <option value="EXCLUDE">EXCLUDE Records Only (Out of Scope)</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-300 mb-1 font-medium">Record Validation Filter</label>
                <select
                  value={onlyValidRecords ? 'valid_only' : 'all_validation'}
                  onChange={(e) => {
                    setOnlyValidRecords(e.target.value === 'valid_only');
                    setPreset('custom');
                  }}
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                >
                  <option value="all_validation">All Extraction States</option>
                  <option value="valid_only">Validated & Reviewed Records Only</option>
                </select>
              </div>
            </div>

            {/* Metadata Checkboxes */}
            <div className="space-y-3 pt-3 border-t border-zinc-800">
              <label className="flex items-center space-x-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeProvenance}
                  onChange={(e) => {
                    setIncludeProvenance(e.target.checked);
                    setPreset('custom');
                  }}
                  className="rounded bg-[#09090b] border-zinc-700 text-emerald-500 focus:ring-0"
                />
                <span className="text-zinc-300 font-medium">
                  Append Provenance Columns <span className="font-mono text-[11px] text-zinc-500">(_prov_doc, _prov_page, _prov_confidence)</span>
                </span>
              </label>

              <label className="flex items-center space-x-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeCuration}
                  onChange={(e) => {
                    setIncludeCuration(e.target.checked);
                    setPreset('custom');
                  }}
                  className="rounded bg-[#09090b] border-zinc-700 text-emerald-500 focus:ring-0"
                />
                <span className="text-zinc-300 font-medium">
                  Append Semantic Curation Governance Columns <span className="font-mono text-[11px] text-zinc-500">(_curation_decision, _curation_reason, _curation_confidence, _derived_chambers)</span>
                </span>
              </label>
            </div>

            <button
              onClick={() => exportMutation.mutate()}
              disabled={!activeDatasetId || exportMutation.isPending}
              className="w-full flex items-center justify-center space-x-2 py-3 bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 font-semibold rounded-lg shadow-sm transition-colors mt-4 text-sm"
            >
              <Download className="w-4 h-4" />
              <span>{exportMutation.isPending ? 'Generating Research Artifact...' : 'Generate & Download Export Package'}</span>
            </button>
          </div>
        </div>

        {/* Right Column: Export Package Output & Quality Checks (1 col) */}
        <div className="space-y-6">
          <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-4 text-xs">
            <div className="flex items-center space-x-2 text-zinc-200 pb-3 border-b border-zinc-800 font-semibold uppercase text-[11px] tracking-wider font-mono">
              <PackageCheck className="w-4 h-4 text-emerald-400" />
              <span>Export Package Manifest</span>
            </div>

            {lastExport ? (
              <div className="p-4 bg-[#09090b] border border-emerald-800/60 rounded-xl space-y-3 font-mono">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>Export Package Ready</span>
                </div>

                <div className="space-y-2 text-zinc-300 text-[11px] pt-1">
                  <div>File: <span className="font-bold text-zinc-100">{lastExport.filename}</span></div>
                  <div>Format: <span className="uppercase text-emerald-400 font-semibold">{lastExport.format}</span></div>
                  <div>Records: <span className="text-zinc-100">{lastExport.record_count.toLocaleString()}</span></div>
                  <div>Size: <span className="text-zinc-100">{(lastExport.file_size_bytes / 1024).toFixed(1)} KB</span></div>
                </div>

                <a
                  href={lastExport.download_url}
                  download={lastExport.filename}
                  className="mt-4 inline-flex items-center justify-center space-x-2 w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm transition-colors font-sans"
                >
                  <Download className="w-4 h-4" />
                  <span>Download File</span>
                </a>
              </div>
            ) : (
              <div className="py-12 text-center text-zinc-500 font-sans space-y-2">
                <Download className="w-8 h-8 text-zinc-600 mx-auto" />
                <p>Select your delivery preset and click "Generate & Download" to create your research export file.</p>
              </div>
            )}
          </div>

          {/* Dataset Specifications Card */}
          {activeDataset && (
            <div className="bg-[#121215] border border-zinc-800 rounded-xl p-4 text-xs font-mono space-y-3">
              <div className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider">
                Dataset Specifications
              </div>
              <div className="space-y-1.5 text-zinc-400 text-[11px]">
                <div>Name: <span className="text-zinc-200">{activeDataset.name}</span></div>
                <div>Schema: <span className="text-zinc-200">{activeDataset.schema_name}</span></div>
                <div>Version: <span className="text-zinc-200">{activeDataset.version_label || 'v1.0.0'}</span></div>
                <div>Total Records: <span className="text-zinc-200">{activeDataset.record_count}</span></div>
                <div>Columns: <span className="text-zinc-200">{activeDataset.schema_columns.length}</span></div>
              </div>

              {activeDataset.curation_summary && (
                <div className="pt-2 border-t border-zinc-800">
                  <div className="text-[10px] text-zinc-500 uppercase mb-1">Curation Distribution</div>
                  <div className="flex items-center space-x-2 text-[11px]">
                    <span className="text-emerald-400 font-semibold">{activeDataset.curation_summary.included || 0} INC</span>
                    <span className="text-zinc-600">•</span>
                    <span className="text-amber-400 font-semibold">{activeDataset.curation_summary.review_required || 0} REV</span>
                    <span className="text-zinc-600">•</span>
                    <span className="text-rose-400 font-semibold">{activeDataset.curation_summary.excluded || 0} EXC</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
