import { useAtomSet, useAtomValue } from "@effect/atom-react";
import { Copy, Check, Trash2, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { copiedMessageIdAtom, copyMessageAtom } from "@/atoms/workbench";

interface MessageActionsProps {
  content: string;
  messageId: string;
  isLastAssistant: boolean;
  onDelete: () => void;
  onRegenerate?: () => void;
}

export function MessageActions({
  content,
  messageId,
  isLastAssistant,
  onDelete,
  onRegenerate,
}: MessageActionsProps) {
  const copiedMessageId = useAtomValue(copiedMessageIdAtom);
  const copyMessage = useAtomSet(copyMessageAtom);
  const copied = copiedMessageId === messageId;

  const handleCopy = () => {
    copyMessage({ id: messageId, content });
  };

  return (
    <div
      className={cn(
        "mt-1 flex w-fit items-center gap-0.5 lg:absolute lg:-top-8 lg:right-2 lg:z-10 lg:mt-0",
        "rounded-lg border border-border bg-surface-200 px-1 py-0.5 shadow-sm",
        "opacity-100 transition-opacity lg:pointer-events-none lg:opacity-0 lg:group-hover:pointer-events-auto lg:group-hover:opacity-100",
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
