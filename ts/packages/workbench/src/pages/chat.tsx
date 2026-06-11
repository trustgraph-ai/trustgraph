import { useAtom, useAtomSet, useAtomValue } from "@effect/atom-react";
import type { KeyboardEvent } from "react";
import {
  MessageSquareText,
  Send,
  Trash2,
  Brain,
  Eye,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  X,
  AlertTriangle,
} from "lucide-react";
import Markdown from "react-markdown";
import { cn } from "@/lib/utils";
import type {
  ChatMessage,
} from "@/atoms/workbench";
import {
  agentPhaseExpandedAtom,
  cancelChatAtom,
  clearMessagesAtom,
  conversationAtom,
  deleteMessageAtom,
  isLoadingAtom,
  regenerateLastMessageAtom,
  setChatModeAtom,
  setConversationInputAtom,
  settingsAtom,
  submitMessageAtom,
} from "@/atoms/workbench";
import { AutoTextarea } from "@/components/ui/textarea";
import { MessageActions } from "@/components/chat/message-actions";
import { ExplainGraph } from "@/components/chat/explain-graph";

const MODES = [
  { value: "graph-rag" as const, label: "Graph RAG" },
  { value: "document-rag" as const, label: "Doc RAG" },
  { value: "agent" as const, label: "Agent" },
];

function AgentPhaseBlock({
  messageId,
  phase,
  icon,
  label,
  content,
  isActive,
}: {
  messageId: string;
  phase: string;
  icon: React.ReactNode;
  label: string;
  content: string;
  isActive: boolean;
}) {
  const [expandedMap, setExpandedMap] = useAtom(agentPhaseExpandedAtom);
  const key = `${messageId}:${phase}`;
  if (content.length === 0 && !isActive) return null;
  const expanded = expandedMap[key] ?? isActive;

  const phaseColors: Record<string, string> = {
    think: "border-amber-500/30 bg-amber-500/5",
    observe: "border-sky-500/30 bg-sky-500/5",
    answer: "border-emerald-500/30 bg-emerald-500/5",
  };

  const badgeColors: Record<string, string> = {
    think: "bg-amber-500/20 text-amber-400",
    observe: "bg-sky-500/20 text-sky-400",
    answer: "bg-emerald-500/20 text-emerald-400",
  };

  return (
    <div className={cn("rounded-md border", phaseColors[phase] ?? "border-border bg-surface-100")}>
      <button
        onClick={() => setExpandedMap({ ...expandedMap, [key]: !expanded })}
        aria-expanded={expanded}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-fg-muted"
      >
        {expanded ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        {icon}
        <span className={cn("rounded px-1.5 py-0.5", badgeColors[phase] ?? "bg-surface-200 text-fg-muted")}>
          {label}
        </span>
        {isActive && <Loader2 className="ml-auto h-3 w-3 animate-spin text-fg-subtle" />}
      </button>
      {expanded && (content.length > 0 || isActive) && (
        <div className="border-t border-border/50 px-3 py-2 text-xs leading-relaxed text-fg-muted">
          <p className="whitespace-pre-wrap">{content.length > 0 ? content : isActive ? "..." : ""}</p>
          {isActive && content.length > 0 && (
            <span className="mt-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
          )}
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  msg,
  collection,
  isLastAssistant,
}: {
  msg: ChatMessage;
  collection: string;
  isLastAssistant: boolean;
}) {
  const deleteMessage = useAtomSet(deleteMessageAtom);
  const regenerateLastMessage = useAtomSet(regenerateLastMessageAtom);
  const isUser = msg.role === "user";
  const agentPhases = msg.agentPhases;
  const isError = !isUser && msg.content.startsWith("Error:");

  return (
    <div className="group relative">
      <div
        className={cn(
          "rounded-lg px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "ml-auto max-w-[80%] bg-brand-700/30 text-fg"
            : isError
              ? "mr-auto max-w-[80%] border border-error/30 bg-error/10 text-error"
              : "mr-auto max-w-[80%] bg-surface-100 text-fg",
        )}
      >
        {agentPhases !== undefined && (
          <div className="mb-2 space-y-1.5">
            <AgentPhaseBlock
              messageId={msg.id}
              phase="think"
              icon={<Brain className="h-3 w-3" />}
              label="Thinking"
              content={agentPhases.think}
              isActive={msg.activePhase === "think"}
            />
            <AgentPhaseBlock
              messageId={msg.id}
              phase="observe"
              icon={<Eye className="h-3 w-3" />}
              label="Observing"
              content={agentPhases.observe}
              isActive={msg.activePhase === "observe"}
            />
            {agentPhases.answer.length > 0 && (
              <div className="flex items-center gap-1.5 px-1 pt-1 text-xs text-emerald-400">
                <CheckCircle className="h-3 w-3" />
                <span className="font-medium">Answer</span>
              </div>
            )}
          </div>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : isError ? (
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="whitespace-pre-wrap">{msg.content}</p>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none text-fg prose-headings:text-fg prose-strong:text-fg prose-p:my-1 prose-a:text-brand-400 prose-pre:bg-surface-200 prose-pre:text-fg prose-code:text-brand-300">
            <Markdown>{msg.content.length > 0 ? msg.content : msg.isStreaming === true ? "" : "(empty)"}</Markdown>
          </div>
        )}

        {msg.isStreaming === true && (
          <span className="mt-1 inline-block h-2 w-2 animate-pulse rounded-full bg-brand-400" />
        )}

        {msg.metadata !== undefined && (
          <div className="mt-2 flex items-center gap-3 text-[10px] text-fg-subtle">
            {msg.metadata.model !== undefined && msg.metadata.model.length > 0 && <span>{msg.metadata.model}</span>}
            {msg.metadata.inTokens != null && <span>in: {msg.metadata.inTokens}</span>}
            {msg.metadata.outTokens != null && <span>out: {msg.metadata.outTokens}</span>}
          </div>
        )}

        {!isUser && !isError && msg.isStreaming !== true && msg.explainEvents !== undefined && msg.explainEvents.length > 0 && (
          <ExplainGraph explainEvents={msg.explainEvents} collection={collection} />
        )}
      </div>
      {!isUser && (
        <MessageActions
          messageId={msg.id}
          content={msg.content}
          isLastAssistant={isLastAssistant}
          onDelete={() => deleteMessage(msg.id)}
          onRegenerate={() => regenerateLastMessage()}
        />
      )}
    </div>
  );
}

export default function ChatPage() {
  const conversation = useAtomValue(conversationAtom);
  const collection = useAtomValue(settingsAtom).collection;
  const isLoading = useAtomValue(isLoadingAtom);
  const setInput = useAtomSet(setConversationInputAtom);
  const setChatMode = useAtomSet(setChatModeAtom);
  const clearMessages = useAtomSet(clearMessagesAtom);
  const submitMessage = useAtomSet(submitMessageAtom);
  const cancelRequest = useAtomSet(cancelChatAtom);

  const handleSubmit = () => {
    if (conversation.input.trim().length > 0) {
      submitMessage({ input: conversation.input });
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const lastAssistantId = [...conversation.messages].reverse().find((message) => message.role === "assistant")?.id;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <MessageSquareText className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Chat</h1>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border bg-surface-100 p-1">
            {MODES.map((mode) => (
              <button
                key={mode.value}
                onClick={() => setChatMode(mode.value)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  conversation.chatMode === mode.value
                    ? "bg-brand-600 text-white"
                    : "text-fg-muted hover:bg-surface-200 hover:text-fg",
                )}
              >
                {mode.label}
              </button>
            ))}
          </div>

          {conversation.messages.length > 0 && (
            <button
              onClick={() => clearMessages(null)}
              className="rounded-lg border border-border p-2 text-fg-subtle hover:bg-surface-200 hover:text-error"
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-border bg-surface-50 p-4">
        {conversation.messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <MessageSquareText className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
            <p className="text-sm text-fg-subtle">Start a conversation with TrustGraph.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {conversation.messages.map((message) => (
              <MessageBubble
                key={message.id}
                msg={message}
                collection={collection}
                isLastAssistant={message.id === lastAssistantId}
              />
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 rounded-lg border border-border bg-surface-50 p-3">
        <div className="flex items-end gap-2">
          <AutoTextarea
            value={conversation.input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask using ${MODES.find((mode) => mode.value === conversation.chatMode)?.label ?? "TrustGraph"}...`}
            disabled={isLoading}
            maxRows={8}
          />
          {isLoading ? (
            <button
              onClick={() => cancelRequest(null)}
              className="rounded-lg border border-border p-3 text-fg-muted hover:bg-error/10 hover:text-error"
              aria-label="Cancel request"
            >
              <X className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={conversation.input.trim().length === 0}
              className="rounded-lg bg-brand-600 p-3 text-white hover:bg-brand-500 disabled:opacity-40"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
