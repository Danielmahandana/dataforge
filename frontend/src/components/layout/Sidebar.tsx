import React from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';

const NAV_ITEMS = [
  { name: 'Overview', path: '/' },
  { name: 'Workspaces', path: '/projects' },
  { name: 'Documents & Blueprints', path: '/documents' },
  { name: 'AI Extraction Studio', path: '/pipeline' },
  { name: 'Relational Datasets', path: '/datasets' },
  { name: 'Validation Audit', path: '/validation' },
  { name: 'Review Queue', path: '/review' },
  { name: 'Relational Exports', path: '/exports' },
];

export const Sidebar: React.FC = () => {
  const {
    selectedProjectId,
    setSelectedProjectId,
    isSidebarOpen,
    setCreateWorkspaceModalOpen,
  } = useAppStore();

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  if (!isSidebarOpen) {
    return null;
  }

  return (
    <aside className="w-60 bg-[#171717] border-r border-white/10 flex flex-col justify-between py-3 px-3 transition-all font-sans text-xs">
      <div className="space-y-4">
        {/* Top Action: New Workspace Button */}
        <button
          onClick={() => setCreateWorkspaceModalOpen(true)}
          className="w-full flex items-center justify-between px-3 py-2 bg-[#212121] hover:bg-white/10 text-white rounded-lg border border-white/10 text-xs font-medium transition-colors"
        >
          <span>+ New Workspace</span>
          <span className="text-[10px] text-zinc-400 font-mono">⌘N</span>
        </button>

        {/* Active Workspaces Thread List (ChatGPT Style) */}
        <div>
          <div className="flex items-center justify-between px-2 pb-1.5 text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
            <span>Workspaces</span>
            <span className="font-mono text-zinc-400">{projects.length}</span>
          </div>

          <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1">
            <button
              onClick={() => setSelectedProjectId(null)}
              className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs transition-colors flex items-center justify-between ${
                selectedProjectId === null
                  ? 'bg-white/10 text-white font-medium'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
              }`}
            >
              <span className="truncate">All Workspaces (Global)</span>
              {selectedProjectId === null && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#10a37f]"></span>
              )}
            </button>

            {projects.map((proj) => {
              const isSelected = selectedProjectId === proj.id;
              return (
                <button
                  key={proj.id}
                  onClick={() => setSelectedProjectId(proj.id)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs transition-colors flex items-center justify-between ${
                    isSelected
                      ? 'bg-white/10 text-white font-medium'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
                  }`}
                >
                  <span className="truncate">{proj.name}</span>
                  {isSelected && (
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10a37f]"></span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Main Navigation Flow */}
        <div>
          <div className="px-2 pb-1.5 text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
            Navigation
          </div>
          <nav className="space-y-0.5">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `block px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
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
        </div>
      </div>

      {/* Footer Info Badge */}
      <div className="pt-3 border-t border-white/10 px-2">
        <div className="text-[11px] text-zinc-400 font-medium">
          Universal Document Provenance
        </div>
        <p className="text-[10px] text-zinc-500 mt-0.5 leading-relaxed">
          Zero data corruption. Exact PDF page bounding box lineage.
        </p>
      </div>
    </aside>
  );
};
