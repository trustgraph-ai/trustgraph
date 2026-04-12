import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
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
import { useConversation, type ChatMessage } from "@/hooks/use-conversation";
import { useChat } from "@/hooks/use-chat";
import { useSettings } from "@/providers/settings-provider";
import { useProgressStore } from "@/hooks/use-progress-store";
import { AutoTextarea } from "@/components/ui/textarea";
import { MessageActions } from "@/components/chat/message-actions";
import { ExplainGraph } from "@/components/chat/explain-graph";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MODES = [
  { value: "graph-rag" as const, label: "Graph RAG" },
  { value: "document-rag" as const, label: "Doc RAG" },
  { value: "agent" as const, label: "Agent" },
];

// ---------------------------------------------------------------------------
// Agent phase section (collapsible)
// ---------------------------------------------------------------------------

function AgentPhaseBlock({
  phase,
  icon,
  label,
  content,
  isActive,
}: {
  phase: string;
  icon: React.ReactNode;
  label: string;
  content: string;
  isActive: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!content && !isActive) return null;

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
    <div
      className={cn(
        "rounded-md border",
        phaseColors[phase] ?? "border-border bg-surface-100",
      )}
    >
      <button
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-fg-muted"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        {icon}
        <span
          className={cn(
            "rounded px-1.5 py-0.5",
            badgeColors[phase] ?? "bg-surface-200 text-fg-muted",
          )}
        >
          {label}
        </span>
        {isActive && (
          <Loader2 className="ml-auto h-3 w-3 animate-spin text-fg-subtle" />
        )}
      </button>
      {expanded && content && (
        <div className="border-t border-border/50 px-3 py-2 text-xs leading-relaxed text-fg-muted">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ msg, collection }: { msg: ChatMessage; collection: string }) {
  const isUser = msg.role === "user";
  const hasAgentPhases = msg.agentPhases != null;
  const isError = !isUser && msg.content.startsWith("Error:");

  return (
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
      {/* Agent phase blocks (only for agent messages) */}
      {hasAgentPhases && msg.agentPhases && (
        <div className="mb-2 space-y-1.5">
          <AgentPhaseBlock
            phase="think"
            icon={<Brain className="h-3 w-3" />}
            label="Thinking"
            content={msg.agentPhases.think}
            isActive={msg.activePhase === "think"}
          />
          <AgentPhaseBlock
            phase="observe"
            icon={<Eye className="h-3 w-3" />}
            label="Observing"
            content={msg.agentPhases.observe}
            isActive={msg.activePhase === "observe"}
          />
          {msg.agentPhases.answer && (
            <div className="flex items-center gap-1.5 px-1 pt-1 text-xs text-emerald-400">
              <CheckCircle className="h-3 w-3" />
              <span className="font-medium">Answer</span>
            </div>
          )}
        </div>
      )}

      {/* Main content (markdown for assistant, plain for user) */}
      {isUser ? (
        <p className="whitespace-pre-wrap">{msg.content}</p>
      ) : isError ? (
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>
      ) : (
        <div className="prose prose-sm max-w-none text-fg prose-headings:text-fg prose-strong:text-fg prose-p:my-1 prose-a:text-brand-400 prose-pre:bg-surface-200 prose-pre:text-fg prose-code:text-brand-300">
          <Markdown>{msg.content || (msg.isStreaming ? "" : "(empty)")}</Markdown>
        </div>
      )}

      {/* Streaming indicator */}
      {msg.isStreaming && (
        <span className="mt-1 inline-block h-2 w-2 animate-pulse rounded-full bg-brand-400" />
      )}

      {/* Token metadata */}
      {msg.metadata && (
        <div className="mt-2 flex items-center gap-3 text-[10px] text-fg-subtle">
          {msg.metadata.model && <span>{msg.metadata.model}</span>}
          {msg.metadata.inTokens != null && (
            <span>in: {msg.metadata.inTokens}</span>
          )}
          {msg.metadata.outTokens != null && (
            <span>out: {msg.metadata.outTokens}</span>
          )}
        </div>
      )}

      {/* Explainability graph */}
      {!isUser && !isError && !msg.isStreaming && msg.explainEvents && msg.explainEvents.length > 0 && (
        <ExplainGraph explainEvents={msg.explainEvents} collection={collection} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chat page
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const messages = useConversation((s) => s.messages);
  const input = useConversation((s) => s.input);
  const chatMode = useConversation((s) => s.chatMode);
  const setInput = useConversation((s) => s.setInput);
  const setChatMode = useConversation((s) => s.setChatMode);
  const clearMessages = useConversation((s) => s.clearMessages);
  const { submitMessage, cancelRequest, regenerateLastMessage } = useChat();
  const deleteMessage = useConversation((s) => s.deleteMessage);
  const collection = useSettings((s) => s.settings.collection);
  const isLoading = useProgressStore((s) => s.isLoading);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Elapsed time counter while loading
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!isLoading) {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, [isLoading]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = useCallback(() => {
    if (input.trim()) {
      submitMessage({ input });
    }
  }, [input, submitMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <MessageSquareText className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Chat</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
            {collection}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Mode selector */}
          <div role="group" aria-label="Chat mode" className="flex rounded-lg border border-border bg-surface-100 p-0.5">
            {MODES.map((mode) => (
              <button
                type="button"
                key={mode.value}
                onClick={() => setChatMode(mode.value)}
                aria-pressed={chatMode === mode.value}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                  chatMode === mode.value
                    ? "bg-brand-600 text-white"
                    : "text-fg-muted hover:text-fg",
                )}
              >
                {mode.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => { cancelRequest(); clearMessages(); }}
            className="rounded-lg p-2 text-fg-subtle hover:bg-surface-200 hover:text-fg"
            title="Clear messages"
            aria-label="Clear messages"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto pb-4 pt-10">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-fg-subtle">
            <MessageSquareText className="mb-3 h-10 w-10 opacity-30" />
            <p>Send a message to start a conversation.</p>
            <p className="mt-1 text-xs">
              Mode: <span className="text-fg-muted">{MODES.find((m) => m.value === chatMode)?.label ?? chatMode}</span>
            </p>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isLastAssistant =
            msg.role === "assistant" &&
            idx === messages.length - 1;

          return (
            <div key={msg.id} className="group relative">
              {!msg.isStreaming && (
                <MessageActions
                  content={msg.content}
                  isLastAssistant={isLastAssistant}
                  onDelete={() => deleteMessage(msg.id)}
                  onRegenerate={isLastAssistant ? regenerateLastMessage : undefined}
                />
              )}
              <MessageBubble msg={msg} collection={collection} />
            </div>
          );
        })}
        <div ref={scrollRef} />
      </div>

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 pb-2 text-xs text-fg-subtle">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Processing... {elapsed}s</span>
          <button
            onClick={cancelRequest}
            className="flex items-center gap-1 rounded-lg px-3 py-1 text-xs text-red-400 hover:bg-surface-200"
          >
            <X className="h-3 w-3" />
            Cancel
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2 border-t border-border pt-4">
        <AutoTextarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          aria-label="Chat message"
          maxRows={6}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          aria-label="Send message"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white transition-colors hover:bg-brand-500 disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
