import { create } from "zustand";
import { persist } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FeatureSwitches {
  flowClasses: boolean;
  submissions: boolean;
  tokenCost: boolean;
  schemas: boolean;
  structuredQuery: boolean;
  ontologyEditor: boolean;
  agentTools: boolean;
  mcpTools: boolean;
  llmModels: boolean;
}

export interface Settings {
  /** Display name / identifier sent with every request */
  user: string;
  /** Optional API key for gateway authentication */
  apiKey: string;
  /** Active knowledge-graph collection */
  collection: string;
  /** Gateway base URL (used when building the WebSocket URL) */
  gatewayUrl: string;
  /** Toggle optional sections of the UI */
  featureSwitches: FeatureSwitches;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_FEATURE_SWITCHES: FeatureSwitches = {
  flowClasses: false,
  submissions: false,
  tokenCost: false,
  schemas: false,
  structuredQuery: false,
  ontologyEditor: false,
  agentTools: false,
  mcpTools: false,
  llmModels: false,
};

const DEFAULT_SETTINGS: Settings = {
  user: "user",
  apiKey: "",
  collection: "default",
  gatewayUrl: "",
  featureSwitches: DEFAULT_FEATURE_SWITCHES,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

interface SettingsState {
  settings: Settings;
  isLoaded: boolean;

  /** Replace the entire settings object */
  setSettings: (settings: Settings) => void;

  /** Update a single top-level key */
  updateSetting: <K extends keyof Settings>(
    key: K,
    value: Settings[K],
  ) => void;

  /** Merge partial feature-switch overrides */
  updateFeatureSwitches: (partial: Partial<FeatureSwitches>) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      isLoaded: true,

      setSettings: (settings) => set({ settings }),

      updateSetting: (key, value) =>
        set((state) => ({
          settings: { ...state.settings, [key]: value },
        })),

      updateFeatureSwitches: (partial) =>
        set((state) => ({
          settings: {
            ...state.settings,
            featureSwitches: {
              ...state.settings.featureSwitches,
              ...partial,
            },
          },
        })),
    }),
    {
      name: "trustgraph-settings",
      // Mark loaded once rehydration completes
      onRehydrateStorage: () => (state) => {
        if (state) state.isLoaded = true;
      },
    },
  ),
);
