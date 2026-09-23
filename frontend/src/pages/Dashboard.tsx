import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FolderGit2,
  FileText,
  Database,
  ShieldCheck,
  ArrowUpRight,
  Upload,
  Play,
  Activity,
  Sparkles,
  BarChart2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';

export const Dashboard: React.FC = () => {
  const { selectedProjectId } = useAppStore();

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', selectedProjectId],
    queryFn: () => apiClient.getDocuments(selectedProjectId || undefined),
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  const { data: activities = [] } = useQuery({
    queryKey: ['activity', selectedProjectId],
    queryFn: () => apiClient.getActivity(selectedProjectId || undefined, 8),
  });

  // Aggregate Metrics
  const totalRecords = datasets.reduce((sum, d) => sum + d.record_count, 0);
  const totalValid = datasets.reduce((sum, d) => sum + d.valid_record_count, 0);
  const totalWarnings = datasets.reduce((sum, d) => sum + d.warning_record_count, 0);
  const totalErrors = datasets.reduce((sum, d) => sum + d.error_record_count, 0);

  const avgQualityScore =
    datasets.length > 0
      ? (datasets.reduce((sum, d) => sum + d.quality_score, 0) / datasets.length).toFixed(1)
      : '100.0';

  const chartData = [
    { name: 'Valid', count: totalValid, color: '#10B981' },
    { name: 'Warnings', count: totalWarnings, color: '#F59E0B' },
    { name: 'Errors', count: totalErrors, color: '#EF4444' },
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight font-sans">
            Workstation Overview
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Universal document intelligence pipeline metrics and extraction audit telemetry
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/documents"
            className="flex items-center space-x-2 px-3.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-200 border border-zinc-700 rounded-lg transition-colors"
          >
            <Upload className="w-4 h-4 text-emerald-400" />
            <span>Upload Documents</span>
          </Link>
          <Link
            to="/pipeline"
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>Run Pipeline</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400">Total Workspaces</span>
            <FolderGit2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">
            {projects.length}
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">
            {selectedProjectId ? 'Active workspace filtered' : 'Across all initiatives'}
          </div>
        </div>

        <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400">Ingested Documents</span>
            <FileText className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">
            {documents.length}
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">
            PDFs classified & layout parsed
          </div>
        </div>

        <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400">Extracted Records</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">
            {totalRecords.toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-emerald-400 font-mono font-medium">
            {totalValid.toLocaleString()} validated rows
          </div>
        </div>

        <div className="p-4 bg-[#121215] border border-zinc-800 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400">Quality Index</span>
            <ShieldCheck className="w-4 h-4 text-amber-300" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">
            {avgQualityScore}%
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">
            Across {datasets.length} active dataset(s)
          </div>
        </div>
      </div>

      {/* Main Grid: Quality Chart & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Record Integrity Distribution Chart */}
        <div className="lg:col-span-2 bg-[#121215] border border-zinc-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-zinc-100 font-sans">
                Record Quality Distribution
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Data validation status across all extracted table rows
              </p>
            </div>
            <Link
              to="/validation"
              className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center space-x-1 font-medium"
            >
              <span>View Audit</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="h-60 w-full">
            {totalRecords > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30, top: 10, bottom: 10 }}>
                  <XAxis type="number" stroke="#71717a" fontSize={11} />
                  <YAxis dataKey="name" type="category" stroke="#a1a1aa" fontSize={12} width={70} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#18181b',
                      borderColor: '#27272a',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#f4f4f5',
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-zinc-500 text-xs font-sans">
                <Database className="w-8 h-8 text-zinc-700 mb-2" />
                <span>No dataset records generated yet. Ingest documents to view metrics.</span>
              </div>
            )}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-zinc-100 font-sans">
                Recent Audit Trail
              </h2>
            </div>
          </div>

          <div className="space-y-3">
            {activities.length > 0 ? (
              activities.map((act) => (
                <div
                  key={act.id}
                  className="p-3 bg-[#09090b] border border-zinc-800/80 rounded-lg text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-emerald-400 text-[10px] uppercase font-bold tracking-wider">
                      {act.action}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-zinc-200 mt-1 line-clamp-2 leading-relaxed">{act.description}</p>
                  <div className="mt-1 text-[10px] text-zinc-500 font-mono">
                    by {act.user}
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-zinc-500 text-xs font-mono">
                No activity records yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

