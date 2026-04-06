import { useConnectionState } from "@trustgraph/react-provider";
import { useProgressStateStore } from "@trustgraph/react-state";
import { semantic, palette, text, border } from "../../theme";

export function StatusBar() {
  const connectionState = useConnectionState();
  const activity = useProgressStateStore((state) => state.activity);

  const getStatusDisplay = () => {
    if (!connectionState) return { color: text.subtle, text: "Initializing..." };
    switch (connectionState.status) {
      case "authenticated":
        return { color: semantic.success, text: "Authenticated" };
      case "connected":
        return { color: semantic.success, text: "Connected" };
      case "unauthenticated":
        return { color: semantic.info, text: "Connected" };
      case "connecting":
        return { color: palette.amber, text: "Connecting..." };
      case "reconnecting":
        return { color: semantic.warning, text: `Reconnecting (${connectionState.reconnectAttempt}/${connectionState.maxAttempts})...` };
      case "failed":
        return { color: semantic.error, text: "Connection failed" };
      default:
        return { color: text.subtle, text: connectionState.status };
    }
  };

  const status = getStatusDisplay();
  const activeActivity = activity.size > 0 ? Array.from(activity)[0] : null;

  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0,
      padding: "8px 28px", borderTop: `1px solid ${border.subtle}`,
      background: "rgba(10,10,15,0.95)", backdropFilter: "blur(8px)",
      display: "flex", justifyContent: "space-between", alignItems: "center",
      fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: text.hint,
    }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {activeActivity ? (
          <>
            <span style={{ color: palette.amber }}>◌</span>
            <span style={{ color: text.faint }}>{activeActivity}...</span>
          </>
        ) : (
          <>
            <span style={{ color: semantic.success }}>◈</span>
            <span style={{ color: text.disabled }}>Ready</span>
          </>
        )}
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <span style={{ color: status.color }}>●</span> {status.text}
        <span style={{ color: text.subtle }}>|</span>
        <span>trustgraph.ai</span>
      </div>
    </div>
  );
}
