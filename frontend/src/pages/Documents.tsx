import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  Search,
  Eye,
  Play,
  Trash2,
  FileSearch,
  X,
  Sparkles,
  Layers,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Document } from '../types';

export const Documents: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedProjectId, openSourceModal } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProjectId, setUploadProjectId] = useState(selectedProjectId || '');
  const [uploadDocType, setUploadDocType] = useState('universal_auto');
  const [inspectingDoc, setInspectingDoc] = useState<Document | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', selectedProjectId],
    queryFn: () => apiClient.getDocuments(selectedProjectId || undefined),
  });

  const { data: inspectionData } = useQuery({
    queryKey: ['document-inspect', inspectingDoc?.id],
    queryFn: () => apiClient.inspectDocument(inspectingDoc!.id),
    enabled: !!inspectingDoc,
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setSelectedDocIds([]);
    },
  });

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const targetProjId = uploadProjectId || (projects.length > 0 ? projects[0].id : null);
    if (!targetProjId) {
      alert('Please select or create a research workspace first before uploading documents.');
      return;
    }

    setIsUploading(true);
    try {
      await apiClient.uploadDocuments(
        targetProjId,
        Array.from(files),
        uploadDocType
      );
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    } catch (err: any) {
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const filteredDocs = documents.filter((doc) =>
    doc.original_name.toLowerCase().includes(search.toLowerCase()) ||
    doc.doc_type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
            Document Ingestion & Blueprints
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Ingest PDFs and assign dynamic Extraction Blueprints (qualifications, occupations, codebooks, financial statements, or auto-inferred).
          </p>
        </div>

        {selectedDocIds.length > 0 && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                navigate('/pipeline', { state: { documentIds: selectedDocIds } });
              }}
              className="flex items-center space-x-2 px-4 py-2 bg-amber-400 hover:bg-amber-300 text-black text-xs font-semibold rounded-xl transition-all shadow-sm"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Launch Pipeline on ({selectedDocIds.length}) Document(s)</span>
            </button>
          </div>
        )}
      </div>

      {/* OpenAI Minimalist Ingestion Dropzone */}
      <div className="p-6 bg-[#121215] border border-zinc-800 rounded-2xl shadow-sm transition-all hover:border-zinc-700">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-zinc-900 rounded-xl border border-zinc-800 flex items-center justify-center text-amber-400">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">
                Ingest Research Documents (PDF)
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Drop reports, codebooks, TVET lists, OFO catalogues, or financial statements.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            {/* Target Project Selection */}
            <select
              value={uploadProjectId}
              onChange={(e) => setUploadProjectId(e.target.value)}
              className="px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
            >
              <option value="">Select Target Workspace...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            {/* Dynamic Extraction Blueprint Selector */}
            <select
              value={uploadDocType}
              onChange={(e) => setUploadDocType(e.target.value)}
              className="px-3 py-2 bg-[#09090b] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
            >
              <option value="universal_auto">✨ AI Auto-Inferred Schema</option>
              <option value="qualifications">🎓 TVET Qualifications & Offerings</option>
              <option value="occupations">💼 OIHD Occupations (OFO Codes)</option>
              <option value="codebook">📊 Survey Metadata Codebook (QLFS)</option>
              <option value="financial">📈 Financial Statements & Balance Sheets</option>
            </select>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />

            <button
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-amber-400 hover:bg-amber-300 text-black text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            >
              {isUploading ? 'Ingesting Files...' : 'Select PDF Files'}
            </button>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative flex-1 w-full sm:max-w-md">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by document name or extraction blueprint..."
            className="w-full pl-10 pr-4 py-2 bg-[#121215] border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-amber-400"
          />
        </div>
        <div className="text-xs text-zinc-400">
          Showing {filteredDocs.length} of {documents.length} document(s)
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-[#121215] border border-zinc-800/80 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900/90 border-b border-zinc-800 text-zinc-400">
              <tr>
                <th className="p-3.5 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={
                      filteredDocs.length > 0 &&
                      filteredDocs.every((d) => selectedDocIds.includes(d.id))
                    }
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDocIds(filteredDocs.map((d) => d.id));
                      } else {
                        setSelectedDocIds([]);
                      }
                    }}
                    className="rounded bg-zinc-950 border-zinc-700 text-amber-400 focus:ring-0"
                  />
                </th>
                <th className="p-3.5">Document Name</th>
                <th className="p-3.5">Extraction Blueprint</th>
                <th className="p-3.5">Pages</th>
                <th className="p-3.5">File Size</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Ingested</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
              {filteredDocs.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <tr
                    key={doc.id}
                    className={`hover:bg-zinc-800/30 transition-colors ${
                      isSelected ? 'bg-zinc-800/50' : ''
                    }`}
                  >
                    <td className="p-3.5 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(doc.id)}
                        className="rounded bg-zinc-950 border-zinc-700 text-amber-400 focus:ring-0"
                      />
                    </td>
                    <td className="p-3.5 font-medium text-zinc-100 max-w-xs truncate">
                      <div className="flex items-center space-x-2.5 truncate">
                        <FileText className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <span className="truncate" title={doc.original_name}>
                          {doc.original_name}
                        </span>
                      </div>
                    </td>
                    <td className="p-3.5">
                      <span className="px-2.5 py-1 bg-zinc-900 text-zinc-300 border border-zinc-800 rounded-lg text-[11px] capitalize">
                        {doc.doc_type}
                      </span>
                    </td>
                    <td className="p-3.5">{doc.page_count} pp</td>
                    <td className="p-3.5">{(doc.file_size / 1024 / 1024).toFixed(2)} MB</td>
                    <td className="p-3.5">
                      <span className="capitalize">{doc.status}</span>
                    </td>
                    <td className="p-3.5 text-zinc-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3.5 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => setInspectingDoc(doc)}
                          className="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded-lg transition"
                          title="Inspect Document"
                        >
                          <FileSearch className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() =>
                            openSourceModal({
                              documentId: doc.id,
                              documentName: doc.original_name,
                              pageNumber: 1,
                            })
                          }
                          className="p-1.5 text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800 rounded-lg transition"
                          title="View Source PDF"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            navigate('/pipeline', { state: { documentIds: [doc.id] } });
                          }}
                          className="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded-lg transition"
                          title="Run Pipeline"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete document "${doc.original_name}"?`)) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          className="p-1.5 text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 rounded-lg transition"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredDocs.length === 0 && !isLoading && (
          <div className="p-12 text-center text-zinc-500 text-xs">
            No documents in this workspace. Upload PDFs using the ingestion panel above.
          </div>
        )}
      </div>

      {/* Document Inspection Modal */}
      {inspectingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl bg-[#121215] border border-zinc-800 rounded-2xl shadow-2xl p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
              <div className="flex items-center space-x-2.5">
                <FileSearch className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-semibold text-zinc-100 truncate max-w-md">
                  Inspection: {inspectingDoc.original_name}
                </h3>
              </div>
              <button
                onClick={() => setInspectingDoc(null)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 bg-[#09090b] border border-zinc-800 rounded-xl text-xs">
                  <div className="text-zinc-400">Total Pages</div>
                  <div className="text-sm font-semibold text-zinc-100 mt-0.5">
                    {inspectionData?.page_count ?? inspectingDoc.page_count}
                  </div>
                </div>
                <div className="p-3.5 bg-[#09090b] border border-zinc-800 rounded-xl text-xs">
                  <div className="text-zinc-400">Detected Tables</div>
                  <div className="text-sm font-semibold text-emerald-400 mt-0.5">
                    {inspectionData?.detected_tables_count ?? 0}
                  </div>
                </div>
                <div className="p-3.5 bg-[#09090b] border border-zinc-800 rounded-xl text-xs">
                  <div className="text-zinc-400">Text Layer</div>
                  <div className="text-sm font-semibold text-zinc-100 mt-0.5">
                    {inspectionData?.has_text_layer ? 'Searchable Text' : 'Scanned / OCR Needed'}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  Page Layout Preview
                </h4>
                {inspectionData?.pages_sample.map((sample) => (
                  <div
                    key={sample.page_number}
                    className="p-3.5 bg-zinc-900/60 border border-zinc-800 rounded-xl text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-amber-400 font-semibold">
                        Page {sample.page_number}
                      </span>
                      <span className="text-zinc-500 text-[11px]">
                        Tables: {sample.table_count} | Dims: {sample.width.toFixed(0)}x{sample.height.toFixed(0)}
                      </span>
                    </div>
                    <p className="text-zinc-300 text-[11px] line-clamp-2 bg-[#09090b] p-2.5 rounded-lg border border-zinc-800">
                      {sample.text_preview || 'No selectable text layer detected.'}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-zinc-800 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setInspectingDoc(null);
                  openSourceModal({
                    documentId: inspectingDoc.id,
                    documentName: inspectingDoc.original_name,
                    pageNumber: 1,
                  });
                }}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-xs text-zinc-300 rounded-xl border border-zinc-800 transition"
              >
                Open Full PDF
              </button>
              <button
                onClick={() => {
                  const docId = inspectingDoc.id;
                  setInspectingDoc(null);
                  navigate('/pipeline', { state: { documentIds: [docId] } });
                }}
                className="px-4 py-2 bg-amber-400 hover:bg-amber-300 text-black text-xs font-semibold rounded-xl transition"
              >
                Launch Pipeline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
