import React, { useState } from "react";

import { ScrollText } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import FlowClassTable from "../components/flow-classes/FlowClassTable";
import { FlowClassEditorView } from "../components/flow-classes/FlowClassEditorView";

type ViewMode = "table" | "editor";

const FlowClassesPage = () => {
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [editingFlowClassId, setEditingFlowClassId] = useState<string | null>(
    null,
  );

  const handleEditFlowClass = (flowClassId: string) => {
    setEditingFlowClassId(flowClassId);
    setViewMode("editor");
  };

  const handleBackToTable = () => {
    setViewMode("table");
    setEditingFlowClassId(null);
  };

  if (viewMode === "editor" && editingFlowClassId) {
    return (
      <FlowClassEditorView
        flowClassId={editingFlowClassId}
        onBack={handleBackToTable}
      />
    );
  }

  return (
    <>
      <PageHeader
        icon={<ScrollText />}
        title="Flow Classes"
        description="Managing the dataflow definitions"
      />
      <FlowClassTable onEdit={handleEditFlowClass} />
    </>
  );
};

export default FlowClassesPage;
