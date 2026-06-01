import type { CSSProperties, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface AutoTextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Maximum number of rows before scrolling */
  maxRows?: number;
}

/**
 * Textarea that auto-resizes to fit its content, up to maxRows.
 */
export function AutoTextarea({
  maxRows = 6,
  className,
  value,
  style,
  ...props
}: AutoTextareaProps) {
  const textareaStyle: CSSProperties & { fieldSizing?: "content" } = {
    ...style,
    fieldSizing: "content",
    maxHeight: `calc(${maxRows}lh + 1.5rem)`,
  };

  return (
    <textarea
      value={value}
      style={textareaStyle}
      className={cn(
        "w-full resize-none overflow-y-auto rounded-lg border border-border bg-surface-100 px-4 py-3 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500",
        className,
      )}
      rows={1}
      {...props}
    />
  );
}
