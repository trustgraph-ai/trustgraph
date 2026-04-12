import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ExplainEvent } from "@trustgraph/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChatMode = "graph-rag" | "document-rag" | "agent";

export type MessageRole = "user" | "assistant" | "system";

/** Phase labels for agent-mode messages */
export type AgentPhase = "think" | "observe" | "answer";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** Timestamp (epoch ms) */
  timestamp: number;
  /** If true the message is still being streamed */
  isStreaming?: boolean;
  /** Optional metadata attached on completion */
  metadata?: {
    model?: string;
    inTokens?: number;
    outTokens?: number;
  };
  /** Agent-mode phases with their accumulated content */
  agentPhases?: {
    think: string;
    observe: string;
    answer: string;
  };
  /** Indicates the current active phase during streaming */
  activePhase?: AgentPhase;
  /** Explainability events received during streaming (graph URIs for source subgraphs) */
  explainEvents?: ExplainEvent[];
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

interface ConversationState {
  messages: ChatMessage[];
  input: string;
  chatMode: ChatMode;

  setInput: (value: string) => void;
  setChatMode: (mode: ChatMode) => void;

  addMessage: (message: ChatMessage) => void;

  /**
   * Update the last message in the list (used during streaming to append
   * chunks).  The `updater` receives the current last message and must
   * return the replacement.
   */
  updateLastMessage: (
    updater: (prev: ChatMessage) => ChatMessage,
  ) => void;

  deleteMessage: (id: string) => void;

  clearMessages: () => void;
}

let _nextMsgId = 0;
export function nextMessageId(): string {
  return `msg-${++_nextMsgId}-${Date.now()}`;
}

export const useConversation = create<ConversationState>()(
  persist(
    (set) => ({
      messages: [],
      input: "",
      chatMode: "graph-rag",

      setInput: (value) => set({ input: value }),
      setChatMode: (mode) => set({ chatMode: mode }),

      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),

      updateLastMessage: (updater) =>
        set((state) => {
          if (state.messages.length === 0) return state;
          const last = state.messages[state.messages.length - 1]!;
          const updated = updater(last);
          return {
            messages: [...state.messages.slice(0, -1), updated],
          };
        }),

      deleteMessage: (id) =>
        set((state) => ({
          messages: state.messages.filter((m) => m.id !== id),
        })),

      clearMessages: () => set({ messages: [] }),
    }),
    {
      name: "tg-conversation",
      // Only persist messages and chatMode, not input or transient state
      partialize: (state) => {
        const MAX_PERSISTED_MESSAGES = 200;
        const filtered = state.messages.filter((m) => !m.isStreaming);
        return {
          messages: filtered.slice(-MAX_PERSISTED_MESSAGES),
          chatMode: state.chatMode,
        };
      },
    },
  ),
);
