import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { RootLayout } from "@/components/layout/root-layout";
import ChatPage from "@/pages/chat";
import LibraryPage from "@/pages/library";
import GraphPage from "@/pages/graph";
import PromptsPage from "@/pages/prompts";
import TokenCostPage from "@/pages/token-cost";
import KnowledgeCoresPage from "@/pages/knowledge-cores";
import FlowsPage from "@/pages/flows";
import SettingsPage from "@/pages/settings";
import { NotificationToasts } from "@/components/notification-toasts";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<RootLayout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/prompts" element={<PromptsPage />} />
          <Route path="/token-cost" element={<TokenCostPage />} />
          <Route path="/knowledge-cores" element={<KnowledgeCoresPage />} />
          <Route path="/flows" element={<FlowsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>

      <NotificationToasts />
    </BrowserRouter>
  );
}
