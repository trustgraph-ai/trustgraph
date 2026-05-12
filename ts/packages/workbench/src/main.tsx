import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "@/App";
import { SocketProvider } from "@/providers/socket-provider";
import { useSettings } from "@/providers/settings-provider";
import "@/index.css";

const queryClient = new QueryClient();

/**
 * AppRoot reads settings from the Zustand store and passes them
 * into the SocketProvider so the WebSocket connection is configured
 * before any child component mounts.
 */
function AppRoot() {
  const settings = useSettings((s) => s.settings);

  return (
    <SocketProvider
      user={settings.user}
      {...(settings.apiKey.length > 0 ? { apiKey: settings.apiKey } : {})}
      {...(settings.gatewayUrl.length > 0 ? { socketUrl: settings.gatewayUrl } : {})}
    >
      <App />
    </SocketProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppRoot />
    </QueryClientProvider>
  </React.StrictMode>,
);

// Dismiss splash screen once React has mounted
requestAnimationFrame(() => {
  const splash = document.getElementById("splash");
  if (splash !== null) {
    splash.classList.add("fade-out");
    splash.addEventListener("transitionend", () => splash.remove());
  }
});
