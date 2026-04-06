import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProgressState {
  /** Set of currently-running activity labels */
  activities: Set<string>;

  /** Derived: true when at least one activity is running */
  isLoading: boolean;

  addActivity: (label: string) => void;
  removeActivity: (label: string) => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useProgressStore = create<ProgressState>()((set) => ({
  activities: new Set<string>(),
  isLoading: false,

  addActivity: (label) =>
    set((state) => {
      const next = new Set(state.activities);
      next.add(label);
      return { activities: next, isLoading: next.size > 0 };
    }),

  removeActivity: (label) =>
    set((state) => {
      const next = new Set(state.activities);
      next.delete(label);
      return { activities: next, isLoading: next.size > 0 };
    }),
}));
