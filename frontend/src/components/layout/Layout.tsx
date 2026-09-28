import React from 'react';
import { Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { SourceDocumentModal } from '../common/SourceDocumentModal';
import { CreateWorkspaceModal } from '../common/CreateWorkspaceModal';

export const Layout: React.FC = () => {
  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: apiClient.getHealth,
    refetchInterval: 6000,
    retry: 1,
  });

  const isOffline = isError || !health || health.status !== 'healthy';

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#0d0d0e] text-zinc-100 font-sans selection:bg-[#10a37f]/30 selection:text-white">
      <Header />
      {isOffline && (
        <div className="bg-rose-950/70 border-b border-rose-800/60 px-4 py-1 text-xs text-rose-200 flex items-center justify-between z-30 font-sans">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-rose-400 animate-ping"></span>
            <span>
              <strong>Backend Offline:</strong> Cannot reach FastAPI on{' '}
              <code className="bg-black/40 px-1 py-0.5 rounded text-rose-300 font-mono">
                http://127.0.0.1:8000
              </code>
            </span>
          </div>
          <span className="text-[11px] text-rose-300 hidden md:inline font-mono">
            Run <code className="bg-black/50 px-1.5 py-0.5 rounded text-amber-300 font-bold">python run_dev.py</code> in backend terminal.
          </span>
        </div>
      )}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-[#0d0d0e] p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
      <SourceDocumentModal />
      <CreateWorkspaceModal />
    </div>
  );
};
