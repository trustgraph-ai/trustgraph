import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { RootLayout } from "@/components/layout/root-layout";
import { ErrorBoundary } from "@/components/error-boundary";
import ChatPage from "@/pages/chat";
import LibraryPage from "@/pages/library";
import GraphPage from "@/pages/graph";
import PromptsPage from "@/pages/prompts";
import TokenCostPage from "@/pages/token-cost";
import KnowledgeCoresPage from "@/pages/knowledge-cores";
import FlowsPage from "@/pages/flows";
import McpToolsPage from "@/pages/mcp-tools";
import SettingsPage from "@/pages/settings";
import { NotificationToasts } from "@/components/notification-toasts";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<RootLayout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ErrorBoundary><ChatPage /></ErrorBoundary>} />
          <Route path="/library" element={<ErrorBoundary><LibraryPage /></ErrorBoundary>} />
          <Route path="/graph" element={<ErrorBoundary><GraphPage /></ErrorBoundary>} />
          <Route path="/prompts" element={<ErrorBoundary><PromptsPage /></ErrorBoundary>} />
          <Route path="/token-cost" element={<ErrorBoundary><TokenCostPage /></ErrorBoundary>} />
          <Route path="/knowledge-cores" element={<ErrorBoundary><KnowledgeCoresPage /></ErrorBoundary>} />
          <Route path="/flows" element={<ErrorBoundary><FlowsPage /></ErrorBoundary>} />
          <Route path="/mcp-tools" element={<ErrorBoundary><McpToolsPage /></ErrorBoundary>} />
          <Route path="/settings" element={<ErrorBoundary><SettingsPage /></ErrorBoundary>} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Route>
      </Routes>

      <NotificationToasts />
    </BrowserRouter>
  );
}
