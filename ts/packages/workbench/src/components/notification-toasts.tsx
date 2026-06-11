import { useAtomSet, useAtomValue } from "@effect/atom-react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { notificationsAtom, removeNotificationAtom, type Notification } from "@/atoms/workbench";

const typeStyles: Record<Notification["type"], string> = {
  success: "border-success/40 bg-success/10 text-success",
  error: "border-error/40 bg-error/10 text-error",
  warning: "border-warning/40 bg-warning/10 text-warning",
  info: "border-brand-500/40 bg-brand-500/10 text-brand-300",
};

/**
 * Renders the active notification stack in the bottom-right corner.
 */
export function NotificationToasts() {
  const notifications = useAtomValue(notificationsAtom);
  const removeNotification = useAtomSet(removeNotificationAtom);

  if (notifications.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2" aria-live="polite">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={cn(
            "pointer-events-none flex items-start gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg",
            typeStyles[n.type],
          )}
        >
          <div className="flex-1">
            <p className="font-medium">{n.title}</p>
            {n.description && (
              <p className="mt-0.5 text-xs opacity-80">{n.description}</p>
            )}
          </div>
          <button
            onClick={() => removeNotification(n.id)}
            className="pointer-events-auto shrink-0 opacity-60 hover:opacity-100"
            aria-label="Dismiss notification"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
