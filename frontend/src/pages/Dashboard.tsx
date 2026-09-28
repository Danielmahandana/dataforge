import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
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

export const Dashboard: React.FC = () => {
  const { selectedProjectId, setCreateWorkspaceModalOpen } = useAppStore();

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

  const totalRecords = datasets.reduce((sum, d) => sum + d.record_count, 0);
  const totalValid = datasets.reduce((sum, d) => sum + d.valid_record_count, 0);
  const totalWarnings = datasets.reduce((sum, d) => sum + d.warning_record_count, 0);
  const totalErrors = datasets.reduce((sum, d) => sum + d.error_record_count, 0);
  const totalCurationReview = datasets.reduce((sum, d) => sum + (d.curation_summary?.review_required || 0), 0);

  const avgQualityScore =
    datasets.length > 0
      ? (datasets.reduce((sum, d) => sum + d.quality_score, 0) / datasets.length).toFixed(1)
      : '100.0';

  const chartData = [
    { name: 'Valid', count: totalValid, color: '#10a37f' },
    { name: 'Warnings', count: totalWarnings, color: '#d97706' },
    { name: 'Errors', count: totalErrors, color: '#e53e3e' },
  ];

  const noProjects = projects.length === 0;

  return (
    <div className="space-y-7 max-w-6xl mx-auto font-sans text-xs">

      {/* Page Header */}
      <div className="flex items-center justify-between pb-5 border-b border-white/10">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Workstation Overview</h1>
          <p className="text-zinc-400 mt-1">
            Extraction pipeline telemetry, quality metrics, and audit trail
            {selectedProjectId && ' — filtered by active workspace'}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Link
            to="/documents"
            className="px-3.5 py-2 bg-[#212121] hover:bg-white/10 text-zinc-300 border border-white/10 rounded-md transition-colors font-medium"
          >
            Upload Documents
          </Link>
          <Link
            to="/pipeline"
            className="px-4 py-2 bg-[#10a37f] hover:bg-[#0e8e6e] text-white rounded-md font-medium transition-colors"
          >
            Run Pipeline
          </Link>
        </div>
      </div>

      {/* Empty State: No Workspaces — Prominent CTA */}
      {noProjects && (
        <div className="py-14 flex flex-col items-center text-center space-y-4 bg-[#171717] rounded-xl border border-white/10">
          <div className="text-sm font-semibold text-white">Welcome to DataForge</div>
          <p className="text-zinc-400 max-w-md leading-relaxed">
            Get started by creating your first research workspace. Workspaces let you isolate documents, define extraction blueprints, and manage relational datasets independently.
          </p>
          <button
            onClick={() => setCreateWorkspaceModalOpen(true)}
            className="px-5 py-2.5 bg-[#10a37f] hover:bg-[#0e8e6e] text-white font-medium rounded-md transition-colors"
          >
            Create a Workspace
          </button>
          <p className="text-zinc-500 text-[11px]">
            After creating a workspace, upload PDF documents and run the AI extraction pipeline.
          </p>
        </div>
      )}

      {/* Review Queue Alert */}
      {totalCurationReview > 0 && (
        <div className="flex items-center justify-between px-4 py-3 bg-amber-950/20 border border-amber-800/40 rounded-lg">
          <div className="flex items-center space-x-3">
            <span className="font-mono font-bold text-amber-300 text-sm">{totalCurationReview}</span>
            <div>
              <div className="font-medium text-amber-200">Records require research review</div>
              <div className="text-zinc-400 mt-0.5">
                Low confidence, borderline matches, or structural ambiguities detected.
              </div>
            </div>
          </div>
          <Link
            to="/review"
            className="px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white font-medium rounded-md transition-colors flex-shrink-0"
          >
            Open Review Queue →
          </Link>
        </div>
      )}

      {/* KPI Metric Row — Frameless */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-white/10 rounded-xl overflow-hidden border border-white/10">
        {[
          {
            label: 'Research Workspaces',
            value: projects.length,
            sub: selectedProjectId ? 'Active scope' : 'Across all projects',
          },
          {
            label: 'Ingested Documents',
            value: documents.length,
            sub: 'PDFs classified & parsed',
          },
          {
            label: 'Extracted Records',
            value: totalRecords.toLocaleString(),
            sub: `${totalValid.toLocaleString()} validated rows`,
            highlight: true,
          },
          {
            label: 'Quality Index',
            value: `${avgQualityScore}%`,
            sub: `${datasets.length} active dataset(s)`,
          },
        ].map((card, i) => (
          <div key={i} className="bg-[#171717] px-5 py-4">
            <div className="text-zinc-400 font-medium">{card.label}</div>
            <div className={`text-2xl font-bold font-mono mt-1.5 ${card.highlight ? 'text-[#10a37f]' : 'text-white'}`}>
              {card.value}
            </div>
            <div className="text-zinc-500 mt-0.5 font-mono text-[10px]">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Main Content Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Record Quality Chart */}
        <div className="lg:col-span-2 bg-[#171717] border border-white/10 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-white">Record Quality Distribution</h2>
              <p className="text-zinc-400 mt-0.5">Validation status across all extracted table rows</p>
            </div>
            <Link
              to="/validation"
              className="text-[#10a37f] hover:text-[#0e8e6e] font-medium"
            >
              View Audit →
            </Link>
          </div>
          <div className="h-56">
            {totalRecords > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30, top: 5, bottom: 5 }}>
                  <XAxis type="number" stroke="#404040" fontSize={11} tick={{ fill: '#707070' }} />
                  <YAxis dataKey="name" type="category" stroke="#404040" fontSize={12} width={70} tick={{ fill: '#a1a1a1' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#212121',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#ececec',
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
              <div className="h-full flex flex-col items-center justify-center text-zinc-500 space-y-2">
                <div className="text-sm text-zinc-400">No dataset records yet</div>
                <p className="text-zinc-500">Ingest documents and run the pipeline to see metrics</p>
              </div>
            )}
          </div>
        </div>

        {/* Audit Trail Activity Feed */}
        <div className="bg-[#171717] border border-white/10 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Recent Audit Trail</h2>
          <div className="space-y-2 overflow-y-auto max-h-64 pr-1">
            {activities.length > 0 ? (
              activities.map((act) => (
                <div
                  key={act.id}
                  className="px-3 py-2.5 bg-[#212121] rounded-lg space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[#10a37f] text-[10px] uppercase font-bold tracking-wider">
                      {act.action}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-zinc-200 line-clamp-2 leading-relaxed">{act.description}</p>
                  <div className="text-zinc-500 font-mono text-[10px]">by {act.user}</div>
                </div>
              ))
            ) : (
              <div className="py-10 text-center text-zinc-500">
                No activity records yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Workflow Navigation Cards — only show if workspaces exist */}
      {!noProjects && (
        <div>
          <h2 className="text-sm font-semibold text-white mb-3">Quick Access</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Workspaces', desc: 'Manage projects & scopes', to: '/projects' },
              { label: 'Ingest Documents', desc: 'Upload & classify PDFs', to: '/documents' },
              { label: 'AI Studio', desc: 'Run extraction pipeline', to: '/pipeline' },
              { label: 'Datasets', desc: 'Browse extracted records', to: '/datasets' },
              { label: 'Validation', desc: 'Audit data quality', to: '/validation' },
              { label: 'Review Queue', desc: 'Resolve flagged records', to: '/review' },
              { label: 'Exports', desc: 'Download datasets', to: '/exports' },
            ].map((nav) => (
              <Link
                key={nav.to}
                to={nav.to}
                className="p-3.5 bg-[#171717] hover:bg-white/5 border border-white/10 rounded-lg transition-colors space-y-1"
              >
                <div className="text-white font-medium">{nav.label}</div>
                <div className="text-zinc-400">{nav.desc}</div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
