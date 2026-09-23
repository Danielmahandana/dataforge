import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Workflow,
  Play,
  ArrowRight,
  RefreshCw,
  Sliders,
  Sparkles,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ProgressBar } from '../components/common/ProgressBar';

export const Pipeline: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const preselectedDocs: string[] = location.state?.documentIds || [];

  const [projectId, setProjectId] = useState<string>(selectedProjectId || '');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>(preselectedDocs);
  const [pipelineType, setPipelineType] = useState<string>('universal_auto');
  const [datasetName, setDatasetName] = useState<string>('');
  const [pageRange, setPageRange] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => apiClient.getDocuments(projectId || undefined),
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ['extraction-jobs', projectId],
    queryFn: () => apiClient.getJobs(projectId || undefined),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.some((j) => j.status === 'running' || j.status === 'pending')) {
        return 2000;
      }
      return 10000;
    },
  });

  useEffect(() => {
    if (!projectId && projects.length > 0) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const runMutation = useMutation({
    mutationFn: apiClient.createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extraction-jobs'] });
      setIsSubmitting(false);
      setDatasetName('');
      setPageRange('');
    },
    onError: (err: any) => {
      setIsSubmitting(false);
      alert('Failed to start extraction job: ' + (err.response?.data?.detail || err.message));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) {
      alert('Please choose a target project.');
      return;
    }
    if (selectedDocIds.length === 0) {
      alert('Please select at least one document to process.');
      return;
    }

    setIsSubmitting(true);

    const parameters: Record<string, any> = {};
    if (pageRange.trim()) {
      const parsedPages = pageRange
        .split(',')
        .map((p) => parseInt(p.trim(), 10))
        .filter((n) => !isNaN(n) && n > 0);
      if (parsedPages.length > 0) {
        parameters.pages = parsedPages;
      }
    }

    runMutation.mutate({
      project_id: projectId,
      document_ids: selectedDocIds,
      pipeline_type: pipelineType,
      parameters,
      target_dataset_name: datasetName.trim() || undefined,
    });
  };

  const toggleSelectDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
          AI Extraction Studio
        </h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Execute automated document intelligence, Groq AI schema compilation, and relational data extraction.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Configuration Form */}
        <div className="lg:col-span-1 bg-[#121215] border border-zinc-800 rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center space-x-2 text-amber-400 pb-3 border-b border-zinc-800 text-xs font-semibold uppercase tracking-wider">
            <Sliders className="w-4 h-4" />
            <span>Extraction Configuration</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Target Project */}
            <div>
              <label className="block text-xs text-zinc-300 mb-1">
                Target Workspace *
              </label>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
              >
                <option value="">Select Workspace...</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Pipeline Strategy / Blueprint */}
            <div>
              <label className="block text-xs text-zinc-300 mb-1">
                Extraction Blueprint Model *
              </label>
              <select
                value={pipelineType}
                onChange={(e) => setPipelineType(e.target.value)}
                className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
              >
                <option value="universal_auto">✨ AI Auto-Inferred Schema (Groq LLM)</option>
                <option value="qualifications">🎓 TVET Qualifications & College Offerings</option>
                <option value="occupations">💼 OIHD High-Demand Occupations & OFO Codes</option>
                <option value="codebook">📊 Survey Metadata Codebook (StatsSA QLFS)</option>
                <option value="financial">📈 Financial Statements & Balance Sheets</option>
                <option value="pdf_tables">📄 Native Line Grid Detector</option>
              </select>
            </div>

            {/* Custom Dataset Name */}
            <div>
              <label className="block text-xs text-zinc-300 mb-1">
                Target Dataset Name (Optional)
              </label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="Defaults to document name"
                className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
              />
            </div>

            {/* Page Range */}
            <div>
              <label className="block text-xs text-zinc-300 mb-1">
                Page Selection (Optional)
              </label>
              <input
                type="text"
                value={pageRange}
                onChange={(e) => setPageRange(e.target.value)}
                placeholder="e.g. 1, 2, 3 or leave blank for all"
                className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
              />
            </div>

            {/* Select Documents */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-zinc-300">
                  Select Documents ({selectedDocIds.length} chosen) *
                </label>
                {documents.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedDocIds.length === documents.length) {
                        setSelectedDocIds([]);
                      } else {
                        setSelectedDocIds(documents.map((d) => d.id));
                      }
                    }}
                    className="text-[11px] text-amber-400 hover:underline"
                  >
                    {selectedDocIds.length === documents.length ? 'Clear' : 'Select All'}
                  </button>
                )}
              </div>

              <div className="max-h-48 overflow-y-auto bg-[#09090b] border border-zinc-800 rounded-xl p-2 space-y-1">
                {documents.map((doc) => {
                  const isChecked = selectedDocIds.includes(doc.id);
                  return (
                    <label
                      key={doc.id}
                      className="flex items-center space-x-2.5 p-2 hover:bg-zinc-900 rounded-lg cursor-pointer text-xs text-zinc-300"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelectDoc(doc.id)}
                        className="rounded bg-zinc-950 border-zinc-700 text-amber-400 focus:ring-0"
                      />
                      <span className="truncate flex-1" title={doc.original_name}>
                        {doc.original_name}
                      </span>
                      <span className="text-[10px] text-zinc-500">{doc.page_count}p</span>
                    </label>
                  );
                })}
                {documents.length === 0 && (
                  <div className="p-4 text-center text-zinc-500 text-xs">
                    No documents available in this workspace.
                  </div>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || selectedDocIds.length === 0}
              className="w-full flex items-center justify-center space-x-2 py-2.5 bg-amber-400 hover:bg-amber-300 text-black text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              <span>{isSubmitting ? 'Launching Job...' : 'Execute Extraction Pipeline'}</span>
            </button>
          </form>
        </div>

        {/* Extraction Jobs Queue */}
        <div className="lg:col-span-2 bg-[#121215] border border-zinc-800 rounded-2xl p-5 space-y-4 flex flex-col shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-zinc-800 text-xs">
            <div className="flex items-center space-x-2 text-zinc-100 font-semibold">
              <Workflow className="w-4 h-4 text-emerald-400" />
              <span>Pipeline Execution Queue</span>
            </div>
            <button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['extraction-jobs'] })}
              className="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-900 transition"
              title="Refresh queue"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3">
            {jobs.map((job) => {
              const isRunning = job.status === 'running';
              const isCompleted = job.status === 'completed';
              const isFailed = job.status === 'failed';

              return (
                <div
                  key={job.id}
                  className="p-4 bg-[#09090b] border border-zinc-800/80 rounded-xl space-y-3 text-xs"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-zinc-100">
                          Job #{job.id.slice(0, 8)}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            isCompleted
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                              : isFailed
                              ? 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
                              : isRunning
                              ? 'bg-amber-950/60 text-amber-400 border border-amber-800/60'
                              : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                          }`}
                        >
                          {job.status}
                        </span>
                        <span className="text-[11px] text-zinc-500">
                          Model: {job.pipeline_type}
                        </span>
                      </div>
                      <div className="text-[11px] text-zinc-500 mt-1">
                        Created: {new Date(job.created_at).toLocaleString()}
                      </div>
                    </div>

                    {isCompleted && job.dataset_id && (
                      <Link
                        to={`/datasets/${job.dataset_id}`}
                        className="flex items-center space-x-1.5 px-3 py-1.5 bg-amber-400 text-black hover:bg-amber-300 rounded-lg text-xs font-semibold transition"
                      >
                        <span>Inspect Dataset</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>

                  <ProgressBar progress={job.progress} showPercentage />

                  {job.metrics && Object.keys(job.metrics).length > 0 && (
                    <div className="grid grid-cols-4 gap-2 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400">
                      <div>
                        Rows: <span className="text-zinc-100 font-semibold">{job.metrics.records_extracted}</span>
                      </div>
                      <div>
                        Valid: <span className="text-emerald-400 font-semibold">{job.metrics.valid_records}</span>
                      </div>
                      <div>
                        Quality: <span className="text-amber-400 font-semibold">{job.metrics.quality_score}%</span>
                      </div>
                      <div>
                        Duration: <span className="text-zinc-200">{job.metrics.duration_ms}ms</span>
                      </div>
                    </div>
                  )}

                  {isFailed && job.error_message && (
                    <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-300 text-xs">
                      Error: {job.error_message}
                    </div>
                  )}
                </div>
              );
            })}

            {jobs.length === 0 && (
              <div className="py-12 text-center text-zinc-500 text-xs">
                No jobs executed yet. Use the configuration form to trigger a pipeline.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
