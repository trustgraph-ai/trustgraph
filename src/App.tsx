import { useState, useEffect } from "react";
import type { TabKey, DomainKey, Entity } from "./types";
import { Header, StatusBar, Toaster } from "./components";
import { GraphView, QueryView, ExplainView, DataView, OntologyView } from "./pages";
import { useGraphData, toast } from "./state";

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("graph");
  const [activeFilter, setActiveFilter] = useState<DomainKey | null>(null);
  const [selectedNode, setSelectedNode] = useState<Entity | null>(null);
  const { entities, isLoading } = useGraphData();

  // Notification when graph loads
  useEffect(() => {
    if (!isLoading && entities.length > 0) {
      toast.success(`Graph loaded: ${entities.length} entities`);
    }
  }, [isLoading, entities.length]);

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
    if (tab !== "graph") {
      setSelectedNode(null);
    }
  };

  return (
    <div style={{
      width: "100%", minHeight: "100vh", background: "#0A0A0F",
      fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
      color: "#E5E5E5", overflow: "hidden",
    }}>
      <Header activeTab={activeTab} onTabChange={handleTabChange} />

      {activeTab === "graph" && (
        <GraphView
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
          selectedNode={selectedNode}
          onNodeSelect={setSelectedNode}
        />
      )}

      {activeTab === "query" && <QueryView />}

      {activeTab === "explain" && <ExplainView />}

      {activeTab === "data" && <DataView />}

      {activeTab === "ontology" && <OntologyView />}

      <StatusBar />
      <Toaster />
    </div>
  );
}
