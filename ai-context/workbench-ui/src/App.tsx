import { useEffect, lazy, Suspense } from "react";

import { Box } from "@chakra-ui/react";
import { BrowserRouter as Router, Routes, Route } from "react-router";

import Layout from "./components/Layout";

import ChatPage from "./pages/ChatPage";
import SearchPage from "./pages/SearchPage";
import EntityPage from "./pages/EntityPage";

// Lazy load GraphPage since it includes heavy 3D visualization library (react-force-graph/Three.js)
const GraphPage = lazy(() => import("./pages/GraphPage"));
// Lazy load FlowClassesPage since it includes reactflow library
const FlowClassesPage = lazy(() => import("./pages/FlowClassesPage"));
// Lazy load less frequently used pages
const OntologiesPage = lazy(() => import("./pages/OntologiesPage"));
const StructuredQueryPage = lazy(() => import("./pages/StructuredQueryPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const SchemasPage = lazy(() => import("./pages/SchemasPage"));
const LLMModelsPage = lazy(() => import("./pages/LLMModelsPage"));
const McpToolsPage = lazy(() => import("./pages/McpToolsPage"));

import FlowsPage from "./pages/FlowsPage";
import LibraryPage from "./pages/LibraryPage";
import KnowledgeCoresPage from "./pages/KnowledgeCoresPage";
import ProcessingPage from "./pages/ProcessingPage";
import TokenCostPage from "./pages/TokenCostPage";
import PromptsPage from "./pages/PromptsPage";
import ToolsPage from "./pages/ToolsPage";

import CenterSpinner from "./components/common/CenterSpinner";
import Progress from "./components/common/Progress";
import { Toaster } from "./components/ui/ToasterComponent";

import { useSocket, useConnectionState } from "@trustgraph/react-provider";
import {
  useProgressStateStore,
  useSessionStore,
} from "@trustgraph/react-state";

const App = () => {
  const socket = useSocket();
  const connectionState = useConnectionState();

  const addActivity = useProgressStateStore((state) => state.addActivity);
  const removeActivity = useProgressStateStore(
    (state) => state.removeActivity,
  );

  const setFlowId = useSessionStore((state) => state.setFlowId);
  const setFlow = useSessionStore((state) => state.setFlow);

  useEffect(() => {
    // Wait for socket connection to be established before loading flows
    if (
      !connectionState ||
      (connectionState.status !== "connected" &&
        connectionState.status !== "authenticated" &&
        connectionState.status !== "unauthenticated")
    ) {
      console.log(
        "App: Waiting for socket connection...",
        connectionState?.status,
      );
      return;
    }

    console.log("App: Socket connected, loading flows...");
    const act = "Load flows";
    addActivity(act);
    socket
      .flows()
      .getFlows()
      .then((ids) => {
        return Promise.all(
          ids.map((id) =>
            socket
              .flows()
              .getFlow(id)
              .then((x) => [id, x]),
          ),
        );
      })
      .then((flows) => {
        removeActivity(act);

        const flowIds = flows.map((fl) => fl[0]);
        if (flowIds.includes("default")) {
          setFlowId("default");
          const flow = flows.filter((fl) => fl[0] == "default")[0][1];
          setFlow(flow);
        } else {
          // No default flow, just pick first in the list.
          setFlowId(flows[0][0]);
          setFlow(flows[0][1]);
        }
      })
      .catch((err) => {
        removeActivity(act);
        console.log("Error:", err);
      });
  }, [
    socket,
    connectionState,
    addActivity,
    removeActivity,
    setFlow,
    setFlowId,
  ]);

  return (
    <Box width="100%" minHeight="100vh" bg="colors.background">
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/entity" element={<EntityPage />} />
            <Route
              path="/graph"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <GraphPage />
                </Suspense>
              }
            />
            <Route path="/flows" element={<FlowsPage />} />
            <Route
              path="/flow-classes"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <FlowClassesPage />
                </Suspense>
              }
            />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/kc" element={<KnowledgeCoresPage />} />
            <Route path="/procs" element={<ProcessingPage />} />
            <Route path="/tokencost" element={<TokenCostPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route
              path="/schemas"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <SchemasPage />
                </Suspense>
              }
            />
            <Route
              path="/ontologies"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <OntologiesPage />
                </Suspense>
              }
            />
            <Route
              path="/structured-query"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <StructuredQueryPage />
                </Suspense>
              }
            />
            <Route path="/agents" element={<ToolsPage />} />
            <Route
              path="/mcp-tools"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <McpToolsPage />
                </Suspense>
              }
            />
            <Route
              path="/llm-models"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <LLMModelsPage />
                </Suspense>
              }
            />
            <Route
              path="/settings"
              element={
                <Suspense fallback={<CenterSpinner />}>
                  <SettingsPage />
                </Suspense>
              }
            />
          </Routes>
        </Layout>
      </Router>
      <Progress />
      <CenterSpinner />
      <Toaster />
    </Box>
  );
};

export default App;
