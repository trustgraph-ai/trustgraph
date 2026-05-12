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
import type { StreamingMetadata, ExplainEvent } from "@trustgraph/client";

function metadataFrom(metadata: StreamingMetadata | undefined): ChatMessage["metadata"] | undefined {
  if (metadata === undefined) return undefined;

  const result: NonNullable<ChatMessage["metadata"]> = {};
  if (metadata.model !== undefined) result.model = metadata.model;
  if (metadata.in_token !== undefined) result.inTokens = metadata.in_token;
  if (metadata.out_token !== undefined) result.outTokens = metadata.out_token;

  return Object.keys(result).length > 0 ? result : undefined;
}

function withoutActivePhase(message: ChatMessage): ChatMessage {
  const next = { ...message };
  delete next.activePhase;
  return next;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseChatReturn {
  submitMessage: (opts: { input: string }) => void;
  cancelRequest: () => void;
  regenerateLastMessage: () => void;
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
    if (abortControllerRef.current !== null) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    updateLastMessage((prev) =>
      withoutActivePhase({
        ...prev,
        content: prev.content.length > 0 ? prev.content : "(Cancelled)",
        isStreaming: false,
      }),
    );
    removeActivity("Chat request");
  }, [updateLastMessage, removeActivity]);

  const submitMessage = useCallback(
    ({ input }: { input: string }) => {
      if (input.trim().length === 0) return;

      // Abort any in-flight request
      if (abortControllerRef.current !== null) {
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

      // Collect explainability events during streaming
      const explainEvents: ExplainEvent[] = [];
      const onExplain = (event: ExplainEvent) => {
        explainEvents.push(event);
      };

      // Attach collected explain events to the message on completion
      const attachExplainEvents = () => {
        if (explainEvents.length > 0) {
          updateLastMessage((prev) => ({
            ...prev,
            explainEvents: [...explainEvents],
          }));
        }
      };

      // Shared handler for streaming responses (graph-rag / document-rag)
      const onChunk = (
        chunk: string,
        complete: boolean,
        metadata?: StreamingMetadata,
      ) => {
        updateLastMessage((prev) => {
          const next: ChatMessage = {
            ...prev,
            content: prev.content + chunk,
            isStreaming: !complete,
          };
          const finalMetadata = complete ? metadataFrom(metadata) : undefined;
          return finalMetadata !== undefined
            ? { ...next, metadata: finalMetadata }
            : next;
        });

        if (complete) {
          attachExplainEvents();
          removeActivity(activityLabel);
        }
      };

      const onError = (error: string) => {
        updateLastMessage((prev) =>
          withoutActivePhase({
            ...prev,
            content: prev.content.length > 0 ? prev.content : `Error: ${error}`,
            isStreaming: false,
          }),
        );
        removeActivity(activityLabel);
      };

      // 3. Dispatch based on chat mode
      switch (chatMode) {
        case "graph-rag":
          flow.graphRagStreaming(input, onChunk, onError, undefined, collection, onExplain);
          break;

        case "document-rag":
          flow.documentRagStreaming(input, onChunk, onError, undefined, collection, onExplain);
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
	                  ...(complete ? {} : { activePhase: "think" as const }),
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
	                  ...(complete ? {} : { activePhase: "observe" as const }),
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
	                const next: ChatMessage = {
	                  ...prev,
	                  content: newAnswer,
	                  agentPhases: {
	                    ...phases,
	                    answer: newAnswer,
	                  },
	                  ...(complete ? {} : { activePhase: "answer" as const }),
	                  isStreaming: !complete,
	                };
	                const finalMetadata = complete ? metadataFrom(metadata) : undefined;
	                const withMetadata = finalMetadata !== undefined
	                  ? { ...next, metadata: finalMetadata }
	                  : next;
	                return complete ? withoutActivePhase(withMetadata) : withMetadata;
	              });
              if (complete) {
                attachExplainEvents();
                removeActivity(activityLabel);
              }
            },
            // error
            onError,
            // explainability
            onExplain,
            // collection
            collection,
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

  const regenerateLastMessage = useCallback(() => {
	    const msgs = useConversation.getState().messages;
	    const lastAssistant = [...msgs].reverse().find((m) => m.role === "assistant");
	    const lastUser = [...msgs].reverse().find((m) => m.role === "user");
	    if (lastAssistant !== undefined && lastUser !== undefined) {
	      useConversation.getState().deleteMessage(lastAssistant.id);
      submitMessage({ input: lastUser.content });
    }
  }, [submitMessage]);

  return { submitMessage, cancelRequest, regenerateLastMessage };
}
