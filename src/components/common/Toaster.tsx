import { useToastStore, Toast, ToastType } from "../../state/toastStore";
import { semantic, surface, text } from "../../theme";

const typeStyles: Record<ToastType, { color: string; icon: string }> = {
  success: { color: semantic.success, icon: "✓" },
  error: { color: semantic.error, icon: "✕" },
  warning: { color: semantic.warning, icon: "!" },
  info: { color: semantic.info, icon: "i" },
};

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const style = typeStyles[toast.type];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "12px 16px",
        background: surface.overlay,
        borderRadius: 8,
        borderLeft: `3px solid ${style.color}`,
        backdropFilter: "blur(12px)",
        boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
        minWidth: 280,
        maxWidth: 400,
        animation: "slideIn 0.2s ease-out",
      }}
    >
      <span
        style={{
          color: style.color,
          fontSize: 12,
          fontWeight: 700,
          width: 18,
          height: 18,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "50%",
          border: `1px solid ${style.color}`,
          flexShrink: 0,
        }}
      >
        {style.icon}
      </span>
      <span
        style={{
          flex: 1,
          fontSize: 12,
          color: text.secondary,
          fontFamily: "'IBM Plex Sans', sans-serif",
          lineHeight: 1.4,
        }}
      >
        {toast.message}
      </span>
      <button
        onClick={onDismiss}
        style={{
          background: "none",
          border: "none",
          color: text.faint,
          cursor: "pointer",
          fontSize: 16,
          padding: 4,
          lineHeight: 1,
        }}
      >
        ×
      </button>
    </div>
  );
}

export function Toaster() {
  const toasts = useToastStore((state) => state.toasts);
  const removeToast = useToastStore((state) => state.removeToast);

  if (toasts.length === 0) return null;

  return (
    <>
      <style>
        {`
          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateX(-20px);
            }
            to {
              opacity: 1;
              transform: translateX(0);
            }
          }
        `}
      </style>
      <div
        style={{
          position: "fixed",
          bottom: 60,
          left: 28,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onDismiss={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </>
  );
}
