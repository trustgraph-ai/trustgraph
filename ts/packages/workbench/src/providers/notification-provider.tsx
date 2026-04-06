import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type NotificationType = "success" | "error" | "warning" | "info";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  description?: string;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

interface NotificationState {
  notifications: Notification[];

  addNotification: (
    type: NotificationType,
    title: string,
    description?: string,
  ) => string;

  removeNotification: (id: string) => void;

  /** Convenience wrappers */
  success: (title: string, description?: string) => string;
  error: (title: string, description?: string) => string;
  warning: (title: string, description?: string) => string;
  info: (title: string, description?: string) => string;
}

let _nextId = 0;
function nextId(): string {
  return `notif-${++_nextId}-${Date.now()}`;
}

/**
 * Simple toast-notification system backed by Zustand.
 *
 * Components can call `useNotification().success("Done!")` and render the
 * current `notifications` array however they like (e.g. a shadcn Toast list).
 *
 * Notifications are auto-dismissed after 5 seconds.
 */
export const useNotification = create<NotificationState>()((set, get) => {
  const AUTO_DISMISS_MS = 5_000;

  const addNotification: NotificationState["addNotification"] = (
    type,
    title,
    description,
  ) => {
    const id = nextId();
    const notification: Notification = { id, type, title, description };

    set((state) => ({
      notifications: [...state.notifications, notification],
    }));

    // Auto-dismiss
    setTimeout(() => {
      get().removeNotification(id);
    }, AUTO_DISMISS_MS);

    return id;
  };

  return {
    notifications: [],

    addNotification,

    removeNotification: (id) =>
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      })),

    success: (title, description) =>
      addNotification("success", title, description),
    error: (title, description) =>
      addNotification("error", title, description),
    warning: (title, description) =>
      addNotification("warning", title, description),
    info: (title, description) => addNotification("info", title, description),
  };
});
