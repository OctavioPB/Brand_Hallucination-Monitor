import { create } from "zustand";

interface AppState {
  /** Selected brand ID for cross-page context */
  selectedBrandId: string | null;
  setSelectedBrand: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedBrandId: null,
  setSelectedBrand: (id) => set({ selectedBrandId: id }),
}));
