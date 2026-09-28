import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';

const TOP_NAV_ITEMS = [
  { name: 'Overview', path: '/' },
  { name: 'Workspaces', path: '/projects' },
  { name: 'Documents', path: '/documents' },
  { name: 'AI Studio', path: '/pipeline' },
  { name: 'Datasets & Review', path: '/datasets' },
  { name: 'Exports', path: '/exports' },
];

export const Header: React.FC = () => {
  const queryClient = useQueryClient();
  const {
    selectedProjectId,
    setSelectedProjectId,
    isSidebarOpen,
    toggleSidebar,
    setCreateWorkspaceModalOpen,
  } = useAppStore();

  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetSuccessMsg, setResetSuccessMsg] = useState<string | null>(null);

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: apiClient.getHealth,
    refetchInterval: 15000,
  });

  const { data: llmStatus } = useQuery({
    queryKey: ['llmStatus'],
    queryFn: apiClient.getLLMStatus,
    refetchInterval: 20000,
  });

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const isHealthy = health?.status === 'healthy';

  const handleResetSystem = async () => {
    setIsResetting(true);
    try {
      const res = await apiClient.resetSystem();
      setSelectedProjectId(null);
      queryClient.invalidateQueries();
      setIsResetModalOpen(false);
      setResetSuccessMsg(res.message || 'System reset successfully.');
      setTimeout(() => setResetSuccessMsg(null), 5000);
    } catch (err: any) {
      alert('System reset failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <>
      <header className="h-13 bg-[#171717] border-b border-white/10 flex items-center justify-between px-4 z-20 font-sans text-xs">
        {/* Left Brand & Sidebar Toggle */}
        <div className="flex items-center space-x-3">
          <button
            onClick={toggleSidebar}
            className="p-1.5 text-zinc-400 hover:text-white hover:bg-white/5 rounded-md transition-colors"
            title={isSidebarOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* OpenAI Inspired Wordmark */}
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[#10a37f]"></span>
            <span className="font-semibold text-white tracking-tight text-sm">
              DataForge
            </span>
            <span className="text-[11px] text-zinc-400 font-mono pl-1">
              v2.0
            </span>
          </div>

          {resetSuccessMsg && (
            <div className="ml-3 px-2.5 py-1 bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 rounded text-[11px]">
              {resetSuccessMsg}
            </div>
          )}
        </div>

        {/* Center Top Workflow Navigation Bar */}
        <nav className="hidden lg:flex items-center space-x-1">
          {TOP_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-white/10 text-white font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
                }`
              }
            >
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Right Workspace Switcher & Actions */}
        <div className="flex items-center space-x-2.5">
          {/* Workspace Dropdown */}
          <div className="flex items-center bg-[#212121] border border-white/10 rounded-md px-2.5 py-1 text-xs">
            <span className="text-zinc-400 mr-2 font-medium hidden sm:inline">Workspace:</span>
            <select
              value={selectedProjectId || ''}
              onChange={(e) => {
                if (e.target.value === '__NEW__') {
                  setCreateWorkspaceModalOpen(true);
                } else {
                  setSelectedProjectId(e.target.value || null);
                }
              }}
              className="bg-transparent text-white focus:outline-none cursor-pointer pr-1 text-xs font-medium"
            >
              <option value="" className="bg-[#212121] text-zinc-300">
                All Workspaces (Global)
              </option>
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#212121] text-white">
                  {p.name}
                </option>
              ))}
              <option value="__NEW__" className="bg-[#212121] text-[#10a37f] font-semibold">
                + Create New Workspace...
              </option>
            </select>
          </div>

          {/* Quick Create Workspace Button */}
          <button
            onClick={() => setCreateWorkspaceModalOpen(true)}
            className="hidden sm:inline-flex items-center px-2.5 py-1 bg-[#10a37f] hover:bg-[#0e8e6e] text-white text-xs font-medium rounded-md transition-colors"
          >
            + New Workspace
          </button>

          {/* LLM Status Telemetry */}
          {llmStatus && (
            <div className="hidden xl:flex items-center space-x-1.5 px-2.5 py-1 bg-white/5 border border-white/10 rounded-md text-[11px] text-zinc-300">
              <span className="text-[#10a37f] font-medium">•</span>
              <span className="capitalize">{llmStatus.active_provider} ({llmStatus.active_model})</span>
            </div>
          )}

          {/* Reset System Trigger */}
          <button
            onClick={() => setIsResetModalOpen(true)}
            className="px-2.5 py-1 text-zinc-400 hover:text-rose-300 hover:bg-rose-950/30 rounded-md transition-colors text-xs"
            title="Clean up platform data"
          >
            Fresh Start
          </button>

          {/* API Health Dot */}
          <div className="flex items-center space-x-1.5 text-[11px] px-2 py-1">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-rose-500 animate-pulse'}`}></span>
            <span className="text-zinc-400 hidden md:inline">{isHealthy ? 'Online' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* Reset Confirmation Modal */}
      {isResetModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 font-sans">
          <div className="w-full max-w-md bg-[#171717] border border-white/10 rounded-xl p-6 shadow-2xl text-xs text-zinc-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h2 className="font-semibold text-sm text-white">Fresh Start — Reset Platform</h2>
              <button
                onClick={() => setIsResetModalOpen(false)}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-zinc-300 leading-relaxed">
              Are you sure you want to reset and remove all platform data? This action will clean up:
            </p>
            <ul className="list-disc list-inside space-y-1 text-zinc-400 pl-1">
              <li>All Workspaces & Research Projects</li>
              <li>Ingested PDF Documents & Page Layout Cache</li>
              <li>Extracted Datasets & Structured Audit Records</li>
              <li>Human Review Logs & Export Histories</li>
            </ul>

            <div className="flex justify-end space-x-2 pt-3 border-t border-white/10">
              <button
                type="button"
                onClick={() => setIsResetModalOpen(false)}
                className="px-3.5 py-1.5 bg-[#212121] hover:bg-white/10 text-zinc-300 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleResetSystem}
                disabled={isResetting}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-medium rounded-md transition-colors"
              >
                {isResetting ? 'Resetting...' : 'Confirm Reset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
