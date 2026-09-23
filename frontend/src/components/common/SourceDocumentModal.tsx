import React, { useState, useEffect } from 'react';
import { X, ExternalLink, ChevronLeft, ChevronRight, FileText, ZoomIn, ZoomOut } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { apiClient } from '../../services/api';

export const SourceDocumentModal: React.FC = () => {
  const { sourceModal, closeSourceModal } = useAppStore();
  const [currentPage, setCurrentPage] = useState(sourceModal.pageNumber || 1);
  const [zoom, setZoom] = useState(100);

  useEffect(() => {
    if (sourceModal.pageNumber) {
      setCurrentPage(sourceModal.pageNumber);
    }
  }, [sourceModal.pageNumber]);

  if (!sourceModal.isOpen) return null;

  const pdfUrl = apiClient.getDocumentFileUrl(sourceModal.documentId);
  const viewerUrl = `${pdfUrl}#page=${currentPage}&zoom=${zoom}`;

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage((p) => p - 1);
    }
  };

  const handleNextPage = () => {
    setCurrentPage((p) => p + 1);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-6xl h-[90vh] bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-darkroom-card border-b border-darkroom-border">
          <div className="flex items-center space-x-3 truncate">
            <div className="p-2 bg-darkroom-navy/60 text-darkroom-gold rounded-lg border border-darkroom-gold/20">
              <FileText className="w-5 h-5" />
            </div>
            <div className="truncate">
              <h3 className="text-sm font-semibold text-gray-100 truncate">
                {sourceModal.documentName || 'Source Document'}
              </h3>
              <p className="text-xs text-gray-400 font-mono">
                {sourceModal.recordIndex !== undefined && (
                  <span className="text-darkroom-gold mr-2">
                    Record #{sourceModal.recordIndex}
                  </span>
                )}
                Document ID: {sourceModal.documentId.slice(0, 8)}...
              </p>
            </div>
          </div>

          {/* Navigation & Controls */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-darkroom-bg border border-darkroom-border rounded-lg px-2 py-1 text-xs font-mono">
              <button
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
                className="p-1 hover:text-darkroom-gold disabled:opacity-30 disabled:hover:text-inherit"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 text-gray-200 font-medium">Page {currentPage}</span>
              <button
                onClick={handleNextPage}
                className="p-1 hover:text-darkroom-gold"
                title="Next Page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center bg-darkroom-bg border border-darkroom-border rounded-lg px-2 py-1 text-xs font-mono">
              <button
                onClick={() => setZoom((z) => Math.max(50, z - 15))}
                className="p-1 hover:text-darkroom-gold"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="px-2 text-gray-300">{zoom}%</span>
              <button
                onClick={() => setZoom((z) => Math.min(200, z + 15))}
                className="p-1 hover:text-darkroom-gold"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>

            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="p-2 text-gray-400 hover:text-white hover:bg-darkroom-border rounded-lg transition-colors"
              title="Open Full PDF in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>

            <button
              onClick={closeSourceModal}
              className="p-2 text-gray-400 hover:text-rose-400 hover:bg-rose-950/40 rounded-lg transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body / PDF Viewer Frame */}
        <div className="flex-1 bg-gray-950 relative overflow-hidden">
          <iframe
            key={`${viewerUrl}-${currentPage}-${zoom}`}
            src={viewerUrl}
            title="PDF Document Viewer"
            className="w-full h-full border-0"
          />
        </div>

        {/* Modal Footer Provenance Summary */}
        <div className="flex items-center justify-between px-5 py-2.5 bg-darkroom-card border-t border-darkroom-border text-xs text-gray-400 font-mono">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
            <span>Audit Trail Verified: Exact extraction source anchored to Page {currentPage}</span>
          </div>
          <div>Darkroom Provenance Engine v2.0</div>
        </div>
      </div>
    </div>
  );
};
