import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';

export const CreateWorkspaceModal: React.FC = () => {
  const queryClient = useQueryClient();
  const {
    isCreateWorkspaceModalOpen,
    setCreateWorkspaceModalOpen,
    setSelectedProjectId,
  } = useAppStore();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: apiClient.createProject,
    onSuccess: (newProj) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      if (newProj && newProj.id) {
        setSelectedProjectId(newProj.id);
      }
      setCreateWorkspaceModalOpen(false);
      setName('');
      setDescription('');
      setTagsInput('');
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Could not create workspace. Make sure backend is running.';
      setErrorMessage(msg);
    },
  });

  if (!isCreateWorkspaceModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMessage('Workspace name is required.');
      return;
    }
    setErrorMessage(null);
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined, tags });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 font-sans text-xs">
      <div className="w-full max-w-md bg-[#171717] border border-white/10 rounded-xl p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <h2 className="text-sm font-semibold text-white">Create Research Workspace</h2>
          <button
            onClick={() => setCreateWorkspaceModalOpen(false)}
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-zinc-300 font-medium mb-1">
              Workspace Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Occupational Qualifications Audit 2026"
              className="w-full px-3 py-2 bg-[#212121] border border-white/10 rounded-md text-white placeholder-zinc-500 focus:outline-none focus:border-[#10a37f]"
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
              placeholder="Primary extraction scope, documents and target datasets..."
              className="w-full px-3 py-2 bg-[#212121] border border-white/10 rounded-md text-white placeholder-zinc-500 focus:outline-none focus:border-[#10a37f]"
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
              placeholder="e.g. DHET, TVET, 2026"
              className="w-full px-3 py-2 bg-[#212121] border border-white/10 rounded-md text-white placeholder-zinc-500 focus:outline-none focus:border-[#10a37f]"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-3 border-t border-white/10">
            <button
              type="button"
              onClick={() => setCreateWorkspaceModalOpen(false)}
              className="px-3.5 py-1.5 bg-[#212121] hover:bg-white/10 text-zinc-300 rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-1.5 bg-[#10a37f] hover:bg-[#0e8e6e] text-white font-medium rounded-md transition-colors"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Workspace'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
