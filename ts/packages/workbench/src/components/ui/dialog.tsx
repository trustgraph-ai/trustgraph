import {
  type ReactNode,
  type MouseEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
} from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  /** Max width class, defaults to max-w-lg */
  className?: string;
}

/**
 * Simple modal dialog built with Tailwind.
 * Renders a backdrop overlay + centered content panel.
 * Includes focus trap, auto-focus, and Escape to close.
 */
export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  className,
}: DialogProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  // Save the element that triggered the dialog so we can restore focus on close
  const triggerRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement | null;
    } else if (triggerRef.current !== null) {
      triggerRef.current.focus();
      triggerRef.current = null;
    }
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Auto-focus first focusable element when dialog opens
  useEffect(() => {
    if (!open || dialogRef.current === null) return;
    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      ),
    ).filter(
      (el) =>
        el.hidden === false &&
        !(el as HTMLButtonElement).disabled &&
        el.offsetParent !== null &&
        window.getComputedStyle(el).display !== "none",
    );
    // Focus the first input/textarea if available, otherwise the close button
    const firstInput = focusable.find(
      (el) => el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT",
    );
    (firstInput ?? focusable[0])?.focus();
  }, [open]);

  // Focus trap — keep Tab within the dialog
  useEffect(() => {
    if (!open || dialogRef.current === null) return;
    const dialog = dialogRef.current;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter(
        (el) =>
          el.hidden === false &&
          !(el as HTMLButtonElement).disabled &&
          el.offsetParent !== null &&
          window.getComputedStyle(el).display !== "none",
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleTab);
    return () => window.removeEventListener("keydown", handleTab);
  }, [open]);

  const handleBackdrop = useCallback(
    (e: MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={handleBackdrop}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          "relative w-full max-w-lg rounded-xl border border-border bg-surface-100 shadow-2xl",
          className,
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 id={titleId} className="text-lg font-semibold text-fg">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-md p-1 text-fg-subtle hover:bg-surface-200 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[60vh] overflow-y-auto px-6 py-4">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
