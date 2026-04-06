import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Minimal flow description kept in session state after selection. */
export interface FlowInfo {
  id: string;
  description?: string;
  [key: string]: unknown;
}

interface SessionState {
  /** Currently-selected flow id */
  flowId: string;
  /** Cached flow definition for the selected flow */
  flow: FlowInfo | null;

  setFlowId: (id: string) => void;
  setFlow: (flow: FlowInfo | null) => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSessionStore = create<SessionState>()((set) => ({
  flowId: "default",
  flow: null,

  setFlowId: (id) => set({ flowId: id }),
  setFlow: (flow) => set({ flow }),
}));
