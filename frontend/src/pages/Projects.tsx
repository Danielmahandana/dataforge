import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Project } from '../types';

export const Projects: React.FC = () => {
  const queryClient = useQueryClient();
  const {
    selectedProjectId,
    setSelectedProjectId,
    setCreateWorkspaceModalOpen,
  } = useAppStore();

  const [editingProject, setEditingProject] = useState<Project | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => apiClient.updateProject(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setEditingProject(null);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Update failed.';
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

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject || !name.trim()) {
      setErrorMessage('Workspace name is required.');
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
    <div className="space-y-6 max-w-6xl mx-auto font-sans text-xs">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/10">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Workspaces
          </h1>
          <p className="text-zinc-400 mt-1">
            Organize document blueprints, AI extractions, and relational datasets by project scope
          </p>
        </div>
        <button
          onClick={() => setCreateWorkspaceModalOpen(true)}
          className="px-4 py-2 bg-[#10a37f] hover:bg-[#0e8e6e] text-white font-medium rounded-md transition-colors"
        >
          + New Workspace
        </button>
      </div>

      {/* Workspaces Frameless List */}
      <div className="divide-y divide-white/10">
        {projects.map((project) => {
          const isSelected = selectedProjectId === project.id;
          return (
            <div
              key={project.id}
              className={`py-4 px-3 rounded-lg transition-colors ${
                isSelected ? 'bg-white/5' : 'hover:bg-white/[0.02]'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1 max-w-2xl">
                  <div className="flex items-center space-x-2">
                    <h2 className="text-sm font-semibold text-white">
                      {project.name}
                    </h2>
                    {isSelected && (
                      <span className="px-2 py-0.5 bg-[#10a37f]/20 text-[#10a37f] text-[10px] font-medium rounded">
                        Active Workspace
                      </span>
                    )}
                  </div>
                  <p className="text-zinc-400 leading-relaxed">
                    {project.description || 'No description provided.'}
                  </p>
                  {project.tags && project.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {project.tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 bg-[#212121] text-zinc-300 rounded text-[10px] font-mono"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right text-zinc-400 font-mono text-[11px] hidden sm:block">
                    <div>{project.document_count} doc(s)</div>
                    <div>{project.dataset_count} dataset(s)</div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSelectedProjectId(isSelected ? null : project.id)}
                      className={`px-3 py-1.5 rounded-md font-medium text-xs transition-colors ${
                        isSelected
                          ? 'bg-[#10a37f] text-white'
                          : 'bg-[#212121] hover:bg-white/10 text-zinc-300'
                      }`}
                    >
                      {isSelected ? 'Selected' : 'Select Scope'}
                    </button>
                    <button
                      onClick={() => startEdit(project)}
                      className="px-2.5 py-1.5 text-zinc-400 hover:text-white rounded-md transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete workspace "${project.name}"?`)) {
                          deleteMutation.mutate(project.id);
                        }
                      }}
                      className="px-2.5 py-1.5 text-zinc-400 hover:text-rose-400 rounded-md transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {projects.length === 0 && !isLoading && (
        <div className="py-16 text-center text-zinc-400 space-y-3">
          <div className="text-sm text-zinc-300 font-medium">No Workspaces Available</div>
          <p className="text-zinc-500 max-w-md mx-auto">
            Create your first workspace to start uploading documents and defining extraction schemas.
          </p>
          <button
            onClick={() => setCreateWorkspaceModalOpen(true)}
            className="px-4 py-2 bg-[#10a37f] hover:bg-[#0e8e6e] text-white font-medium rounded-md transition-colors"
          >
            + Create First Workspace
          </button>
        </div>
      )}

      {/* Edit Modal */}
      {editingProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-[#171717] border border-white/10 rounded-xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h2 className="text-sm font-semibold text-white">Edit Workspace</h2>
              <button
                onClick={() => setEditingProject(null)}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {errorMessage && (
              <div className="p-3 bg-rose-950/70 border border-rose-800/60 rounded-md text-rose-200">
                {errorMessage}
              </div>
            )}

            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Workspace Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#212121] border border-white/10 rounded-md text-white focus:outline-none focus:border-[#10a37f]"
                />
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-[#212121] border border-white/10 rounded-md text-white focus:outline-none focus:border-[#10a37f]"
                />
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  className="w-full px-3 py-2 bg-[#212121] border border-white/10 rounded-md text-white focus:outline-none focus:border-[#10a37f]"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setEditingProject(null)}
                  className="px-3.5 py-1.5 bg-[#212121] hover:bg-white/10 text-zinc-300 rounded-md"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-4 py-1.5 bg-[#10a37f] hover:bg-[#0e8e6e] text-white font-medium rounded-md transition-colors"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
