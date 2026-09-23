import { create } from 'zustand';

interface SourceModalState {
  isOpen: boolean;
  documentId: string;
  documentName: string;
  pageNumber: number;
  recordIndex?: number;
}

interface AppState {
  selectedProjectId: string | null;
  setSelectedProjectId: (id: string | null) => void;
  sourceModal: SourceModalState;
  openSourceModal: (params: {
    documentId: string;
    documentName: string;
    pageNumber: number;
    recordIndex?: number;
  }) => void;
  closeSourceModal: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedProjectId: null,
  setSelectedProjectId: (id) => set({ selectedProjectId: id }),
  sourceModal: {
    isOpen: false,
    documentId: '',
    documentName: '',
    pageNumber: 1,
  },
  openSourceModal: ({ documentId, documentName, pageNumber, recordIndex }) =>
    set({
      sourceModal: {
        isOpen: true,
        documentId,
        documentName,
        pageNumber,
        recordIndex,
      },
    }),
  closeSourceModal: () =>
    set((state) => ({
      sourceModal: { ...state.sourceModal, isOpen: false },
    })),
}));
