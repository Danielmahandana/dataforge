import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Download,
  FileSpreadsheet,
  FileCode,
  FileText,
  Database,
  CheckCircle2,
  ExternalLink,
  PackageCheck,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ExportResponse } from '../types';

export const Exports: React.FC = () => {
  const location = useLocation();
  const { selectedProjectId } = useAppStore();

  const defaultDsId = location.state?.defaultDatasetId;

  const [activeDatasetId, setActiveDatasetId] = useState<string>(defaultDsId || '');
  const [format, setFormat] = useState<string>('csv');
  const [includeProvenance, setIncludeProvenance] = useState<boolean>(true);
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

  const exportMutation = useMutation({
    mutationFn: () =>
      apiClient.exportDataset(activeDatasetId, {
        format,
        include_provenance: includeProvenance,
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

  return (
    <div className="space-y-6 font-sans">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">
          Dataset Exporter
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Generate production-ready machine-readable datasets in CSV, JSON, and Excel formats
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Export Configuration Form */}
        <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-4 text-xs">
          <div className="flex items-center space-x-2 text-emerald-400 pb-3 border-b border-zinc-800 font-semibold uppercase text-[11px] tracking-wider font-mono">
            <Download className="w-4 h-4" />
            <span>Export Configuration</span>
          </div>

          <div>
            <label className="block text-zinc-300 mb-1 font-medium">Select Dataset *</label>
            <select
              value={activeDatasetId}
              onChange={(e) => setActiveDatasetId(e.target.value)}
              className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.record_count} records)
                </option>
              ))}
            </select>
          </div>

          {/* Format Selection Cards */}
          <div>
            <label className="block text-zinc-300 mb-2 font-medium">Target File Format *</label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setFormat('csv')}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-2 transition-all ${
                  format === 'csv'
                    ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400 font-bold'
                    : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <FileText className="w-6 h-6" />
                <span>CSV</span>
              </button>

              <button
                type="button"
                onClick={() => setFormat('xlsx')}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-2 transition-all ${
                  format === 'xlsx'
                    ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400 font-bold'
                    : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <FileSpreadsheet className="w-6 h-6" />
                <span>Excel (.xlsx)</span>
              </button>

              <button
                type="button"
                onClick={() => setFormat('json')}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-2 transition-all ${
                  format === 'json'
                    ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400 font-bold'
                    : 'border-zinc-800 bg-[#09090b] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <FileCode className="w-6 h-6" />
                <span>JSON</span>
              </button>
            </div>
          </div>

          {/* Options Checkboxes */}
          <div className="space-y-2.5 pt-3 border-t border-zinc-800">
            <label className="flex items-center space-x-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={includeProvenance}
                onChange={(e) => setIncludeProvenance(e.target.checked)}
                className="rounded bg-[#09090b] border-zinc-700 text-emerald-500 focus:ring-0"
              />
              <span className="text-zinc-300">
                Include Provenance Columns (_prov_doc, _prov_page, _prov_confidence)
              </span>
            </label>

            <label className="flex items-center space-x-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyValidRecords}
                onChange={(e) => setOnlyValidRecords(e.target.checked)}
                className="rounded bg-[#09090b] border-zinc-700 text-emerald-500 focus:ring-0"
              />
              <span className="text-zinc-300">
                Filter: Only export validated / reviewed records
              </span>
            </label>
          </div>

          <button
            onClick={() => exportMutation.mutate()}
            disabled={!activeDatasetId || exportMutation.isPending}
            className="w-full flex items-center justify-center space-x-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 font-semibold rounded-lg shadow-sm transition-colors mt-2"
          >
            <Download className="w-4 h-4" />
            <span>{exportMutation.isPending ? 'Generating File...' : 'Generate & Download Export'}</span>
          </button>
        </div>

        {/* Export Result Preview */}
        <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-4 text-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 text-zinc-200 pb-3 border-b border-zinc-800 font-semibold uppercase text-[11px] tracking-wider font-mono">
              <PackageCheck className="w-4 h-4 text-emerald-400" />
              <span>Export Summary & Package</span>
            </div>

            {lastExport ? (
              <div className="mt-4 p-4 bg-[#09090b] border border-emerald-800/60 rounded-xl space-y-3 font-mono">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>Export Package Ready</span>
                </div>

                <div className="space-y-1.5 text-zinc-300 text-[11px]">
                  <div>File: <span className="font-bold text-zinc-100">{lastExport.filename}</span></div>
                  <div>Format: <span className="uppercase text-emerald-400">{lastExport.format}</span></div>
                  <div>Records: <span>{lastExport.record_count.toLocaleString()}</span></div>
                  <div>Size: <span>{(lastExport.file_size_bytes / 1024).toFixed(1)} KB</span></div>
                </div>

                <a
                  href={lastExport.download_url}
                  download={lastExport.filename}
                  className="mt-4 inline-flex items-center justify-center space-x-2 w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm transition-colors font-sans"
                >
                  <Download className="w-4 h-4" />
                  <span>Download {lastExport.filename}</span>
                </a>
              </div>
            ) : (
              <div className="py-16 text-center text-zinc-500 font-sans">
                Configure your export settings and click "Generate & Download Export" to build your dataset file.
              </div>
            )}
          </div>

          {activeDataset && (
            <div className="p-3 bg-[#09090b] border border-zinc-800 rounded-lg text-zinc-400 text-[11px] font-mono leading-relaxed">
              <div>Target Schema: <span className="text-zinc-200 font-semibold">{activeDataset.schema_name}</span></div>
              <div>Columns: <span className="text-zinc-200 font-semibold">{activeDataset.schema_columns.length}</span></div>
              <div>Available Rows: <span className="text-zinc-200 font-semibold">{activeDataset.record_count}</span></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

