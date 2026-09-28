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
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  isCreateWorkspaceModalOpen: boolean;
  setCreateWorkspaceModalOpen: (open: boolean) => void;
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
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  isCreateWorkspaceModalOpen: false,
  setCreateWorkspaceModalOpen: (open) => set({ isCreateWorkspaceModalOpen: open }),
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
