import { Outlet } from "react-router";
import { Sidebar } from "./sidebar";
import { FlowSelector } from "./flow-selector";
import { useProgressStore } from "@/hooks/use-progress-store";

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
  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-surface-0">
      {/* Global loading bar */}
      <LoadingBar />

      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-end border-b border-border bg-surface-50 px-6">
          <FlowSelector />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
