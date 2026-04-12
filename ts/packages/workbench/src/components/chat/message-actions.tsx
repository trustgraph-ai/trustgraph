import { useState, useCallback } from "react";
import { Copy, Check, Trash2, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

interface MessageActionsProps {
  content: string;
  isLastAssistant: boolean;
  onDelete: () => void;
  onRegenerate?: () => void;
}

export function MessageActions({
  content,
  isLastAssistant,
  onDelete,
  onRegenerate,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for insecure contexts
      const textarea = document.createElement("textarea");
      textarea.value = content;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [content]);

  return (
    <div
      className={cn(
        "absolute -top-8 right-2 z-10 flex items-center gap-0.5",
        "rounded-lg border border-border bg-surface-200 px-1 py-0.5 shadow-sm",
        "pointer-events-none opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100",
      )}
    >
      <button
        onClick={handleCopy}
        className="rounded p-1.5 text-fg-subtle hover:bg-surface-300 hover:text-fg"
        title={copied ? "Copied!" : "Copy message"}
        aria-label={copied ? "Copied" : "Copy message"}
      >
        {copied ? (
          <Check className="h-3 w-3 text-success" />
        ) : (
          <Copy className="h-3 w-3" />
        )}
      </button>

      {isLastAssistant && onRegenerate && (
        <button
          onClick={onRegenerate}
          className="rounded p-1.5 text-fg-subtle hover:bg-surface-300 hover:text-fg"
          title="Regenerate response"
          aria-label="Regenerate response"
        >
          <RotateCcw className="h-3 w-3" />
        </button>
      )}

      <button
        onClick={onDelete}
        className="rounded p-1.5 text-fg-subtle hover:bg-error/20 hover:text-error"
        title="Delete message"
        aria-label="Delete message"
      >
        <Trash2 className="h-3 w-3" />
      </button>
    </div>
  );
}
