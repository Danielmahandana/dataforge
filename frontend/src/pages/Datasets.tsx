import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Database,
  ArrowRight,
  Trash2,
  Download,
  ShieldCheck,
  FileSpreadsheet,
  Table,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';

export const Datasets: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteDataset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight font-sans">
            Structured Datasets
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Normalized, schema-validated database tables compiled from unstructured documents
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {datasets.map((dataset) => {
          const score = dataset.quality_score;
          const scoreVariant =
            score >= 90 ? 'success' : score >= 75 ? 'warning' : 'danger';

          return (
            <div
              key={dataset.id}
              className="flex flex-col justify-between p-5 bg-[#121215] border border-zinc-800 hover:border-zinc-700 rounded-xl transition-all"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2.5">
                    <Table className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <h2 className="text-sm font-semibold text-zinc-100 line-clamp-1">
                      {dataset.name}
                    </h2>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Delete dataset "${dataset.name}" and all records?`)) {
                        deleteMutation.mutate(dataset.id);
                      }
                    }}
                    className="p-1 text-zinc-400 hover:text-rose-400 rounded transition-colors"
                    title="Delete dataset"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <p className="text-xs text-zinc-400 mt-2 line-clamp-2 min-h-[2.5rem] leading-relaxed">
                  {dataset.description || 'Normalized structured dataset.'}
                </p>

                {/* Badges */}
                <div className="flex items-center space-x-2 mt-4">
                  <Badge variant="gold">{dataset.schema_name}</Badge>
                  <Badge variant={scoreVariant}>{score}% Quality</Badge>
                  <span className="text-[11px] text-zinc-500 capitalize font-mono">
                    {dataset.status}
                  </span>
                </div>
              </div>

              {/* Stats & Link */}
              <div className="mt-5 pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2 text-zinc-400">
                  <span className="text-zinc-200 font-bold font-mono">
                    {dataset.record_count.toLocaleString()}
                  </span>
                  <span>records</span>
                </div>

                <Link
                  to={`/datasets/${dataset.id}`}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-400 border border-emerald-800/50 rounded-lg text-xs font-medium transition-colors"
                >
                  <span>Inspect Data</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {datasets.length === 0 && !isLoading && (
        <div className="p-12 text-center bg-[#121215] border border-dashed border-zinc-800 rounded-xl">
          <Database className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-zinc-300 font-sans">No Datasets Available</h3>
          <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
            Run an extraction pipeline on your uploaded PDF documents to generate validated datasets.
          </p>
          <Link
            to="/pipeline"
            className="inline-block mt-4 px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-500 text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            Launch Extraction Pipeline
          </Link>
        </div>
      )}
    </div>
  );
};

