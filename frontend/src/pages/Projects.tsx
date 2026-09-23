import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderPlus,
  FolderGit2,
  FileText,
  Database,
  Trash2,
  Edit2,
  Tag,
  Check,
  X,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Project } from '../types';

export const Projects: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedProjectId, setSelectedProjectId } = useAppStore();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const createMutation = useMutation({
    mutationFn: apiClient.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setIsCreateOpen(false);
      setName('');
      setDescription('');
      setTagsInput('');
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Could not connect to backend server. Make sure port 8000 is running.';
      setErrorMessage(msg);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => apiClient.updateProject(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setEditingProject(null);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Could not connect to backend server. Make sure port 8000 is running.';
      setErrorMessage(msg);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteProject,
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      if (selectedProjectId === deletedId) {
        setSelectedProjectId(null);
      }
    },
    onError: (err: any) => {
      alert('Delete failed: ' + (err.response?.data?.detail || err.message));
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMessage('Project name is required.');
      return;
    }
    setErrorMessage(null);
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined, tags });
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject || !name.trim()) {
      setErrorMessage('Project name is required.');
      return;
    }
    setErrorMessage(null);
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    updateMutation.mutate({
      id: editingProject.id,
      data: { name: name.trim(), description: description.trim() || undefined, tags },
    });
  };

  const startEdit = (p: Project) => {
    setEditingProject(p);
    setName(p.name);
    setDescription(p.description || '');
    setTagsInput((p.tags || []).join(', '));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight font-sans">
            Research Workspaces
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Isolate extraction blueprints, documents, and relational datasets by project scope
          </p>
        </div>
        <button
          onClick={() => {
            setIsCreateOpen(true);
            setEditingProject(null);
            setName('');
            setDescription('');
            setTagsInput('');
          }}
          className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Workspace</span>
        </button>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {projects.map((project) => {
          const isSelected = selectedProjectId === project.id;
          return (
            <div
              key={project.id}
              className={`flex flex-col justify-between p-5 bg-[#121215] border rounded-xl transition-all ${
                isSelected
                  ? 'border-emerald-500/80 shadow-md shadow-emerald-500/5'
                  : 'border-zinc-800 hover:border-zinc-700'
              }`}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2.5">
                    <FolderGit2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <h2 className="text-sm font-semibold text-zinc-100 line-clamp-1">
                      {project.name}
                    </h2>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => startEdit(project)}
                      className="p-1 text-zinc-400 hover:text-zinc-200 rounded transition-colors"
                      title="Edit project"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete project "${project.name}" and all associated data?`)) {
                          deleteMutation.mutate(project.id);
                        }
                      }}
                      className="p-1 text-zinc-400 hover:text-rose-400 rounded transition-colors"
                      title="Delete project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-zinc-400 mt-2 line-clamp-2 min-h-[2.5rem] leading-relaxed">
                  {project.description || 'No description provided.'}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mt-4">
                  {project.tags && project.tags.length > 0 ? (
                    project.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center space-x-1 px-2 py-0.5 bg-zinc-900 text-amber-300/90 border border-zinc-800 rounded text-[10px]"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        <span>{tag}</span>
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px] text-zinc-500 italic">No tags</span>
                  )}
                </div>
              </div>

              {/* Stats & Select Button */}
              <div className="mt-5 pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-3 text-zinc-400">
                  <span className="flex items-center space-x-1">
                    <FileText className="w-3.5 h-3.5 text-sky-400" />
                    <span>{project.document_count}</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Database className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{project.dataset_count}</span>
                  </span>
                </div>

                <button
                  onClick={() => setSelectedProjectId(isSelected ? null : project.id)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    isSelected
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
                  }`}
                >
                  {isSelected ? 'Active Workspace' : 'Select Scope'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {projects.length === 0 && !isLoading && (
        <div className="p-12 text-center bg-[#121215] border border-dashed border-zinc-800 rounded-xl">
          <FolderGit2 className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-zinc-300 font-sans">No Workspaces Found</h3>
          <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
            Create your first workspace to start uploading PDF documents and extracting structured data.
          </p>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="mt-4 px-4 py-2 bg-emerald-600 text-white hover:bg-emerald-500 text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            Create Workspace
          </button>
        </div>
      )}

      {/* Create / Edit Modal */}
      {(isCreateOpen || editingProject) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-[#121215] border border-zinc-800 rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <h2 className="text-sm font-bold text-zinc-100 font-sans">
                {editingProject ? 'Edit Workspace' : 'Create New Workspace'}
              </h2>
              <button
                onClick={() => {
                  setIsCreateOpen(false);
                  setEditingProject(null);
                }}
                className="text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {errorMessage && (
              <div className="mt-3 p-3 bg-rose-950/80 border border-rose-800 rounded-lg text-xs text-rose-300 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">Action Failed</div>
                  <div>{errorMessage}</div>
                </div>
              </div>
            )}

            <form onSubmit={editingProject ? handleUpdate : handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs text-zinc-300 mb-1 font-medium">
                  Workspace Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. merSETA Occupational Qualifications Audit 2026"
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-sans"
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-300 mb-1 font-medium">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of research initiative and extraction goals..."
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-sans"
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-300 mb-1 font-medium">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="e.g. DHET, TVET, Qualifications, 2026"
                  className="w-full px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-sans"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreateOpen(false);
                    setEditingProject(null);
                  }}
                  className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-1.5 bg-emerald-600 text-white hover:bg-emerald-500 text-xs font-semibold rounded-lg shadow-sm transition-colors"
                >
                  {editingProject ? 'Save Changes' : 'Create Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

