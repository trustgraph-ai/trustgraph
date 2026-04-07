import { useCallback, useRef } from "react";
import { useSocket } from "@/providers/socket-provider";
import {
  useConversation,
  nextMessageId,
  type ChatMessage,
} from "./use-conversation";
import { useSessionStore } from "./use-session-store";
import { useProgressStore } from "./use-progress-store";
import { useSettings } from "@/providers/settings-provider";
import type { StreamingMetadata } from "@trustgraph/client";

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseChatReturn {
  submitMessage: (opts: { input: string }) => void;
  cancelRequest: () => void;
}

/**
 * Orchestrates sending a chat message through the selected RAG / agent
 * pipeline and accumulates streamed chunks into the conversation store.
 */
export function useChat(): UseChatReturn {
  const socket = useSocket();
  const flowId = useSessionStore((s) => s.flowId);
  const chatMode = useConversation((s) => s.chatMode);
  const addMessage = useConversation((s) => s.addMessage);
  const updateLastMessage = useConversation((s) => s.updateLastMessage);
  const setInput = useConversation((s) => s.setInput);
  const collection = useSettings((s) => s.settings.collection);
  const addActivity = useProgressStore((s) => s.addActivity);
  const removeActivity = useProgressStore((s) => s.removeActivity);

  const abortControllerRef = useRef<AbortController | null>(null);

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    updateLastMessage((prev) => ({
      ...prev,
      content: prev.content || "(Cancelled)",
      isStreaming: false,
      activePhase: undefined,
    }));
    removeActivity("Chat request");
  }, [updateLastMessage, removeActivity]);

  const submitMessage = useCallback(
    ({ input }: { input: string }) => {
      if (!input.trim()) return;

      // Abort any in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const activityLabel = "Chat request";

      // 1. Add the user message
      const userMsg: ChatMessage = {
        id: nextMessageId(),
        role: "user",
        content: input,
        timestamp: Date.now(),
      };
      addMessage(userMsg);
      setInput("");

      // 2. Add a placeholder assistant message for streaming
      const assistantId = nextMessageId();
      const isAgent = chatMode === "agent";
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        isStreaming: true,
        ...(isAgent
          ? {
              agentPhases: { think: "", observe: "", answer: "" },
              activePhase: "think" as const,
            }
          : {}),
      };
      addMessage(assistantMsg);
      addActivity(activityLabel);

      const flow = socket.flow(flowId);

      // Shared handler for streaming responses (graph-rag / document-rag)
      const onChunk = (
        chunk: string,
        complete: boolean,
        metadata?: StreamingMetadata,
      ) => {
        updateLastMessage((prev) => ({
          ...prev,
          content: prev.content + chunk,
          isStreaming: !complete,
          ...(complete && metadata
            ? {
                metadata: {
                  model: metadata.model,
                  inTokens: metadata.in_token,
                  outTokens: metadata.out_token,
                },
              }
            : {}),
        }));

        if (complete) {
          removeActivity(activityLabel);
        }
      };

      const onError = (error: string) => {
        updateLastMessage((prev) => ({
          ...prev,
          content: prev.content || `Error: ${error}`,
          isStreaming: false,
          activePhase: undefined,
        }));
        removeActivity(activityLabel);
      };

      // 3. Dispatch based on chat mode
      switch (chatMode) {
        case "graph-rag":
          flow.graphRagStreaming(input, onChunk, onError, undefined, collection);
          break;

        case "document-rag":
          flow.documentRagStreaming(input, onChunk, onError, undefined, collection);
          break;

        case "agent": {
          // Agent has separate think / observe / answer streams.
          // We track each phase in agentPhases and display the answer
          // as the main content.

          flow.agent(
            input,
            // think
            (chunk, complete) => {
              updateLastMessage((prev) => {
                const phases = prev.agentPhases ?? {
                  think: "",
                  observe: "",
                  answer: "",
                };
                return {
                  ...prev,
                  agentPhases: {
                    ...phases,
                    think: phases.think + chunk,
                  },
                  activePhase: complete ? prev.activePhase : "think",
                };
              });
            },
            // observe
            (chunk, complete) => {
              updateLastMessage((prev) => {
                const phases = prev.agentPhases ?? {
                  think: "",
                  observe: "",
                  answer: "",
                };
                return {
                  ...prev,
                  agentPhases: {
                    ...phases,
                    observe: phases.observe + chunk,
                  },
                  activePhase: complete ? prev.activePhase : "observe",
                };
              });
            },
            // answer
            (chunk, complete, metadata) => {
              updateLastMessage((prev) => {
                const phases = prev.agentPhases ?? {
                  think: "",
                  observe: "",
                  answer: "",
                };
                const newAnswer = phases.answer + chunk;
                return {
                  ...prev,
                  content: newAnswer,
                  agentPhases: {
                    ...phases,
                    answer: newAnswer,
                  },
                  activePhase: complete ? undefined : "answer",
                  isStreaming: !complete,
                  ...(complete && metadata
                    ? {
                        metadata: {
                          model: metadata.model,
                          inTokens: metadata.in_token,
                          outTokens: metadata.out_token,
                        },
                      }
                    : {}),
                };
              });
              if (complete) {
                removeActivity(activityLabel);
              }
            },
            // error
            onError,
          );
          break;
        }
      }
    },
    [
      socket,
      flowId,
      chatMode,
      collection,
      addMessage,
      updateLastMessage,
      setInput,
      addActivity,
      removeActivity,
    ],
  );

  return { submitMessage, cancelRequest };
}
