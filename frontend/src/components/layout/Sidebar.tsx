import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  FileText,
  Workflow,
  Database,
  ShieldCheck,
  History,
  Download,
  Sparkles,
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Overview', path: '/', icon: LayoutDashboard },
  { name: 'Workspaces', path: '/projects', icon: FolderGit2 },
  { name: 'Ingest & Blueprints', path: '/documents', icon: FileText },
  { name: 'AI Extraction Studio', path: '/pipeline', icon: Workflow },
  { name: 'Relational Datasets', path: '/datasets', icon: Database },
  { name: 'Validation Audit', path: '/validation', icon: ShieldCheck },
  { name: 'Review Queue', path: '/review', icon: History },
  { name: 'Relational Exports', path: '/exports', icon: Download },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-56 bg-[#09090b] border-r border-zinc-800/80 flex flex-col justify-between py-4">
      {/* Primary Navigation */}
      <nav className="space-y-1 px-3">
        <div className="px-3 pb-2 text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Data Engineering Workflow
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-zinc-800/90 text-amber-400 border border-zinc-700/80 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info / Provenance Badge */}
      <div className="px-4 py-3 mx-3 bg-zinc-900/60 border border-zinc-800 rounded-xl text-xs text-zinc-400">
        <div className="flex items-center space-x-1.5 text-amber-400 text-xs font-semibold mb-1">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Universal Lineage</span>
        </div>
        <p className="text-[11px] text-zinc-500 leading-relaxed">
          Zero data corruption guarantee. Exact PDF page bounding box provenance tracked per cell.
        </p>
      </div>
    </aside>
  );
};
