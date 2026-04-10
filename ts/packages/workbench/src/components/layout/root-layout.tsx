import { Outlet } from "react-router";
import { WifiOff } from "lucide-react";
import { Sidebar } from "./sidebar";
import { FlowSelector } from "./flow-selector";
import { useProgressStore } from "@/hooks/use-progress-store";
import { useConnectionState } from "@/providers/socket-provider";

/**
 * Top loading bar -- shown when any global activity is in progress.
 */
function LoadingBar() {
  const isLoading = useProgressStore((s) => s.isLoading);

  if (!isLoading) return null;

  return (
    <div className="absolute left-0 right-0 top-0 z-40 h-0.5 overflow-hidden bg-surface-200">
      <div className="h-full w-1/3 animate-[slide_1.2s_ease-in-out_infinite] bg-brand-500" />
    </div>
  );
}

/**
 * Root layout: fixed sidebar + scrollable main content area with a top bar.
 */
export function RootLayout() {
  const connectionState = useConnectionState();
  const isDisconnected =
    connectionState.status === "failed" ||
    connectionState.status === "reconnecting";

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-surface-0">
      {/* Skip to main content link (visible on focus for keyboard users) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:shadow-lg"
      >
        Skip to content
      </a>

      {/* Global loading bar */}
      <LoadingBar />

      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-end border-b border-border bg-surface-50 px-6">
          <FlowSelector />
        </header>

        {/* Connection lost banner */}
        {isDisconnected && (
          <div className="flex items-center gap-2 border-b border-warning/30 bg-warning/10 px-4 py-2 text-xs text-warning">
            <WifiOff className="h-3.5 w-3.5" />
            <span>Connection lost. Attempting to reconnect...</span>
          </div>
        )}

        {/* Page content */}
        <main id="main-content" className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
