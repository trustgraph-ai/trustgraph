import { useRef, useEffect, type TextareaHTMLAttributes } from "react";
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
  ...props
}: AutoTextareaProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (el === null) return;

    // Reset height so scrollHeight is recalculated
    el.style.height = "auto";

    // Compute line height from computed styles
    const style = window.getComputedStyle(el);
    const lineHeight = parseFloat(style.lineHeight) || 20;
    const maxHeight = lineHeight * maxRows;

    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, [value, maxRows]);

  return (
    <textarea
      ref={ref}
      value={value}
      className={cn(
        "w-full resize-none rounded-lg border border-border bg-surface-100 px-4 py-3 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500",
        className,
      )}
      rows={1}
      {...props}
    />
  );
}
