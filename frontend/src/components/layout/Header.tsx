import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Sparkles, FolderGit2, CheckCircle2, AlertCircle, RefreshCw, Trash2, X } from 'lucide-react';
import { apiClient } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';

export const Header: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedProjectId, setSelectedProjectId } = useAppStore();

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
      <header className="h-14 bg-[#09090b] border-b border-zinc-800/80 flex items-center justify-between px-6 z-20">
        {/* Brand & Platform Identifier */}
        <div className="flex items-center space-x-3">
          <div className="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-700 flex items-center justify-center font-bold text-amber-400 text-xs shadow-sm">
            DF
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-sm text-zinc-100 tracking-tight font-sans">
              Darkroom DataForge
            </span>
            <span className="px-2 py-0.5 bg-zinc-900 text-zinc-400 text-[10px] font-mono rounded border border-zinc-800">
              v2.0 Universal
            </span>
          </div>

          {resetSuccessMsg && (
            <div className="ml-4 px-3 py-1 bg-emerald-950/80 border border-emerald-800 rounded-lg text-xs font-sans text-emerald-400 flex items-center space-x-1.5 animate-pulse">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{resetSuccessMsg}</span>
            </div>
          )}
        </div>

        {/* Workspace Selector & LLM / Backend Telemetry & Reset Button */}
        <div className="flex items-center space-x-3">
          {/* Project Selector */}
          <div className="flex items-center space-x-2 bg-zinc-900/80 border border-zinc-800 px-3 py-1.5 rounded-lg text-xs">
            <FolderGit2 className="w-3.5 h-3.5 text-amber-400" />
            <select
              value={selectedProjectId || ''}
              onChange={(e) => setSelectedProjectId(e.target.value || null)}
              className="bg-transparent text-xs text-zinc-200 focus:outline-none cursor-pointer pr-2 font-sans"
            >
              <option value="" className="bg-[#121215] text-zinc-400">
                All Workspaces (Global)
              </option>
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#121215] text-zinc-200">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Groq AI Telemetry Badge */}
          {llmStatus && (
            <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-zinc-300">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span className="capitalize">{llmStatus.active_provider} ({llmStatus.active_model})</span>
            </div>
          )}

          {/* Fresh Start / Reset Platform Button */}
          <button
            onClick={() => setIsResetModalOpen(true)}
            className="flex items-center space-x-1.5 px-3 py-1 bg-zinc-900 hover:bg-rose-950/60 text-zinc-400 hover:text-rose-300 border border-zinc-800 hover:border-rose-800/60 rounded-lg text-xs font-medium transition-colors"
            title="Clean up platform data for a fresh start"
          >
            <RefreshCw className="w-3.5 h-3.5 text-rose-400" />
            <span>Fresh Start</span>
          </button>

          {/* Backend Online Indicator */}
          <div className="flex items-center space-x-2">
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-sans ${
                isHealthy
                  ? 'text-emerald-400 bg-emerald-950/30 border border-emerald-800/40'
                  : 'text-rose-400 bg-rose-950/40 border border-rose-800/60'
              }`}
            >
              {isHealthy ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>API Online</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span>API Offline</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Reset Confirmation Modal */}
      {isResetModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-[#121215] border border-zinc-800 rounded-xl p-6 shadow-2xl font-sans">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center space-x-2 text-rose-400 font-bold text-sm">
                <Trash2 className="w-4 h-4" />
                <span>Fresh Start - System Reset</span>
              </div>
              <button
                onClick={() => setIsResetModalOpen(false)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3">
              <p className="text-xs text-zinc-300 leading-relaxed">
                Are you sure you want to clean up all platform data for a fresh start?
              </p>
              <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-[11px] text-rose-300 space-y-1">
                <div className="font-semibold">This action will erase:</div>
                <ul className="list-disc list-inside space-y-0.5 text-zinc-400">
                  <li>All Workspaces & Projects</li>
                  <li>All Ingested PDF Documents</li>
                  <li>All Extracted Structured Datasets & Records</li>
                  <li>All Validation Audit Logs & Review Histories</li>
                </ul>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-3 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setIsResetModalOpen(false)}
                className="px-3.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleResetSystem}
                disabled={isResetting}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center space-x-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
                <span>{isResetting ? 'Resetting System...' : 'Reset & Start Fresh'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

